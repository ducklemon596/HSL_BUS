# ============================================================================
# WEB APPLICATION SERVICE - Cloud Run
# Serves real-time bus data via Flask with SocketIO
# Auto-scales to zero when no external requests (cost optimization)
# ============================================================================

# Service Account for Cloud Run Web App
resource "google_service_account" "app_service" {
  account_id   = "hsl-app-service"
  display_name = "Service Account for HSL Bus Web App"
  description  = "Service account for Cloud Run web application"
}

# Grant Cloud Run permissions
resource "google_project_iam_member" "app_cloud_run_role" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

# Grant Cloud Logging permissions
resource "google_project_iam_member" "app_logging_role" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

# Grant Cloud Monitoring permissions
resource "google_project_iam_member" "app_monitoring_role" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

# Grant Redis access (if using Cloud Memorystore Redis)
# For GCE VM Redis: The app will access via environment variable IP
resource "google_project_iam_member" "app_redis_role" {
  project = var.project_id
  role    = "roles/redis.editor"
  member  = "serviceAccount:${google_service_account.app_service.email}"
}

# VPC Connector for Cloud Run to access private resources (Redis VM, Kafka)
resource "google_vpc_access_connector" "app_connector" {
  name            = "hsl-app-vpc-connector"
  region          = var.region
  ip_cidr_range   = "10.10.0.0/28"
  network         = "default"
  min_throughput  = 200
  max_throughput  = 300
}

# Firewall rule to allow Cloud Run (via VPC connector) to access Redis
resource "google_compute_firewall" "allow_app_to_redis" {
  name    = "hsl-allow-app-to-redis"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["6379"]  # Redis port
  }

  source_ranges = ["10.10.0.0/28"]  # VPC connector range
  target_tags   = ["allow-redis-internal"]
}

# Firewall rule to allow Cloud Run to access Kafka
resource "google_compute_firewall" "allow_app_to_kafka" {
  name    = "hsl-allow-app-to-kafka"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["9092"]  # Kafka broker
  }

  source_ranges = ["10.10.0.0/28"]  # VPC connector range
}

# Cloud Run Web Application Service
resource "google_cloud_run_service" "app" {
  name     = "hsl-bus-web-app"
  location = var.region

  template {
    spec {
      # Service account for the Cloud Run instance
      service_account_name = google_service_account.app_service.email

      # Container configuration
      containers {
        image = var.app_service_image

        # Environment variables for application configuration
        env {
          name  = "REDIS_HOST"
          value = google_compute_instance.redis_server.network_interface[0].network_ip
        }

        env {
          name  = "REDIS_PORT"
          value = "6379"
        }

        env {
          name  = "KAFKA_BROKER"
          value = google_managed_kafka_cluster.bus_kafka.bootstrap_config[0].vpc_configs[0].bootstrap_address
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
          value = "0.0.0.0"
        }

        env {
          name  = "FLASK_PORT"
          value = "8080"
        }

        # Resource requests and limits
        resources {
          limits = {
            memory = var.cloud_run_memory
            cpu    = tostring(var.cloud_run_cpu)
          }
        }
      }

      # Timeout for requests
      timeout_seconds = var.cloud_run_timeout_seconds

      # Concurrency settings
      concurrency = 80
    }

    # Metadata for VPC connector
    metadata {
      annotations = {
        "run.googleapis.com/vpc-access-connector"  = google_vpc_access_connector.app_connector.name
        "run.googleapis.com/vpc-access-egress"     = "private-ranges-only"
        "autoscaling.knative.dev/maxScale"         = var.cloud_run_max_instances
        "autoscaling.knative.dev/minScale"         = var.cloud_run_min_instances
      }
    }
  }

  # Traffic configuration
  traffic {
    percent         = 100
    latest_revision = true
  }

  # Depends on all backend services being ready
  depends_on = [
    google_compute_instance.redis_server,
    google_managed_kafka_cluster.bus_kafka,
    google_managed_kafka_topic.bus_topic,
    google_dataproc_cluster.spark_cluster,
    google_compute_instance.ingestion_vm,
    google_vpc_access_connector.app_connector,
    google_project_iam_member.app_cloud_run_role
  ]
}

# Allow unauthenticated access to the web app (public)
resource "google_cloud_run_service_iam_member" "app_public_access" {
  service       = google_cloud_run_service.app.name
  location      = google_cloud_run_service.app.location
  role          = "roles/run.invoker"
  member        = "allUsers"
}

# ============================================================================
# OUTPUTS - Web Application Information
# ============================================================================

output "app_service_url" {
  description = "URL of the web application (public endpoint)"
  value       = google_cloud_run_service.app.status[0].url
}

output "app_service_account_email" {
  description = "Email of the app service account"
  value       = google_service_account.app_service.email
}
