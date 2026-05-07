"""Centralized configuration settings for HSL Bus system"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""

    # GCP configuration
    GCS_BRONZE_PATH = os.getenv(
        "GCS_BRONZE_PATH", "gs://hsl-bus-data-lake-v1/bronze_layer/"
    )
    GCS_SILVER_PATH = os.getenv(
        "GCS_SILVER_PATH", "gs://hsl-bus-data-lake-v1/silver_layer/"
    )
    SPARK_CHECKPOINT_DIR = os.getenv(
        "SPARK_CHECKPOINT_DIR", "gs://hsl-bus-data-lake-v1/checkpoints/"
    )

    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "10.148.0.9")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_TIMEOUT = int(os.getenv("REDIS_TIMEOUT", 60))

    # MQTT Configuration
    MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.hsl.fi")
    MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
    MQTT_TOPIC = os.getenv("MQTT_TOPIC", "/hfp/v2/journey/ongoing/vp/bus/#")
    MQTT_USERNAME = os.getenv("MQTT_USERNAME")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

    # Kafka Configuration
    KAFKA_BROKER = os.getenv("KAFKA_BROKER", "10.148.0.4:9092")
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "hsl_bus")

    # Spark Configuration
    SPARK_KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKER", "10.148.0.4:9092")

    # Flask Configuration
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    FLASK_PORT = int(os.getenv("FLASK_PORT", 8080))
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Geographic Data Validation
    LOCATION_LAT_MIN = float(os.getenv("LOCATION_LAT_MIN", 60.0))
    LOCATION_LAT_MAX = float(os.getenv("LOCATION_LAT_MAX", 60.5))
    LOCATION_LONG_MIN = float(os.getenv("LOCATION_LONG_MIN", 24.5))
    LOCATION_LONG_MAX = float(os.getenv("LOCATION_LONG_MAX", 25.5))

    # Speed Validation (m/s)
    MAX_SPEED = float(os.getenv("MAX_SPEED", 33.3))  # ~120 km/h
    MIN_SPEED = float(os.getenv("MIN_SPEED", 0))

    # Direction Validation (degrees)
    MIN_HEADING = float(os.getenv("MIN_HEADING", 0))
    MAX_HEADING = float(os.getenv("MAX_HEADING", 360))

    @classmethod
    def to_dict(cls):
        """Convert settings to dictionary"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and key.isupper()
        }


# Default settings instance
settings_instance: Optional[Settings] = None


def get_settings_instance() -> Settings:
    global settings_instance
    if settings_instance is None:
        settings_instance = Settings()
    return settings_instance
