from pyspark.sql import SparkSession
from shared_lib.logger import get_logger_instance

logger = get_logger_instance(__name__)


def create_spark_session() -> SparkSession:
    spark = (
        SparkSession.builder.appName("HSL_Bus_Pipeline")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.databricks.delta.optimizeWrite.enabled", "true")
        .config("spark.databricks.delta.autoCompact.enabled", "true")
        .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")
    logger.info("👷 Spark Session created for Dataproc")
    return spark
