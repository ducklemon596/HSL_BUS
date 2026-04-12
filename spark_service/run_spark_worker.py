"""Apache Spark worker for real-time data processing"""

import json
import os
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    current_timestamp,
    dayofmonth,
    expr,
    lower,
    month,
    row_number,
    sort_array,
    struct,
    trim,
    window,
    avg,
    col,
    from_json,
    collect_list,
    max,
    min,
    year,
)
from pyspark.sql.window import Window as SparkWindow
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    LongType,
    IntegerType,
)
from delta.tables import DeltaTable

from hsl_common import get_settings_instance, get_logger_instance

logger = get_logger_instance(__name__)
settings_instance = get_settings_instance()


class SparkWorker:
    """Spark streaming worker for processing bus data"""

    # Define schema for VP (Vehicle Position) data
    VP_SCHEMA = StructType(
        [
            StructField("desi", StringType(), True),
            StructField("dir", StringType(), True),
            StructField("oper", IntegerType(), True),
            StructField("veh", IntegerType(), True),
            StructField("unique_veh_id", StringType(), True),
            StructField("tst", StringType(), True),
            StructField("tsi", LongType(), True),
            StructField("spd", DoubleType(), True),
            StructField("hdg", IntegerType(), True),
            StructField("lat", DoubleType(), True),
            StructField("long", DoubleType(), True),
            StructField("acc", DoubleType(), True),
            StructField("dl", IntegerType(), True),
            StructField("odo", DoubleType(), True),
            StructField("drst", IntegerType(), True),
            StructField("oday", StringType(), True),
            StructField("jrn", IntegerType(), True),
            StructField("line", IntegerType(), True),
            StructField("start", StringType(), True),
            StructField("loc", StringType(), True),
            StructField("stop", StringType(), True),
            StructField("route", StringType(), True),
            StructField("occu", IntegerType(), True),
        ]
    )

    BUS_SCHEMA = StructType([StructField("VP", VP_SCHEMA, True)])

    def __init__(self):
        """Initialize Spark session and Redis connection"""
        self.spark = self._create_spark_session()
        logger.info("✅ Spark worker initialized")

    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with Kafka connector"""
        spark_version = "3.3.2"
        kafka_package = f"org.apache.spark:spark-sql-kafka-0-10_2.12:{spark_version}"

        # Locate GCP credentials file
        gcp_credentials = os.getenv("GCP_CREDENTIALS", "/app/credentials.json")

        spark = (
            SparkSession.builder.appName("HSL_Bus_Pipeline")
            # Set timezone to UTC for timestamp consistency across different environments
            # Timestamps in the data are in UTC, so we want Spark to interpret them as UTC to avoid timezone-related bugs
            .config("spark.sql.session.timeZone", "UTC")
            # Allocate memory for driver and executors
            .config("spark.driver.memory", "4g")
            .config("spark.executor.memory", "4g")
            # Configure GCS credentials for Spark to access GCS buckets
            .config(
                "spark.hadoop.google.cloud.auth.service.account.json.keyfile",
                gcp_credentials,
            )
            # Configure GCS connector for bronze layer
            .config(
                "spark.jars.packages",
                "com.google.cloud.bigdataoss:gcs-connector:hadoop3-2.2.5",
            )
            .config("spark.hadoop.google.cloud.auth.service.account.enable", "true")
            .config(
                "spark.hadoop.fs.gs.impl",
                "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem",
            )
            # Configure GCS connector for delta lake (silver layer)
            .config(
                "spark.hadoop.fs.AbstractFileSystem.gs.impl",
                "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS",
            )
            .config(
                "spark.jars.packages",
                "io.delta:delta-core_2.12:2.3.0,com.google.cloud.bigdataoss:gcs-connector:hadoop3-2.2.5",
            )
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config(
                "spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog",
            )
            # Optimize for streaming writes to Delta Lake in GCS
            .config("spark.databricks.delta.optimizeWrite.enabled", "true")
            .config("spark.databricks.delta.autoCompact.enabled", "true")
            # Configure Kafka package for streaming from Kafka
            .config("spark.jars.packages", kafka_package)
            .getOrCreate()
        )

        # Set log level to WARN to reduce verbosity
        spark.sparkContext.setLogLevel("ERROR")
        logger.info("👷 Spark Session created")
        return spark

    def _read_from_kafka(self, starting_offsets="latest") -> DataFrame:
        """Read raw data from Kafka topic
        starting_offsets: "latest" or "earliest"
        Returns a DataFrame with columns
        """
        return (
            self.spark.readStream.format("kafka")
            .option(
                "kafka.bootstrap.servers",
                settings_instance.SPARK_KAFKA_BOOTSTRAP_SERVERS,
            )
            .option("subscribe", settings_instance.KAFKA_TOPIC)
            .option("startingOffsets", starting_offsets)
            .load()
            .selectExpr("CAST(key AS STRING) as key", "CAST(value AS STRING) as value")
            .withColumn("data", from_json(col("value"), self.BUS_SCHEMA))
            .select("data.VP.*")
            .withColumn("tst", col("tst").cast("timestamp"))
        )

    def _clean_bus_data(self, raw_df: DataFrame) -> DataFrame:
        """Filter bus data based on validation rules"""
        return raw_df.filter(
            # Unique identification
            col("unique_veh_id").isNotNull()
            &
            # Geographic bounds (Helsinki area)
            (
                col("lat").between(
                    settings_instance.LOCATION_LAT_MIN,
                    settings_instance.LOCATION_LAT_MAX,
                )
            )
            & (
                col("long").between(
                    settings_instance.LOCATION_LONG_MIN,
                    settings_instance.LOCATION_LONG_MAX,
                )
            )
            &
            # Speed validation
            (col("spd") >= settings_instance.MIN_SPEED)
            & (col("spd") <= settings_instance.MAX_SPEED)
            &
            # Heading validation
            (
                col("hdg").between(
                    settings_instance.MIN_HEADING, settings_instance.MAX_HEADING
                )
            )
            &
            # Occupancy validation
            (col("occu") >= 0)
        )

    def _write_position_to_redis(self, batch_df: DataFrame, batch_id: int):
        """Write position data to Redis (Distributed version)"""

        redis_host = settings_instance.REDIS_HOST
        redis_port = settings_instance.REDIS_PORT
        redis_password = getattr(settings_instance, "REDIS_PASSWORD", None)

        # This function will be executed INDEPENDENTLY on each Spark Worker Node for its own partition of data
        def process_partition(iterator):
            # If partition is empty, just return
            try:
                first_row = next(iterator)
            except StopIteration:
                return

            from itertools import chain
            import redis

            if not hasattr(redis, "_my_global_client"):
                pool = redis.ConnectionPool(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True,
                    max_connections=10,
                )
                redis._my_global_client = redis.Redis(connection_pool=pool)
            redis_client = redis._my_global_client

            full_iterator = chain([first_row], iterator)

            LUA_POSITION_SCRIPT = """
            local bus_key = KEYS[1] 
            local new_tsi = tonumber(ARGV[1])
            local new_data = ARGV[2]
            local old_tsi = redis.call('HGET', bus_key, 'tsi')
            if not old_tsi or new_tsi > tonumber(old_tsi) then 
                redis.call('HSET', bus_key, 'data', new_data, 'tsi', new_tsi)
                redis.call('EXPIRE', bus_key, 600)
                return 1 
            end
            return 0 
            """
            update_latest = redis_client.register_script(LUA_POSITION_SCRIPT)

            with redis_client.pipeline() as pipe:
                count = 0

                for row in full_iterator:
                    bus_id = row["unique_veh_id"]
                    tsi = row["tsi"]
                    payload = {
                        "lat": float(row["lat"]),
                        "long": float(row["long"]),
                        "spd": float(row["spd"]),
                        "hdg": int(row["hdg"]),
                        "tst": str(row["tst"]),
                        "desi": str(row["desi"]),
                    }
                    update_latest(
                        keys=[bus_id], args=[tsi, json.dumps(payload)], client=pipe
                    )
                    count += 1

                    if count % 500 == 0:
                        pipe.execute()

                if count % 500 != 0:
                    pipe.execute()

        # Driver allows Spark to distribute the Redis write tasks to Worker Nodes
        try:
            batch_df.foreachPartition(process_partition)
            logger.info(f"💾 Batch {batch_id}: Dispatched writes to Redis via Workers")
        except Exception as e:
            logger.error(f"❌ Error dispatching Redis writes: {e}")

    def _write_speed_avg_to_redis(self, batch_df: DataFrame, batch_id: int):
        """Write speed average data to Redis (Distributed version)"""

        window_spec = SparkWindow.partitionBy("unique_veh_id").orderBy(
            col("window_end").desc()
        )

        final_df = (
            batch_df.withColumn("row_num", row_number().over(window_spec))
            .filter(col("row_num") == 1)
            .drop("row_num")
        )

        redis_host = settings_instance.REDIS_HOST
        redis_port = settings_instance.REDIS_PORT
        redis_password = getattr(settings_instance, "REDIS_PASSWORD", None)

        def process_partition(iterator):
            try:
                first_row = next(iterator)
            except StopIteration:
                return

            from itertools import chain
            import redis

            if not hasattr(redis, "_my_global_client"):
                pool = redis.ConnectionPool(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    decode_responses=True,
                    max_connections=10,
                )
                redis._my_global_client = redis.Redis(connection_pool=pool)
            redis_client = redis._my_global_client

            full_iterator = chain([first_row], iterator)

            LUA_TRAFFIC_SCRIPT = """
            local bus_key = KEYS[1]
            local new_window_end = ARGV[1]
            local avg_speed = ARGV[2]
            local is_stuck = ARGV[3]

            local old_window_end = redis.call('HGET', bus_key, 'window_end_time')

            if not old_window_end or new_window_end >= old_window_end then
                redis.call('HSET', bus_key, 
                    'window_end_time', new_window_end, 
                    'window_avg_speed', avg_speed, 
                    'is_stuck', is_stuck
                )
                return 1 
            end
            return 0 
            """
            update_traffic = redis_client.register_script(LUA_TRAFFIC_SCRIPT)

            with redis_client.pipeline() as pipe:
                count = 0
                # Worker lặp qua dữ liệu của phân vùng nó đang giữ
                for row in full_iterator:
                    bus_id = row["unique_veh_id"]
                    avg_speed = round(row["avg_speed"], 2)
                    window_end = str(row["window_end"])

                    is_stuck = (
                        "True"
                        if (row["observed_duration_seconds"] >= 180)
                        and (row["avg_speed"] < 4)
                        else "False"
                    )

                    update_traffic(
                        keys=[bus_id],
                        args=[window_end, avg_speed, is_stuck],
                        client=pipe,
                    )
                    count += 1

                    if count % 500 == 0:
                        pipe.execute()

                if count % 500 != 0:
                    pipe.execute()

        try:
            final_df.foreachPartition(process_partition)
            logger.info(
                f"💾 Batch {batch_id}: Dispatched speed averages to Redis via Workers"
            )
        except Exception as e:
            logger.error(f"❌ Error dispatching speed averages writes: {e}")

    def _write_position_to_redis_query(self, clean_df: DataFrame):
        """Write position data to Redis using foreachBatch"""
        return (
            clean_df.select(
                "unique_veh_id", "tst", "tsi", "lat", "long", "spd", "hdg", "desi"
            )
            .writeStream.foreachBatch(self._write_position_to_redis)
            .outputMode("update")
            .trigger(processingTime="1 second")
            .start()
        )

    def _write_speed_avg_to_redis_query(self, clean_df: DataFrame) -> DataFrame:
        """Write speed average data to Redis using foreachBatch"""
        return (
            clean_df.withWatermark("tst", "1 minute")
            .groupBy(window(col("tst"), "5 minute", "1 minute"), col("unique_veh_id"))
            .agg(
                avg("spd").alias("avg_speed"),
                max("tsi").alias("latest_msg_tsi"),
                min("tsi").alias("earliest_msg_tsi"),
            )
            .select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                col("unique_veh_id"),
                col("avg_speed"),
                (expr("latest_msg_tsi - earliest_msg_tsi")).alias(
                    "observed_duration_seconds"
                ),
            )
            .writeStream.foreachBatch(self._write_speed_avg_to_redis)
            .outputMode("update")
            .trigger(processingTime="10 seconds")
            .start()
        )

    def _write_to_silver_layer(self, batch_df: DataFrame, batch_id: int) -> DataFrame:
        """Write cleaned data to Silver layer in GCS
        This function will UPSERT data into Delta Lake format in GCS
        """
        silver_path = settings_instance.GCS_SILVER_PATH

        if DeltaTable.isDeltaTable(self.spark, silver_path):
            delta_table = DeltaTable.forPath(self.spark, silver_path)
            delta_table.alias("target").merge(
                batch_df.alias("source"),
                "target.event_date = source.event_date "
                + "AND target.unique_veh_id = source.unique_veh_id "
                + "AND target.window_end = source.window_end",
            ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
        else:
            batch_df.write.format("delta").mode("append").partitionBy(
                "event_date"
            ).save(silver_path)

    def _bronze_layer(self, raw_kafka_df: DataFrame) -> DataFrame:
        """Start Spark streaming to write raw data to GCS (Bronze layer)"""
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

    def _silver_layer(self, clean_df: DataFrame) -> DataFrame:
        """Start Spark streaming to read clean data, and write to Silver layer"""

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
            )  # Filter out data points where the bus is at a stop
            .withWatermark("tst", "3 minutes")
            .groupBy(window(col("tst"), "10 minute"), col("unique_veh_id"))
            .agg(
                avg("spd").alias("avg_speed"),
                max("tst").alias("latest_msg_tst"),
                min("tst").alias("earliest_msg_tst"),
                collect_list(struct(col("tsi"), col("lat"), col("long"))).alias(
                    "unsorted_trajectory"
                ),
            )
            .withColumn(
                "trajectory_path", sort_array(col("unsorted_trajectory"), asc=True)
            )
            .withColumn("window_start", col("window.start"))
            .withColumn("window_end", col("window.end"))
            .withColumn(
                "observed_duration_seconds",
                expr(
                    "unix_timestamp(latest_msg_tst) - unix_timestamp(earliest_msg_tst)"
                ),
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
            .writeStream.foreachBatch(self._write_to_silver_layer)
            .option("checkpointLocation", silver_checkpoint)
            .outputMode("update")
            .trigger(processingTime="5 minutes")
            .start()
        )

    def start(self):
        """Start Spark streaming processing"""
        try:
            logger.info("🚀 Start streaming from Kafka...")

            # Read from Kafka
            # DataFrame remains the same as the structure in sample.json
            raw_df_for_streaming = self._read_from_kafka(starting_offsets="latest")
            raw_df_for_storage = self._read_from_kafka(starting_offsets="earliest")
            # Clean data
            clean_df_for_streaming = self._clean_bus_data(raw_df_for_streaming)
            clean_df_for_storage = self._clean_bus_data(raw_df_for_storage)

            # 1. Write to Redis for real-time updates
            # These processing are for streaming UI and real-time updates, not for batch storage
            # Don't need config checkpoint since we only want the latest state in Redis, not the full history
            position_query = self._write_position_to_redis_query(clean_df_for_streaming)
            speed_avg_query = self._write_speed_avg_to_redis_query(
                clean_df_for_streaming
            )

            # 2. Write raw data to GCS for storage
            # So we need checkpoint to ensure exactly-once semantics and data integrity
            bronze_query = self._bronze_layer(raw_df_for_storage)
            silver_query = self._silver_layer(clean_df_for_storage)

            self.spark.streams.awaitAnyTermination()

        except Exception as e:
            logger.critical(f"💀 Spark Error: {e}")
            raise
        except KeyboardInterrupt:
            logger.info("🛑 Spark worker interrupted by user")
        finally:
            if hasattr(self, "spark") and self.spark is not None:
                logger.info("🛑 Stopping active streams...")
                for stream in self.spark.streams.active:
                    stream.stop()
                logger.info("🛑 Stopping Spark Session...")
                self.spark.stop()


def main():
    """Main entry point for Spark worker"""
    worker = SparkWorker()
    worker.start()


if __name__ == "__main__":
    main()
