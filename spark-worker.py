import pyspark
from pyspark.sql.functions import window, avg, col, from_json
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    LongType,
    IntegerType,
)
import os

spark_version = pyspark.__version__
kafka_package = f"org.apache.spark:spark-sql-kafka-0-10_2.12:{spark_version}"

spark = (
    SparkSession.builder.config("spark.jars.packages", kafka_package)
    .appName("BusDataProcessing")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

print("👷 Đã khởi tạo Spark Session")
kafka_bookstrap_servers = os.getenv("KAFKA_BROKER", "kafka:9092")

vp_schema = StructType(
    [
        StructField("desi", StringType(), True),  # Số hiệu tuyến (VD: 37)
        StructField("dir", StringType(), True),  # Chiều đi (1 hoặc 2)
        StructField("oper", IntegerType(), True),  # Mã nhà xe (VD: 22)
        StructField("veh", IntegerType(), True),  # Biển số xe (VD: 1219)
        StructField(
            "unique_veh_id", StringType(), True
        ),  # Trường do ta tự chế ở bước Ingestion để đảm bảo mỗi xe có một ID duy nhất (VD: "22_1219")
        StructField(
            "tst", StringType(), True
        ),  # Thời gian chuẩn ISO (Khuyên dùng String lúc đầu cho an toàn)
        StructField(
            "tsi", LongType(), True
        ),  # Thời gian Unix (Số rất to nên dùng LongType)
        StructField("spd", DoubleType(), True),  # Tốc độ m/s (Số thực)
        StructField("hdg", IntegerType(), True),  # Hướng di chuyển (Độ)
        StructField("lat", DoubleType(), True),  # Vĩ độ
        StructField("long", DoubleType(), True),  # Kinh độ
        StructField("acc", DoubleType(), True),  # Gia tốc
        StructField(
            "dl", IntegerType(), True
        ),  # Độ trễ (Giây, âm là đi nhanh, dương là đi chậm)
        StructField("odo", DoubleType(), True),  # Công tơ mét (Có thể null)
        StructField("drst", IntegerType(), True),  # Trạng thái cửa (0/1, có thể null)
        StructField("oday", StringType(), True),  # Ngày chạy
        StructField("jrn", IntegerType(), True),  # Mã chuyến đi
        StructField("line", IntegerType(), True),  # Mã luồng tuyến
        StructField("start", StringType(), True),  # Giờ khởi hành
        StructField("loc", StringType(), True),  # Loại định vị (GPS)
        StructField("stop", StringType(), True),  # Trạm dừng hiện tại
        StructField("route", StringType(), True),  # Mã định tuyến
        StructField("occu", IntegerType(), True),  # Số lượng khách (0 = rỗng)
    ]
)

# ĐỊNH NGHĨA LỚP BÊN NGOÀI CÙNG
bus_schema = StructType([StructField("VP", vp_schema, True)])

raw_df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", kafka_bookstrap_servers)
    .option("subscribe", "hsl_bus")
    .option("startingOffsets", "earliest")
    .load()
)

string_df = raw_df.selectExpr(
    "CAST(key AS STRING) as key", "CAST(value AS STRING) as json_str"
)

stream_df = string_df.withColumn("data", from_json(col("json_str"), bus_schema)).select(
    "data.VP.*"
)

query = (
    stream_df.writeStream.format("console")
    .outputMode("append")
    .option("truncate", "false")
    .option("checkpointLocation", "/home/jovyan/work/checkpoints/bus_hsl/")
    .start()
)

query.awaitTermination()
