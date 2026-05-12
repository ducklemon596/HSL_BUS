#!/bin/bash
set -e

echo "🚀 Starting automated environment setup for HSL Bus..."

# 1. Install required Python libraries
echo "📦 Installing Python libraries..."
pip3 install redis python-dotenv delta-spark==2.3.0

# 2. Prepare workspace
mkdir -p /tmp/kafka-setup
cd /tmp/kafka-setup

# 3. Download EVERYTHING needed
echo "📥 Downloading all dependencies..."
# - Managed Kafka Auth (The Key)
wget -q https://github.com/googleapis/managedkafka/releases/download/v1.0.6/release-and-dependencies.zip
unzip -q release-and-dependencies.zip

# - Spark-Kafka Connectors & Pool2 (The Engine)
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.3.2/spark-sql-kafka-0-10_2.12-3.3.2.jar
wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.3.2/spark-token-provider-kafka-0-10_2.12-3.3.2.jar
wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

# - Delta Lake libraries
wget -q https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.3.0/delta-core_2.12-2.3.0.jar
wget -q https://repo1.maven.org/maven2/io/delta/delta-storage/2.3.0/delta-storage-2.3.0.jar

# 4. INSTALL ALL TO SPARK JARS (The Master Stroke)
echo "🏗️ Installing all Jars into Spark system path..."
# Vét sạch mọi file .jar trong thư mục hiện tại và các thư mục con
# TRỪ các file jackson-*.jar để tránh xung đột phiên bản (dùng bản 2.13.x có sẵn của cụm)
sudo find . -type f -name "*.jar" ! -name "jackson-*.jar" -exec cp {} /usr/lib/spark/jars/ \;

sudo chmod 644 /usr/lib/spark/jars/*.jar

# 5. Clean up
cd /
rm -rf /tmp/kafka-setup

echo "✅ Dataproc cluster is fully equipped and ready for action!"