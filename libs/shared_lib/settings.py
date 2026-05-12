"""Centralized configuration settings for HSL Bus system"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Application settings with hybrid support for environment variables and Spark properties.

    Cluster-injected settings (Kafka, Redis, GCS) must be initialized via init_from_spark()
    after SparkSession creation. Local/dev settings can use environment variables.
    """

    def __init__(self):
        # === Static Configuration (from environment variables) ===
        # These are typically set locally during development

        # MQTT Configuration (used by ingestion service, not Spark workers)
        self.MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.hsl.fi")
        self.MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
        self.MQTT_TOPIC = os.getenv("MQTT_TOPIC", "/hfp/v2/journey/ongoing/vp/bus/#")
        self.MQTT_USERNAME = os.getenv("MQTT_USERNAME")
        self.MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

        # Flask Configuration (used by web service, not Spark workers)
        self.FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
        self.FLASK_PORT = int(os.getenv("FLASK_PORT", 8080))
        self.FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")

        # Logging Configuration (can be overridden by Spark property)
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

        # Geographic Data Validation (from environment, not cluster-injected)
        self.LOCATION_LAT_MIN = float(os.getenv("LOCATION_LAT_MIN", 60.0))
        self.LOCATION_LAT_MAX = float(os.getenv("LOCATION_LAT_MAX", 60.5))
        self.LOCATION_LONG_MIN = float(os.getenv("LOCATION_LONG_MIN", 24.5))
        self.LOCATION_LONG_MAX = float(os.getenv("LOCATION_LONG_MAX", 25.5))

        # Speed Validation (m/s) (from environment, not cluster-injected)
        self.MAX_SPEED = float(os.getenv("MAX_SPEED", 33.3))  # ~120 km/h
        self.MIN_SPEED = float(os.getenv("MIN_SPEED", 0))

        # Direction Validation (degrees) (from environment, not cluster-injected)
        self.MIN_HEADING = float(os.getenv("MIN_HEADING", 0))
        self.MAX_HEADING = float(os.getenv("MAX_HEADING", 360))

        # === Cluster-Injected Configuration (will be set via init_from_spark) ===
        # These must be loaded from Spark properties on Dataproc clusters
        self._initialized = False
        self.GCS_BRONZE_PATH: Optional[str] = None
        self.GCS_SILVER_PATH: Optional[str] = None
        self.SPARK_CHECKPOINT_DIR: Optional[str] = None
        self.REDIS_HOST: Optional[str] = None
        self.REDIS_PORT: Optional[int] = None
        self.REDIS_DB: int = 0
        self.REDIS_TIMEOUT: int = 60
        self.KAFKA_BROKERS: Optional[str] = None
        self.KAFKA_TOPIC: Optional[str] = None

    def init_from_spark(self, spark) -> None:
        """
        Initialize cluster-injected settings from Spark properties.

        MUST be called immediately after SparkSession creation in the main module.
        This allows configurations passed via --properties to override defaults.

        Args:
            spark: SparkSession instance

        Raises:
            ValueError: If required Spark properties are missing
        """
        from shared_lib.logger import get_logger_instance

        logger = get_logger_instance(__name__)

        try:
            # Kafka settings (required for streaming)
            self.KAFKA_BROKERS = spark.conf.get(
                "spark.hsl.kafka.brokers", os.getenv("KAFKA_BROKERS", None)
            )
            if not self.KAFKA_BROKERS:
                raise ValueError(
                    "Missing required configuration: spark.hsl.kafka.brokers "
                    "(pass via --properties spark.hsl.kafka.brokers=...)"
                )

            self.KAFKA_TOPIC = spark.conf.get(
                "spark.hsl.kafka.topic", os.getenv("KAFKA_TOPIC", None)
            )
            if not self.KAFKA_TOPIC:
                raise ValueError(
                    "Missing required configuration: spark.hsl.kafka.topic "
                    "(pass via --properties spark.hsl.kafka.topic=...)"
                )

            # Redis settings (required for real-time updates)
            self.REDIS_HOST = spark.conf.get(
                "spark.hsl.redis.host", os.getenv("REDIS_HOST", None)
            )
            if not self.REDIS_HOST:
                raise ValueError(
                    "Missing required configuration: spark.hsl.redis.host "
                    "(pass via --properties spark.hsl.redis.host=...)"
                )

            self.REDIS_PORT = int(
                spark.conf.get("spark.hsl.redis.port", os.getenv("REDIS_PORT", "6379"))
            )

            # GCS settings (required for data lake writes)
            self.GCS_BRONZE_PATH = spark.conf.get(
                "spark.hsl.gcs.bronze", os.getenv("GCS_BRONZE_PATH", None)
            )
            if not self.GCS_BRONZE_PATH:
                raise ValueError(
                    "Missing required configuration: spark.hsl.gcs.bronze "
                    "(pass via --properties spark.hsl.gcs.bronze=...)"
                )

            self.GCS_SILVER_PATH = spark.conf.get(
                "spark.hsl.gcs.silver", os.getenv("GCS_SILVER_PATH", None)
            )
            if not self.GCS_SILVER_PATH:
                raise ValueError(
                    "Missing required configuration: spark.hsl.gcs.silver "
                    "(pass via --properties spark.hsl.gcs.silver=...)"
                )

            self.SPARK_CHECKPOINT_DIR = spark.conf.get(
                "spark.hsl.gcs.checkpoint", os.getenv("SPARK_CHECKPOINT_DIR", None)
            )
            if not self.SPARK_CHECKPOINT_DIR:
                raise ValueError(
                    "Missing required configuration: spark.hsl.gcs.checkpoint "
                    "(pass via --properties spark.hsl.gcs.checkpoint=...)"
                )

            # Optional settings
            self.REDIS_DB = int(spark.conf.get("spark.hsl.redis.db", "0"))
            self.REDIS_TIMEOUT = int(spark.conf.get("spark.hsl.redis.timeout", "60"))
            self.LOG_LEVEL = spark.conf.get("spark.hsl.log.level", self.LOG_LEVEL)

            self._initialized = True
            logger.info("✅ Settings initialized from Spark properties")

        except Exception as e:
            logger.error(f"❌ Failed to initialize settings from Spark: {e}")
            raise

    def is_initialized(self) -> bool:
        """Check if cluster-injected settings have been initialized."""
        return self._initialized

    def assert_initialized(self) -> None:
        """Raise an error if settings haven't been initialized yet."""
        if not self._initialized:
            raise RuntimeError(
                "Settings not initialized! Call settings_instance.init_from_spark(spark) "
                "immediately after creating the SparkSession in main.py"
            )

    def to_dict(self) -> dict:
        """Convert all settings to dictionary."""
        return {
            key: getattr(self, key)
            for key in dir(self)
            if not key.startswith("_") and not callable(getattr(self, key))
        }


# Global settings instance (lazy singleton)
_settings_instance: Optional[Settings] = None


def get_settings_instance() -> Settings:
    """Get or create the global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
