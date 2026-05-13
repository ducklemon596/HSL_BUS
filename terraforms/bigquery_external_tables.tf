resource "google_bigquery_dataset" "analytics" {
  dataset_id  = var.analytics_dataset_id
  project     = var.project_id
  location    = var.region
  description = "BigQuery dataset for bus analytics external tables."
  labels      = var.resource_labels
}

resource "google_bigquery_table" "bronze_bus_data" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "bronze_bus_data"
  project    = var.project_id

  friendly_name = "Bus Bronze Layer External Table"
  description   = "External BigQuery table reading raw Bronze Parquet data from GCS with Hive partitioning."

  external_data_configuration {
    source_format = "PARQUET"
    source_uris   = ["gs://${var.data_lake_bucket}/bronze_layer/year=*"]
    autodetect    = true

    hive_partitioning_options {
      mode                     = "AUTO"
      source_uri_prefix        = "gs://${var.data_lake_bucket}/bronze_layer/"
      require_partition_filter = false
    }
  }
}

resource "google_bigquery_table" "silver_bus_data" {
  provider   = google-beta
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "silver_bus_data"
  project    = var.project_id

  friendly_name = "Bus Silver Layer External Table"
  description   = "External BigQuery table reading cleaned Silver Delta Lake data from GCS."

  external_data_configuration {
    source_format = "DELTA_LAKE"
    source_uris   = ["gs://${var.data_lake_bucket}/silver_layer/"]
    autodetect    = true
  }
}
