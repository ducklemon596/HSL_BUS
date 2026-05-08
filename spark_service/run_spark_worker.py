"""Spark worker orchestration for the HSL bus pipeline."""

from shared_lib import get_logger_instance
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
    """Orchestrates Spark streaming for bus data processing."""

    def __init__(self, starting_offsets: str = "latest"):
        self.spark = create_spark_session()
        self.starting_offsets = starting_offsets
        logger.info("✅ Spark worker initialized")

    def start(self):
        logger.info("🚀 Start streaming from Kafka...")

        REDIS_HOST = self.spark.conf.get("spark.hsl.redis.host", "localhost")

        raw_df_for_streaming = read_from_kafka(
            self.spark, starting_offsets=self.starting_offsets
        )
        raw_df_for_storage = read_from_kafka(self.spark, starting_offsets="earliest")

        clean_df_for_streaming = clean_bus_data(raw_df_for_streaming)
        clean_df_for_storage = clean_bus_data(raw_df_for_storage)

        write_position_to_redis_query(clean_df_for_streaming, redis_host=REDIS_HOST)
        write_speed_avg_to_redis_query(clean_df_for_streaming, redis_host=REDIS_HOST)

        bronze_layer(raw_df_for_storage)
        silver_layer(clean_df_for_storage)

        self.spark.streams.awaitAnyTermination()


def main():
    worker = SparkWorker()
    worker.start()


if __name__ == "__main__":
    main()
