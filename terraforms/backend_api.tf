# ============================================================================
# BACKEND SERVICE - Cloud Run
# Serves analytics queries from BigQuery external tables.
# ============================================================================

# Dedicated Service Account for the Backend
resource "google_service_account" "bus_backend_sa" {
  account_id   = "bus-backend-sa"
  display_name = "Service Account for Bus Analytics Backend"
  description  = "Service account for Cloud Run backend"
}

# IAM Role Bindings for the Service Account
resource "google_project_iam_member" "bus_backend_bigquery_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.bus_backend_sa.email}"
}

resource "google_project_iam_member" "bus_backend_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.bus_backend_sa.email}"
}

resource "google_project_iam_member" "bus_backend_storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.bus_backend_sa.email}"
}

resource "google_project_iam_member" "bus_backend_artifact_registry_role" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.bus_backend_sa.email}"
}

# VPC Access Connector for the Backend
resource "google_vpc_access_connector" "backend_connector" {
  name           = "bus-backend-vpc-conn"
  region         = var.region
  network        = google_compute_network.vpc_network.name
  ip_cidr_range  = var.backend_vpc_cidr_range
  min_throughput = 200
  max_throughput = 300
}

# Firewall rule to allow Backend to access Redis
resource "google_compute_firewall" "allow_bus_backend_to_redis" {
  name    = "hsl-allow-bus-backend-to-redis"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = [tostring(var.redis_port)]
  }

  source_ranges = [var.backend_vpc_cidr_range]
  target_tags   = [local.redis_firewall_tag]
}

# Cloud Run Service for the Backend
resource "google_cloud_run_service" "bus_analytics_backend" {
  name     = "bus-analytics-backend"
  location = var.region

  template {
    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.backend_connector.id
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
        "autoscaling.knative.dev/maxScale"        = var.cloud_run_max_instances
        "autoscaling.knative.dev/minScale"        = var.cloud_run_min_instances
      }
    }
    
    spec {
      service_account_name = google_service_account.bus_backend_sa.email

      containers {
        image = var.backend_image

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "DATASET_ID"
          value = var.analytics_dataset_id
        }

        env {
          name  = "REDIS_HOST"
          value = google_compute_instance.redis_server.network_interface[0].network_ip
        }

        env {
          name  = "REDIS_PORT"
          value = tostring(var.redis_port)
        }

        resources {
          limits = {
            cpu    = "1000m" # 1 vCPU
            memory = "512Mi" # 512MB Memory
          }
        }
      }

      timeout_seconds = var.cloud_run_timeout_seconds
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_compute_instance.redis_server,
    google_managed_kafka_cluster.bus_kafka,
    google_managed_kafka_topic.bus_topic,
    google_dataproc_cluster.spark_cluster,
    google_compute_instance.ingestion_vm,
    google_vpc_access_connector.backend_connector,
    google_project_iam_member.bus_backend_artifact_registry_role,
    google_project_iam_member.bus_backend_bigquery_viewer,
    google_project_iam_member.bus_backend_bigquery_job_user,
    google_project_iam_member.bus_backend_storage_viewer,
    time_sleep.wait_for_redis
  ]
}

# Allow unauthenticated access to the Cloud Run service
resource "google_cloud_run_service_iam_member" "bus_backend_invoker" {
  service  = google_cloud_run_service.bus_analytics_backend.name
  location = google_cloud_run_service.bus_analytics_backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}