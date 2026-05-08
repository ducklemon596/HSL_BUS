from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json

from shared_lib import get_settings_instance
from schemas import BUS_SCHEMA

settings_instance = get_settings_instance()

jaas_config = (
    "org.apache.kafka.common.security.oauthbearer.OAuthBearerLoginModule required;"
)


def get_kafka_options(
    bootstrap_servers: str, topic: str, starting_offsets: str
) -> dict:
    """Get Kafka connection options as a dictionary for better maintainability."""
    return {
        "kafka.bootstrap.servers": bootstrap_servers,
        "subscribe": topic,
        "startingOffsets": starting_offsets,
        # GCP IAM security configuration
        "kafka.security.protocol": "SASL_SSL",
        "kafka.sasl.mechanism": "OAUTHBEARER",
        "kafka.sasl.jaas.config": jaas_config,
        "kafka.sasl.login.callback.handler.class": (
            "com.google.cloud.hosted.kafka.auth.GcpLoginCallbackHandler"
        ),
    }


def read_from_kafka(spark: SparkSession, starting_offsets: str = "latest") -> DataFrame:
    """Read data from Kafka topic and parse JSON messages.

    Args:
        spark: SparkSession instance
        starting_offsets: Kafka starting offsets ("latest", "earliest", or JSON string)

    Returns:
        DataFrame with parsed bus data
    """
    dynamic_bootstrap_servers = spark.conf.get(
        "spark.hsl.kafka.servers", settings_instance.SPARK_KAFKA_BOOTSTRAP_SERVERS
    )
    dynamic_topic = spark.conf.get(
        "spark.hsl.kafka.topic", settings_instance.KAFKA_TOPIC
    )

    options = get_kafka_options(
        bootstrap_servers=dynamic_bootstrap_servers,
        topic=dynamic_topic,
        starting_offsets=starting_offsets,
    )

    kafka_df = spark.readStream.format("kafka")
    for key, value in options.items():
        kafka_df = kafka_df.option(key, value)

    return (
        kafka_df.load()
        .selectExpr("CAST(key AS STRING) as key", "CAST(value AS STRING) as value")
        .withColumn("data", from_json(col("value"), BUS_SCHEMA))
        .select("data.VP.*")
        .withColumn("tst", col("tst").cast("timestamp"))
    )
