from pyspark.sql import DataFrame
from pyspark.sql.functions import col

from shared_lib.settings import get_settings_instance


def clean_bus_data(raw_df: DataFrame) -> DataFrame:
    """
    Apply data quality filters and validation rules to raw bus data.

    Filters based on geographic bounds, speed ranges, and heading ranges.
    All configuration values are obtained from the centralized settings instance.

    Args:
        raw_df: Raw DataFrame from Kafka

    Returns:
        Cleaned DataFrame with validation filters applied

    Raises:
        RuntimeError: If settings haven't been initialized
    """
    config = get_settings_instance()
    config.assert_initialized()

    return raw_df.filter(
        col("unique_veh_id").isNotNull()
        & col("lat").between(
            config.LOCATION_LAT_MIN,
            config.LOCATION_LAT_MAX,
        )
        & col("long").between(
            config.LOCATION_LONG_MIN,
            config.LOCATION_LONG_MAX,
        )
        & (col("spd") >= config.MIN_SPEED)
        & (col("spd") <= config.MAX_SPEED)
        & col("hdg").between(
            config.MIN_HEADING,
            config.MAX_HEADING,
        )
        & (col("occu") >= 0)
    )
