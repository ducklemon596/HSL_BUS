from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    avg,
    collect_list,
    col,
    current_timestamp,
    dayofmonth,
    expr,
    lower,
    max as max_,
    min as min_,
    month,
    sort_array,
    struct,
    trim,
    window,
    year,
)
from delta.tables import DeltaTable

from shared_lib.logger import get_logger_instance
from shared_lib.settings import get_settings_instance

logger = get_logger_instance(__name__)


def write_to_silver_layer(batch_df: DataFrame, batch_id: int):
    """
    Write aggregated data to Silver layer Delta table.

    Uses merge operations to handle updates and inserts.

    Args:
        batch_df: DataFrame with aggregated data
        batch_id: Batch ID from Spark Streaming

    Raises:
        RuntimeError: If settings haven't been initialized
    """
    config = get_settings_instance()
    config.assert_initialized()

    silver_path = config.GCS_SILVER_PATH

    if DeltaTable.isDeltaTable(batch_df.sparkSession, silver_path):
        delta_table = DeltaTable.forPath(batch_df.sparkSession, silver_path)
        delta_table.alias("target").merge(
            batch_df.alias("source"),
            "target.event_date = source.event_date "
            + "AND target.unique_veh_id = source.unique_veh_id "
            + "AND target.window_end = source.window_end",
        ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
        logger.info(
            f"✅ Batch {batch_id}: Merged {batch_df.count()} rows to Silver layer"
        )
    else:
        batch_df.write.format("delta").mode("append").partitionBy("event_date").save(
            silver_path
        )
        logger.info(f"✅ Batch {batch_id}: Initialized Silver layer Delta table")


def bronze_layer(raw_kafka_df: DataFrame):
    """
    Create a streaming query that writes raw data to Bronze layer (data lake).

    Raw data is partitioned by year/month/day for efficient querying.

    Args:
        raw_kafka_df: Raw DataFrame from Kafka

    Returns:
        StreamingQuery object

    Raises:
        RuntimeError: If settings haven't been initialized
    """
    config = get_settings_instance()
    config.assert_initialized()

    bronze_path = config.GCS_BRONZE_PATH
    checkpoint_dir = config.SPARK_CHECKPOINT_DIR

    bronze_checkpoint = f"{checkpoint_dir}bronze/"
    bronze_df = (
        raw_kafka_df.withColumn("ingest_time", current_timestamp())
        .withColumn("year", year(col("ingest_time")))
        .withColumn("month", month(col("ingest_time")))
        .withColumn("day", dayofmonth(col("ingest_time")))
    )

    logger.info(f"📝 Bronze layer: Writing to {bronze_path}")
    return (
        bronze_df.writeStream.format("parquet")
        .option("path", bronze_path)
        .option("checkpointLocation", bronze_checkpoint)
        .partitionBy("year", "month", "day")
        .outputMode("append")
        .trigger(processingTime="5 minutes")
        .start()
    )


def silver_layer(clean_df: DataFrame):
    """
    Create a streaming query that writes cleaned, aggregated data to Silver layer.

    Performs time-windowed aggregations and traffic status classification.

    Args:
        clean_df: Cleaned DataFrame with validation applied

    Returns:
        StreamingQuery object

    Raises:
        RuntimeError: If settings haven't been initialized
    """
    config = get_settings_instance()
    config.assert_initialized()

    silver_path = config.GCS_SILVER_PATH
    checkpoint_dir = config.SPARK_CHECKPOINT_DIR

    silver_checkpoint = f"{checkpoint_dir}silver/"

    logger.info(f"📝 Silver layer: Writing to {silver_path}")
    return (
        clean_df.filter(
            (
                col("drst").isNull()
                | (trim(col("drst")) == "")
                | (lower(col("drst")) == "null")
            )
            & (
                col("stop").isNull()
                | (trim(col("stop")) == "")
                | (lower(col("stop")) == "null")
            )
        )
        .withWatermark("tst", "3 minutes")
        .groupBy(window(col("tst"), "10 minute"), col("unique_veh_id"))
        .agg(
            avg("spd").alias("avg_speed"),
            max_("tst").alias("latest_msg_tst"),
            min_("tst").alias("earliest_msg_tst"),
            collect_list(struct(col("tsi"), col("lat"), col("long"))).alias(
                "unsorted_trajectory"
            ),
        )
        .withColumn("trajectory_path", sort_array(col("unsorted_trajectory"), True))
        .withColumn("window_start", col("window.start"))
        .withColumn("window_end", col("window.end"))
        .withColumn(
            "observed_duration_seconds",
            expr("unix_timestamp(latest_msg_tst) - unix_timestamp(earliest_msg_tst)"),
        )
        .withColumn(
            "traffic_status",
            expr(
                "CASE WHEN observed_duration_seconds < 480 THEN 'UNKNOWN' "
                + "WHEN avg_speed >= 4 THEN 'NORMAL' "
                + "WHEN avg_speed >= 3 THEN 'LIGHT' "
                + "WHEN avg_speed >= 1 THEN 'HEAVY' "
                + "ELSE 'GRIDLOCK' END"
            ),
        )
        .withColumn(
            "trajectory",
            expr(
                "CASE WHEN traffic_status IN ('LIGHT', 'HEAVY', 'GRIDLOCK') "
                + "THEN transform(trajectory_path, x -> struct(x.lat, x.long)) "
                + "ELSE NULL END"
            ),
        )
        .withColumn("event_date", col("window_start").cast("date"))
        .drop("unsorted_trajectory", "trajectory_path", "window")
        .writeStream.foreachBatch(write_to_silver_layer)
        .option("checkpointLocation", silver_checkpoint)
        .outputMode("update")
        .trigger(processingTime="5 minutes")
        .start()
    )
