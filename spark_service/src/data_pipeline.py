from pyspark.sql import DataFrame
from pyspark.sql.functions import col

from shared_lib import get_settings_instance

settings_instance = get_settings_instance()


def clean_bus_data(raw_df: DataFrame) -> DataFrame:
    return raw_df.filter(
        col("unique_veh_id").isNotNull()
        & col("lat").between(
            settings_instance.LOCATION_LAT_MIN,
            settings_instance.LOCATION_LAT_MAX,
        )
        & col("long").between(
            settings_instance.LOCATION_LONG_MIN,
            settings_instance.LOCATION_LONG_MAX,
        )
        & (col("spd") >= settings_instance.MIN_SPEED)
        & (col("spd") <= settings_instance.MAX_SPEED)
        & col("hdg").between(
            settings_instance.MIN_HEADING,
            settings_instance.MAX_HEADING,
        )
        & (col("occu") >= 0)
    )
