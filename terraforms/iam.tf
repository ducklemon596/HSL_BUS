# Init service account for Spark Workers 
resource "google_service_account" "spark_worker" {
  account_id   = "dataproc-spark-worker"
  display_name = "Service Account for Dataproc Spark Workers"
  description  = "Grant permissions for Spark workers to access Dataproc and Storage"
}

# Dataproc standard role
resource "google_project_iam_member" "dataproc_worker_role" {
  project = var.project_id
  role    = "roles/dataproc.worker"
  member  = "serviceAccount:${google_service_account.spark_worker.email}"
}

# GCS read/write access role
resource "google_project_iam_member" "storage_admin_role" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.spark_worker.email}"
}