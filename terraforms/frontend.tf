# ============================================================================
# FRONTEND SERVICE - Cloud Run
# Deploys the new Bus HSL UI frontend.
# ============================================================================

resource "google_service_account" "bus_frontend_sa" {
  account_id   = "bus-frontend-sa"
  display_name = "Service Account for Bus HSL Frontend"
  description  = "Service account used by Cloud Run frontend"
}

resource "google_project_iam_member" "bus_frontend_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.bus_frontend_sa.email}"
}

resource "google_cloud_run_service" "bus_frontend" {
  name     = "bus-frontend"
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.bus_frontend_sa.email

      containers {
        image = var.frontend_service_image

        env {
          name  = "BACKEND_API_URL"
          value = google_cloud_run_service.bus_analytics_backend.status[0].url
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "bus_frontend_invoker" {
  service  = google_cloud_run_service.bus_frontend.name
  location = google_cloud_run_service.bus_frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}