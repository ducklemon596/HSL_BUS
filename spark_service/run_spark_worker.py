"""Spark worker orchestration for the HSL bus pipeline."""

from shared_lib.logger import get_logger_instance, update_loggers_from_settings
from shared_lib.settings import get_settings_instance
from src.kafka_reader import read_from_kafka
from src.data_pipeline import clean_bus_data
from src.redis_writer import (
    write_position_to_redis_query,
    write_speed_avg_to_redis_query,
)
from src.spark_session import create_spark_session
from src.storage_writer import bronze_layer, silver_layer

logger = get_logger_instance(__name__)


class SparkWorker:
    """
    Orchestrates Spark structured streaming for HSL bus data processing.

    Lifecycle:
    1. Create SparkSession
    2. Initialize settings from Spark properties
    3. Start streaming pipelines (Kafka → Redis, Kafka → GCS Bronze/Silver)
    """

    def __init__(self, starting_offsets: str = "latest"):
        """
        Initialize the Spark worker.

        Args:
            starting_offsets: Kafka offset to start from ("latest", "earliest", or JSON)
        """
        # Step 1: Create SparkSession
        self.spark = create_spark_session()
        logger.info("✅ SparkSession created")

        # Step 2: Initialize all configuration from Spark properties
        # Must happen BEFORE any streaming logic that uses settings
        settings_instance = get_settings_instance()
        try:
            settings_instance.init_from_spark(self.spark)
        except ValueError as e:
            logger.error(f"❌ Configuration error: {e}")
            raise

        # Update loggers with configured log level
        update_loggers_from_settings()

        self.starting_offsets = starting_offsets
        logger.info("✅ Spark worker initialized and configured")

    def start(self):
        """
        Start the streaming pipelines.

        Pipelines:
        - Kafka → Redis: Real-time position and traffic updates
        - Kafka → GCS: Raw data (Bronze) and aggregated data (Silver)
        """
        logger.info("🚀 Starting Spark streaming pipelines...")

        # Get configured Redis connection details
        settings_instance = get_settings_instance()
        settings_instance.assert_initialized()

        redis_host = settings_instance.REDIS_HOST
        redis_port = settings_instance.REDIS_PORT

        # Read from Kafka (two streams: one for real-time Redis, one for GCS storage)
        raw_df_for_streaming = read_from_kafka(
            self.spark, starting_offsets=self.starting_offsets
        )
        raw_df_for_storage = read_from_kafka(self.spark, starting_offsets="earliest")

        # Clean both streams
        clean_df_for_streaming = clean_bus_data(raw_df_for_streaming)
        clean_df_for_storage = clean_bus_data(raw_df_for_storage)

        # Redis pipeline: Real-time position and traffic status updates
        logger.info("📍 Starting Redis pipeline (position & traffic updates)...")
        write_position_to_redis_query(clean_df_for_streaming, redis_host, redis_port)
        write_speed_avg_to_redis_query(clean_df_for_streaming, redis_host, redis_port)

        # GCS pipeline: Bronze (raw) and Silver (aggregated) layers
        logger.info("💾 Starting GCS pipeline (Bronze & Silver layers)...")
        bronze_layer(raw_df_for_storage)
        silver_layer(clean_df_for_storage)

        logger.info("✅ All streaming pipelines started successfully")
        logger.info("⏳ Streaming... Press Ctrl+C to stop")

        # Wait for any termination (error or manual stop)
        self.spark.streams.awaitAnyTermination()
        logger.info("🛑 Streaming stopped")


def main():
    """Main entry point for the Spark worker."""
    try:
        worker = SparkWorker()
        worker.start()
    except Exception as e:
        logger.error(f"❌ Fatal error in Spark worker: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
