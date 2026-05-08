#!/bin/bash
set -e  # Exit on any error

echo "🚀 Starting environment setup for HSL Bus Project on Dataproc..."

apt-get update
# Sửa 'dotenv' thành 'python-dotenv' cho đúng chuẩn thư viện Python
pip3 install redis python-dotenv delta-spark==2.3.0

# Create a temporary directory to store the downloaded jars
mkdir -p /tmp/spark-jars
cd /tmp/spark-jars

# Install Kafka connector jars
# This is necessary for Spark to read/write data from/to Kafka topics.
# We need both the main connector and its dependencies.
echo "📦 Downloading Kafka connector jars..."
wget https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.3.2/spark-sql-kafka-0-10_2.12-3.3.2.jar
wget https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar
wget https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.3.2/spark-token-provider-kafka-0-10_2.12-3.3.2.jar
wget https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

# Install GCP Managed Kafka Auth jar
# This handles the passwordless IAM authentication for Google Cloud
echo "📦 Downloading GCP Managed Kafka Auth jar..."
wget https://repo1.maven.org/maven2/com/google/cloud/hosted/kafka/managed-kafka-auth-login-handler/1.0.6/managed-kafka-auth-login-handler-1.0.6.jar

# Install Delta Lake jars
echo "📦 Downloading Delta Lake jars..."
wget https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.3.0/delta-core_2.12-2.3.0.jar
wget https://repo1.maven.org/maven2/io/delta/delta-storage/2.3.0/delta-storage-2.3.0.jar

# Copy the downloaded jars to Spark's jars directory
echo "📦 Installing jars to Spark..."
sudo cp *.jar /usr/lib/spark/jars/

# Clean up the temporary directory
cd /
rm -rf /tmp/spark-jars

echo "👷 Environment setup complete for HSL Bus Project!"