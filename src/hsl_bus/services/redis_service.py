"""Redis service for storing and retrieving bus data"""

import json
import logging
from typing import Optional, Dict, Any
import redis

from ..config import settings_instance

logger = logging.getLogger(__name__)


class RedisService:
    """Service for managing Redis operations"""

    def __init__(self):
        """Initialize Redis connection"""
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
        """Test Redis connection"""
        try:
            self.redis_client.ping()
            logger.info(
                f"✅ Connected to Redis at {settings_instance.REDIS_HOST}:{settings_instance.REDIS_PORT}"
            )
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise

    def set_bus_data(self, bus_id: str, data: Dict[str, Any], ttl: int = 60) -> bool:
        """
        Store bus data in Redis with TTL

        Args:
            bus_id: Unique vehicle ID
            data: Bus data dictionary
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            value = json.dumps(data)
            self.redis_client.set(bus_id, value, ex=ttl)
            return True
        except Exception as e:
            logger.error(f"❌ Error setting bus data: {e}")
            return False

    def get_bus_data(self, bus_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve bus data from Redis

        Args:
            bus_id: Unique vehicle ID

        Returns:
            Bus data dictionary or None if not found
        """
        try:
            value = self.redis_client.get(bus_id)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"❌ Error getting bus data: {e}")
            return None

    def get_all_buses(self) -> dict:
        """
        Retrieve all bus data currently in Redis
        Returns: Dictionary with all bus data
        """
        try:
            snapshot = {}
            cursor = '0' 

            while True:
                cursor, keys = self.redis_client.scan(cursor=cursor, count=1000)

                if keys:
                    pipeline = self.redis_client.pipeline()
                    for key in keys:
                        # Dùng HGETALL để bê TOÀN BỘ các trường trong Hash ra (data, is_stuck, avg_speed...)
                        pipeline.hgetall(key)
                    
                    # Trả về 1 mảng các Dictionary
                    values = pipeline.execute() 
                    
                    for key, hash_data in zip(keys, values):
                        # hash_data lúc này trông như thế này: 
                        # {"data": '{"lat": 60.1, ...}', "is_stuck": "True", "window_avg_speed": "15.5", "tsi": "123"}
                        
                        if hash_data and "data" in hash_data:
                            try:
                                # 1. Mở gói cái chuỗi văn bản JSON bên trong trường "data"
                                parsed_data = json.loads(hash_data["data"])
                                
                                # 2. Xử lý an toàn trạng thái is_stuck (chống lỗi None)
                                raw_stuck = str(hash_data.get("is_stuck", "False")).lower()
                                is_stuck = True if raw_stuck == "true" else False
                                
                                # 3. Lắp ráp lại đúng chuẩn Schema JSON Frontend yêu cầu
                                snapshot[key] = {
                                    "data": parsed_data,
                                    "tsi": hash_data.get("tsi"),
                                    "window_end_time": hash_data.get("window_end_time"),
                                    "avg_speed": hash_data.get("window_avg_speed"),
                                    "is_stuck": is_stuck
                                }
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON for key {key}")
                                continue     

                # ĐIỀU KIỆN DỪNG PHẢI ĐẶT Ở CUỐI CÙNG (Sau khi đã xử lý hết keys)
                if cursor == 0 or cursor == '0' or cursor == b'0':
                    break

            return snapshot
        except Exception as e:
            logger.error(f"❌ Error getting all buses: {e}")
            return {}

    def delete_bus_data(self, bus_id: str) -> bool:
        """
        Delete bus data from Redis

        Args:
            bus_id: Unique vehicle ID

        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"bus:{bus_id}"
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"❌ Error deleting bus data: {e}")
            return False

    def close(self) -> None:
        """Close Redis connection"""
        try:
            self.client.close()
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
