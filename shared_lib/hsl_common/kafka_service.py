"""Kafka service for message publishing"""

import json
import time
from typing import Optional, Callable

from .settings import get_settings_instance
from .logger import get_logger_instance
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

logger = get_logger_instance(__name__)
settings_instance = get_settings_instance()


class KafkaService:
    """Service for managing Kafka producer operations"""

    def __init__(self, retry_delay: int = 5):
        """
        Initialize Kafka producer with resilient retry logic

        Args:
            retry_delay: Delay in seconds between connection retries
        """
        self.retry_delay = retry_delay
        self.producer = self._create_producer()

    def _create_producer(self) -> KafkaProducer:
        """Create Kafka producer with infinite retry and fail-fast logic"""
        attempt = 1

        while True:
            try:
                logger.info(f"⏳ Initializing Kafka connection (Attempt: {attempt})...")

                producer = KafkaProducer(
                    bootstrap_servers=settings_instance.KAFKA_BROKER,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: str(k).encode("utf-8"),
                    max_block_ms=5000,
                    api_version=(2, 5, 0),
                )

                logger.info(
                    f"✅ Successfully connected to Kafka at {settings_instance.KAFKA_BROKER}"
                )
                return producer

            except NoBrokersAvailable as e:
                logger.warning(
                    f"⚠️ No brokers available. Retrying in {self.retry_delay} seconds..."
                )
            except Exception as e:
                logger.warning(
                    f"❌ Error connecting to Kafka: {e}. Retrying in {self.retry_delay} seconds..."
                )

            time.sleep(self.retry_delay)
            attempt += 1

    def send_message(
        self,
        value: dict,
        key: Optional[str] = None,
        topic: Optional[str] = None,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> None:
        """Send message to Kafka"""
        if topic is None:
            topic = settings_instance.KAFKA_TOPIC

        try:
            future = self.producer.send(topic, value=value, key=key)

            if on_success:
                future.add_callback(on_success)
            if on_error:
                future.add_errback(on_error)
        except Exception as e:
            logger.error(f"❌ Error sending message to Kafka: {e}")
            if on_error:
                on_error(e)

    def flush(self, timeout: int = 30) -> None:
        """Flush pending messages"""
        try:
            self.producer.flush(timeout)
            logger.debug(f"Flushed messages (timeout: {timeout}s)")
        except Exception as e:
            logger.error(f"❌ Error flushing messages: {e}")

    def close(self) -> None:
        """Close Kafka producer"""
        try:
            self.producer.close()
            logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"❌ Error closing Kafka producer: {e}")


# Singleton instance
_kafka_service: Optional[KafkaService] = None


def get_kafka_service() -> KafkaService:
    """Get or create Kafka service instance"""
    global _kafka_service
    if _kafka_service is None:
        _kafka_service = KafkaService()
    return _kafka_service
