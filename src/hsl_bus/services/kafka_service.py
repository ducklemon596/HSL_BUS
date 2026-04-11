"""Kafka service for message publishing"""

import json
import logging
import time
from typing import Optional, Callable

from kafka import KafkaProducer
from ..config import settings_instance

logger = logging.getLogger(__name__)


class KafkaService:
    """Service for managing Kafka producer operations"""

    def __init__(self, max_retries: int = 5, retry_delay: int = 5):
        """
        Initialize Kafka producer with retry logic

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay in seconds between retries
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.producer = self._create_producer()

    def _create_producer(self) -> KafkaProducer:
        """Create Kafka producer with retry logic"""
        for attempt in range(self.max_retries):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=settings_instance.KAFKA_BROKER,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: str(k).encode("utf-8"),
                )
                logger.info(
                    f"✅ Connected to Kafka at {settings_instance.KAFKA_BROKER}"
                )
                return producer
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"❌ Kafka connection failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {self.retry_delay} seconds..."
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"❌ Failed to connect to Kafka after {self.max_retries} attempts"
                    )
                    raise

    def send_message(
        self,
        value: dict,
        key: Optional[str] = None,
        topic: Optional[str] = None,
        on_success: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> None:
        """
        Send message to Kafka

        Args:
            value: Dictionary to be serialized and sent
            key: Message key for partitioning
            topic: Kafka topic (uses default if not provided)
            on_success: Callback function on successful send
            on_error: Callback function on error
        """
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
        """
        Flush pending messages

        Args:
            timeout: Timeout in seconds
        """
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
