from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    LongType,
    IntegerType,
)

VP_SCHEMA = StructType(
    [
        StructField("desi", StringType(), True),
        StructField("dir", StringType(), True),
        StructField("oper", IntegerType(), True),
        StructField("veh", IntegerType(), True),
        StructField("unique_veh_id", StringType(), True),
        StructField("tst", StringType(), True),
        StructField("tsi", LongType(), True),
        StructField("spd", DoubleType(), True),
        StructField("hdg", IntegerType(), True),
        StructField("lat", DoubleType(), True),
        StructField("long", DoubleType(), True),
        StructField("acc", DoubleType(), True),
        StructField("dl", IntegerType(), True),
        StructField("odo", DoubleType(), True),
        StructField("drst", IntegerType(), True),
        StructField("oday", StringType(), True),
        StructField("jrn", IntegerType(), True),
        StructField("line", IntegerType(), True),
        StructField("start", StringType(), True),
        StructField("loc", StringType(), True),
        StructField("stop", StringType(), True),
        StructField("route", StringType(), True),
        StructField("occu", IntegerType(), True),
    ]
)

BUS_SCHEMA = StructType([StructField("VP", VP_SCHEMA, True)])
