"""Redis service for storing and retrieving bus data"""

import json
import time
from typing import Optional, Dict, Any
import redis
from .settings import get_settings_instance
from .logger import get_logger_instance

settings_instance = get_settings_instance()
logger = get_logger_instance(__name__)


class RedisService:
    """Service for managing Redis operations"""

    def __init__(self, max_retries: int = 5, retry_delay: int = 3):
        """Initialize Redis connection with Connection Pool and Retry logic"""
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        redis_pool = redis.ConnectionPool(
            host=settings_instance.REDIS_HOST,
            port=settings_instance.REDIS_PORT,
            db=settings_instance.REDIS_DB,
            decode_responses=True,
            max_connections=10,
        )

        self.redis_client = redis.Redis(connection_pool=redis_pool)
        self._test_connection()

    def _test_connection(self) -> None:
        """Test Redis connection with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                self.redis_client.ping()
                logger.info(
                    f"✅ Connected to Redis at {settings_instance.REDIS_HOST}:{settings_instance.REDIS_PORT}"
                )
                return
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"⚠️ Redis didn't respond (Attempt {attempt + 1}). Retrying in {self.retry_delay}s..."
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ Failed to connect to Redis: {e}")
                    raise

    def set_bus_data(self, bus_id: str, data: Dict[str, Any], ttl: int = 600) -> bool:
        """Store bus data as Redis HASH"""
        try:
            key = f"bus:{bus_id}"
            self.redis_client.hset(key, mapping=data)
            self.redis_client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"❌ Error setting bus data: {e}")
            return False

    def get_bus_data(self, bus_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve bus data from Redis"""
        try:
            key = f"bus:{bus_id}"
            hash_data = self.redis_client.hgetall(key)
            if not hash_data:
                return None
            return hash_data
        except Exception as e:
            logger.error(f"❌ Error getting bus data: {e}")
            return None

    def get_all_buses(self) -> dict:
        """Retrieve all bus data currently in Redis using SCAN and PIPELINE"""
        try:
            snapshot = {}
            cursor = 0

            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor, match="bus:*", count=1000
                )

                if keys:
                    pipeline = self.redis_client.pipeline()
                    for key in keys:
                        pipeline.hgetall(key)

                    values = pipeline.execute()

                    for key, hash_data in zip(keys, values):
                        clean_bus_id = key.replace("bus:", "")

                        if hash_data and "data" in hash_data:
                            try:
                                parsed_data = json.loads(hash_data["data"])
                                raw_stuck = str(
                                    hash_data.get("is_stuck", "False")
                                ).lower()
                                is_stuck = True if raw_stuck == "true" else False

                                snapshot[clean_bus_id] = {
                                    "data": parsed_data,
                                    "tsi": hash_data.get("tsi"),
                                    "window_end_time": hash_data.get("window_end_time"),
                                    "avg_speed": hash_data.get("window_avg_speed"),
                                    "is_stuck": is_stuck,
                                }
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON for key {key}")
                                continue

                if cursor == 0:
                    break

            return snapshot
        except Exception as e:
            logger.error(f"❌ Error getting all buses: {e}")
            return {}

    def delete_bus_data(self, bus_id: str) -> bool:
        """Delete bus data from Redis"""
        try:
            key = f"bus:{bus_id}"
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"❌ Error deleting bus data: {e}")
            return False

    def close(self) -> None:
        """Close Redis connection"""
        try:
            self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Redis connection: {e}")


# Singleton instance
_redis_service: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    """Get or create Redis service instance"""
    global _redis_service
    if _redis_service is None:
        _redis_service = RedisService()
    return _redis_service
