"""
Initialize Bus HSL BigQuery external tables after the streaming job writes data.

This DAG intentionally owns BigQuery external table creation instead of Terraform.
Terraform creates only the durable infrastructure: buckets, dataset, IAM, and
compute. Airflow waits for the first Delta Lake commit, then creates or replaces
the Bronze and Silver external tables with stable DDL.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectsWithPrefixExistenceSensor

PROJECT_ID = "hsl-bus-streaming-495014"
BUCKET_NAME = "hsl-bus-data-lake"
DATASET_ID = "bus_analytics"
LOCATION = "asia-southeast1"

BRONZE_TABLE_ID = "bronze_bus_data"
SILVER_TABLE_ID = "silver_bus_data"

default_args = {
    "owner": "data-platform",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="init_bus_hsl_bigquery_external_tables",
    description="Create Bus HSL BigQuery external tables after Spark writes the first batch.",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@once",
    catchup=False,
    max_active_runs=1,
    tags=["bus-hsl", "bigquery", "initialization"],
) as dag:
    wait_for_silver_delta_log = GCSObjectsWithPrefixExistenceSensor(
        task_id="wait_for_silver_delta_log",
        bucket=BUCKET_NAME,
        prefix="silver_layer/_delta_log/",
        poke_interval=60,
        timeout=60 * 60 * 6,
        mode="reschedule",
    )

    create_bronze_external_table = BigQueryInsertJobOperator(
        task_id="create_bronze_external_table",
        location=LOCATION,
        configuration={
            "query": {
                "query": f"""
                CREATE OR REPLACE EXTERNAL TABLE `{PROJECT_ID}.{DATASET_ID}.{BRONZE_TABLE_ID}`
                WITH PARTITION COLUMNS
                OPTIONS (
                  format = 'PARQUET',
                  uris = ['gs://{BUCKET_NAME}/bronze_layer/year=*'],
                  hive_partition_uri_prefix = 'gs://{BUCKET_NAME}/bronze_layer/',
                  require_hive_partition_filter = false
                )
                """,
                "useLegacySql": False,
            }
        },
    )

    create_silver_external_table = BigQueryInsertJobOperator(
        task_id="create_silver_external_table",
        location=LOCATION,
        configuration={
            "query": {
                "query": f"""
                CREATE OR REPLACE EXTERNAL TABLE `{PROJECT_ID}.{DATASET_ID}.{SILVER_TABLE_ID}`
                OPTIONS (
                  format = 'DELTA_LAKE',
                  uris = ['gs://{BUCKET_NAME}/silver_layer']
                )
                """,
                "useLegacySql": False,
            }
        },
    )

    wait_for_silver_delta_log >> [
        create_bronze_external_table,
        create_silver_external_table,
    ]
