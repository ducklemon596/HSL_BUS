# ============================================================================
# WEB APPLICATION SERVICE - Cloud Run
# Serves real-time bus data while enforcing private network access for Redis/Kafka.
# Public endpoint exposure is intentionally disabled unless explicitly enabled.
# ============================================================================

resource "google_service_account" "app_service" {
  account_id   = var.app_service_account_id
  display_name = "Service Account for HSL Bus Web App"
  description  = "Service account for Cloud Run web application"
}

resource "google_project_iam_member" "app_logging_role" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

resource "google_project_iam_member" "app_monitoring_role" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

resource "google_project_iam_member" "app_artifact_registry_role" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

resource "google_project_iam_member" "app_redis_role" {
  project = var.project_id
  role    = "roles/redis.editor"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

resource "google_vpc_access_connector" "app_connector" {
  name           = var.app_vpc_connector_name
  region         = var.region
  network        = var.network_name
  ip_cidr_range  = var.app_vpc_cidr_range
  min_throughput = 200
  max_throughput = 300
}

resource "google_compute_firewall" "allow_app_to_redis" {
  name    = "hsl-allow-app-to-redis"
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = [tostring(var.redis_port)]
  }

  source_ranges = [var.app_vpc_cidr_range]
  target_tags   = [local.redis_firewall_tag]
}

resource "google_compute_firewall" "allow_app_to_kafka" {
  name    = "hsl-allow-app-to-kafka"
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = [tostring(var.kafka_port)]
  }

  source_ranges = [var.app_vpc_cidr_range]
  # Managed Kafka endpoint restriction is handled by the network path; target tags are not available for managed service brokers.
}

resource "google_cloud_run_service" "app" {
  name     = var.app_service_name
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.app_service.email

      containers {
        image = var.app_service_image

        env {
          name  = "REDIS_HOST"
          value = google_compute_instance.redis_server.network_interface[0].network_ip
        }

        env {
          name  = "REDIS_PORT"
          value = tostring(var.redis_port)
        }

        env {
          name  = "KAFKA_BROKERS"
          value = local.kafka_bootstrap_host
        }

        env {
          name  = "KAFKA_PORT"
          value = tostring(var.kafka_port)
        }

        env {
          name  = "KAFKA_TOPIC"
          value = google_managed_kafka_topic.bus_topic.topic_id
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "FLASK_HOST"
          value = var.flask_host
        }

        env {
          name  = "FLASK_PORT"
          value = tostring(var.flask_port)
        }

        resources {
          limits = {
            memory = var.cloud_run_memory
            cpu    = tostring(var.cloud_run_cpu)
          }
        }
      }

      timeout_seconds = var.cloud_run_timeout_seconds
    }

    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.app_connector.name
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
        "autoscaling.knative.dev/maxScale"        = var.cloud_run_max_instances
        "autoscaling.knative.dev/minScale"        = var.cloud_run_min_instances
      }
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
    google_vpc_access_connector.app_connector,
    google_project_iam_member.app_logging_role,
    google_project_iam_member.app_monitoring_role,
    google_project_iam_member.app_artifact_registry_role,
    google_project_iam_member.app_redis_role,
    time_sleep.wait_for_redis
  ]
}

resource "google_cloud_run_service_iam_member" "app_public_access" {
  count    = var.app_allow_unauthenticated ? 1 : 0
  service  = google_cloud_run_service.app.name
  location = google_cloud_run_service.app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "app_service_url" {
  description = "URL of the web application"
  value       = google_cloud_run_service.app.status[0].url
}

output "app_service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.app_service.email
}
