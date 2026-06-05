# /**
#  * IAM for Airflow initialization workers.
#  *
#  * Airflow owns one-time initialization actions that depend on runtime data
#  * already existing in GCS, such as creating BigQuery external tables after
#  * Spark Streaming writes the first Bronze/Silver batch. Terraform intentionally
#  * does not create those external tables.
#  */

# resource "google_service_account" "airflow_worker" {
#   account_id   = "airflow-worker-sa"
#   display_name = "Airflow Worker Service Account"
#   description  = "Runs Bus HSL Airflow initialization DAGs for BigQuery external tables."
#   project      = var.project_id
# }

# # Allows the GCS sensor and BigQuery external table metadata to inspect objects
# # in the data lake bucket without granting write or bucket-admin permissions.
# resource "google_storage_bucket_iam_member" "airflow_data_lake_object_viewer" {
#   bucket = google_storage_bucket.data_lake.name
#   role   = "roles/storage.objectViewer"
#   member = "serviceAccount:${google_service_account.airflow_worker.email}"
# }

# # Allows Airflow to submit BigQuery DDL jobs in the project.
# resource "google_project_iam_member" "airflow_bigquery_job_user" {
#   project = var.project_id
#   role    = "roles/bigquery.jobUser"
#   member  = "serviceAccount:${google_service_account.airflow_worker.email}"
# }

# # Allows Airflow to create and replace tables only inside the analytics dataset.
# resource "google_bigquery_dataset_iam_member" "airflow_analytics_data_editor" {
#   project    = var.project_id
#   dataset_id = google_bigquery_dataset.analytics.dataset_id
#   role       = "roles/bigquery.dataEditor"
#   member     = "serviceAccount:${google_service_account.airflow_worker.email}"
# }

# output "airflow_worker_service_account_email" {
#   description = "Service account email for Airflow workers running initialization DAGs."
#   value       = google_service_account.airflow_worker.email
# }
