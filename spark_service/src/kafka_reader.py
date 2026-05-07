from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json

from shared_lib import get_settings_instance
from schemas import BUS_SCHEMA

settings_instance = get_settings_instance()


def read_from_kafka(spark: SparkSession, starting_offsets: str = "latest") -> DataFrame:
    return (
        spark.readStream.format("kafka")
        .option(
            "kafka.bootstrap.servers", settings_instance.SPARK_KAFKA_BOOTSTRAP_SERVERS
        )
        .option("subscribe", settings_instance.KAFKA_TOPIC)
        .option("startingOffsets", starting_offsets)
        .load()
        .selectExpr("CAST(key AS STRING) as key", "CAST(value AS STRING) as value")
        .withColumn("data", from_json(col("value"), BUS_SCHEMA))
        .select("data.VP.*")
        .withColumn("tst", col("tst").cast("timestamp"))
    )
