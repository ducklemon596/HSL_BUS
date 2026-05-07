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

from shared_lib import get_logger_instance, get_settings_instance

logger = get_logger_instance(__name__)
settings_instance = get_settings_instance()


def write_to_silver_layer(batch_df: DataFrame, batch_id: int):
    silver_path = settings_instance.GCS_SILVER_PATH
    if DeltaTable.isDeltaTable(batch_df.sparkSession, silver_path):
        delta_table = DeltaTable.forPath(batch_df.sparkSession, silver_path)
        delta_table.alias("target").merge(
            batch_df.alias("source"),
            "target.event_date = source.event_date "
            + "AND target.unique_veh_id = source.unique_veh_id "
            + "AND target.window_end = source.window_end",
        ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
    else:
        batch_df.write.format("delta").mode("append").partitionBy("event_date").save(
            silver_path
        )


def bronze_layer(raw_kafka_df: DataFrame):
    bronze_checkpoint = f"{settings_instance.SPARK_CHECKPOINT_DIR}bronze/"
    bronze_df = (
        raw_kafka_df.withColumn("ingest_time", current_timestamp())
        .withColumn("year", year(col("ingest_time")))
        .withColumn("month", month(col("ingest_time")))
        .withColumn("day", dayofmonth(col("ingest_time")))
    )

    return (
        bronze_df.writeStream.format("parquet")
        .option("path", settings_instance.GCS_BRONZE_PATH)
        .option("checkpointLocation", bronze_checkpoint)
        .partitionBy("year", "month", "day")
        .outputMode("append")
        .trigger(processingTime="5 minutes")
        .start()
    )


def silver_layer(clean_df: DataFrame):
    silver_checkpoint = f"{settings_instance.SPARK_CHECKPOINT_DIR}silver/"
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
