from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, from_json

from shared_lib.settings import get_settings_instance
from src.schemas import BUS_SCHEMA

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
    """
    Read data from Kafka topic and parse JSON messages.

    Retrieves Kafka configuration from the centralized settings instance.

    Args:
        spark: SparkSession instance
        starting_offsets: Kafka starting offsets ("latest", "earliest", or JSON string)

    Returns:
        DataFrame with parsed bus data

    Raises:
        RuntimeError: If settings haven't been initialized
    """
    config = get_settings_instance()
    config.assert_initialized()

    # Get Kafka settings from centralized configuration
    bootstrap_servers = config.KAFKA_BROKERS
    topic = config.KAFKA_TOPIC

    options = get_kafka_options(
        bootstrap_servers=bootstrap_servers,
        topic=topic,
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
