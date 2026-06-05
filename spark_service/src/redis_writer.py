import json
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, row_number, avg, max as max_, min as min_, window
from pyspark.sql.window import Window as SparkWindow

from shared_lib.logger import get_logger_instance

logger = get_logger_instance(__name__)

# Global Redis client pool (connection pooling for efficiency across partitions)
_redis_client = None


def _get_redis_client(redis_host: str, redis_port: int):
    """
    Get or create a Redis client with connection pooling.

    This is called within worker executors via foreachPartition, so we use
    a module-level cache to avoid recreating connections per partition.

    Args:
        redis_host: Redis server hostname
        redis_port: Redis server port

    Returns:
        Redis client instance
    """
    import redis

    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            max_connections=10,
        )
        _redis_client = redis.Redis(connection_pool=pool)
        # Test connection
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis at {redis_host}:{redis_port}: {e}")
        raise


def _process_position_partition(
    iterator, redis_host: str, redis_port: int, redis_password=None
):
    """
    Process a partition of position data and write to Redis.

    Uses Lua scripting to ensure atomic operations on the server side.

    Args:
        iterator: Row iterator from Spark partition
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_password: Redis password (unused, but kept for compatibility)
    """
    try:
        first_row = next(iterator)
    except StopIteration:
        return

    from itertools import chain

    redis_client = _get_redis_client(redis_host, redis_port)

    LUA_POSITION_SCRIPT = """
    local bus_key = KEYS[1]
    local new_tsi = tonumber(ARGV[1])
    local new_data = ARGV[2]
    local old_tsi = redis.call('HGET', bus_key, 'tsi')
    if not old_tsi or new_tsi > tonumber(old_tsi) then
        redis.call('HSET', bus_key, 'data', new_data, 'tsi', new_tsi)
        redis.call('EXPIRE', bus_key, 600)
        return 1
    end
    return 0
    """
    update_latest = redis_client.register_script(LUA_POSITION_SCRIPT)

    with redis_client.pipeline() as pipe:
        count = 0
        for row in chain([first_row], iterator):
            bus_id = f"bus:{row['unique_veh_id']}"
            tsi = row["tsi"]
            payload = {
                "lat": float(row["lat"]),
                "long": float(row["long"]),
                "spd": float(row["spd"]),
                "hdg": int(row["hdg"]),
                "tst": str(row["tst"]),
                "desi": str(row["desi"]),
            }
            update_latest(keys=[bus_id], args=[tsi, json.dumps(payload)], client=pipe)
            count += 1
            if count % 500 == 0:
                pipe.execute()

        if count % 500 != 0:
            pipe.execute()


def write_position_to_redis(
    batch_df: DataFrame,
    batch_id: int,
    redis_host: str,
    redis_port: int,
    redis_password=None,
):
    """
    Write current bus positions to Redis for real-time tracking.

    Args:
        batch_df: DataFrame containing position data
        batch_id: Batch ID from Spark Streaming
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_password: Redis password (unused, but kept for compatibility)
    """
    try:
        batch_df.foreachPartition(
            lambda iterator: _process_position_partition(
                iterator, redis_host, redis_port, redis_password
            )
        )
        logger.info(f"💾 Batch {batch_id}: Dispatched position updates to Redis")
    except Exception as exc:
        logger.error(f"❌ Error dispatching Redis position writes: {exc}")
        raise


def _process_speed_partition(
    iterator, redis_host: str, redis_port: int, redis_password=None
):
    """
    Process a partition of speed/traffic data and write to Redis.

    Uses Lua scripting to ensure only the most recent traffic status is stored.

    Args:
        iterator: Row iterator from Spark partition
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_password: Redis password (unused, but kept for compatibility)
    """
    try:
        first_row = next(iterator)
    except StopIteration:
        return

    from itertools import chain

    redis_client = _get_redis_client(redis_host, redis_port)

    LUA_TRAFFIC_SCRIPT = """
    local bus_key = KEYS[1]
    local new_window_end = ARGV[1]
    local avg_speed = ARGV[2]
    local is_stuck = ARGV[3]

    local old_window_end = redis.call('HGET', bus_key, 'window_end_time')

    if not old_window_end or new_window_end >= old_window_end then
        redis.call('HSET', bus_key,
            'window_end_time', new_window_end,
            'window_avg_speed', avg_speed,
            'is_stuck', is_stuck
        )
        return 1
    end
    return 0
    """
    update_traffic = redis_client.register_script(LUA_TRAFFIC_SCRIPT)

    with redis_client.pipeline() as pipe:
        count = 0
        for row in chain([first_row], iterator):
            bus_id = f"bus:{row['unique_veh_id']}"
            avg_speed = round(row["avg_speed"], 2)
            window_end = str(row["window_end"])
            is_stuck = (
                "True"
                if (row["observed_duration_seconds"] >= 180) and (row["avg_speed"] < 4)
                else "False"
            )
            update_traffic(
                keys=[bus_id],
                args=[window_end, avg_speed, is_stuck],
                client=pipe,
            )
            count += 1
            if count % 500 == 0:
                pipe.execute()

        if count % 500 != 0:
            pipe.execute()


def write_speed_avg_to_redis(
    batch_df: DataFrame,
    batch_id: int,
    redis_host: str,
    redis_port: int,
    redis_password=None,
):
    """
    Write aggregated speed data and traffic status to Redis.

    Deduplicates by keeping only the most recent window per vehicle.

    Args:
        batch_df: DataFrame containing aggregated speed data
        batch_id: Batch ID from Spark Streaming
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_password: Redis password (unused, but kept for compatibility)
    """
    window_spec = SparkWindow.partitionBy("unique_veh_id").orderBy(
        col("window_end").desc()
    )
    final_df = (
        batch_df.withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    try:
        final_df.foreachPartition(
            lambda iterator: _process_speed_partition(
                iterator, redis_host, redis_port, redis_password
            )
        )
        logger.info(f"💾 Batch {batch_id}: Dispatched speed/traffic data to Redis")
    except Exception as exc:
        logger.error(f"❌ Error dispatching speed/traffic writes: {exc}")
        raise


def write_position_to_redis_query(
    clean_df: DataFrame, redis_host: str, redis_port: int, redis_password=None
):
    """
    Create a streaming query to continuously write positions to Redis.

    Args:
        clean_df: Cleaned DataFrame with position data
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_password: Redis password (unused, but kept for compatibility)

    Returns:
        StreamingQuery object
    """
    return (
        clean_df.select(
            "unique_veh_id",
            "tst",
            "tsi",
            "lat",
            "long",
            "spd",
            "hdg",
            "desi",
        )
        .writeStream.foreachBatch(
            lambda batch_df, batch_id: write_position_to_redis(
                batch_df, batch_id, redis_host, redis_port, redis_password
            )
        )
        .outputMode("update")
        .trigger(processingTime="1 second")
        .start()
    )


def write_speed_avg_to_redis_query(
    clean_df: DataFrame, redis_host: str, redis_port: int, redis_password=None
):
    """
    Create a streaming query to continuously write speed/traffic data to Redis.

    Args:
        clean_df: Cleaned DataFrame with event data
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_password: Redis password (unused, but kept for compatibility)

    Returns:
        StreamingQuery object
    """
    return (
        clean_df.withWatermark("tst", "1 minute")
        .groupBy(window(col("tst"), "5 minute", "1 minute"), col("unique_veh_id"))
        .agg(
            avg("spd").alias("avg_speed"),
            max_("tsi").alias("latest_msg_tsi"),
            min_("tsi").alias("earliest_msg_tsi"),
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("unique_veh_id"),
            col("avg_speed"),
            (col("latest_msg_tsi") - col("earliest_msg_tsi")).alias(
                "observed_duration_seconds"
            ),
        )
        .writeStream.foreachBatch(
            lambda batch_df, batch_id: write_speed_avg_to_redis(
                batch_df, batch_id, redis_host, redis_port, redis_password
            )
        )
        .outputMode("update")
        .trigger(processingTime="10 seconds")
        .start()
    )
