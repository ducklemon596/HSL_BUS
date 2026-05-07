import json
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, row_number, avg, max as max_, min as min_, window
from pyspark.sql.window import Window as SparkWindow

from shared_lib import get_logger_instance, get_settings_instance

logger = get_logger_instance(__name__)
settings_instance = get_settings_instance()


def _get_redis_client():
    import redis

    if not hasattr(redis, "_my_global_client"):
        pool = redis.ConnectionPool(
            host=settings_instance.REDIS_HOST,
            port=settings_instance.REDIS_PORT,
            password=getattr(settings_instance, "REDIS_PASSWORD", None),
            decode_responses=True,
            max_connections=10,
        )
        redis._my_global_client = redis.Redis(connection_pool=pool)

    return redis._my_global_client


def _process_position_partition(iterator):
    try:
        first_row = next(iterator)
    except StopIteration:
        return

    from itertools import chain

    redis_client = _get_redis_client()

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
            bus_id = row["unique_veh_id"]
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


def write_position_to_redis(batch_df: DataFrame, batch_id: int):
    try:
        batch_df.foreachPartition(_process_position_partition)
        logger.info(f"💾 Batch {batch_id}: Dispatched writes to Redis via Workers")
    except Exception as exc:
        logger.error(f"❌ Error dispatching Redis writes: {exc}")


def _process_speed_partition(iterator):
    try:
        first_row = next(iterator)
    except StopIteration:
        return

    from itertools import chain

    redis_client = _get_redis_client()

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
            bus_id = row["unique_veh_id"]
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


def write_speed_avg_to_redis(batch_df: DataFrame, batch_id: int):
    window_spec = SparkWindow.partitionBy("unique_veh_id").orderBy(
        col("window_end").desc()
    )
    final_df = (
        batch_df.withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    try:
        final_df.foreachPartition(_process_speed_partition)
        logger.info(
            f"💾 Batch {batch_id}: Dispatched speed averages to Redis via Workers"
        )
    except Exception as exc:
        logger.error(f"❌ Error dispatching speed averages writes: {exc}")


def write_position_to_redis_query(clean_df: DataFrame):
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
        .writeStream.foreachBatch(write_position_to_redis)
        .outputMode("update")
        .trigger(processingTime="1 second")
        .start()
    )


def write_speed_avg_to_redis_query(clean_df: DataFrame):
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
        .writeStream.foreachBatch(write_speed_avg_to_redis)
        .outputMode("update")
        .trigger(processingTime="10 seconds")
        .start()
    )
