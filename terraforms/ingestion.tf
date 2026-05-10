# ============================================================================
# INGESTION SERVICE - MQTT to Kafka Bridge
# This VM hosts the ingestion agent and is restricted to private network access.
# ============================================================================

resource "google_service_account" "ingestion_service" {
  account_id   = var.ingestion_service_account_id
  display_name = "Service Account for HSL Bus Ingestion"
  description  = "Service account for MQTT to Kafka ingestion service on VM"
}

resource "google_project_iam_member" "ingestion_kafka_role" {
  project = var.project_id
  role    = "roles/managedkafka.admin"
  member  = "serviceAccount:${google_service_account.ingestion_service.email}"
}

resource "google_project_iam_member" "ingestion_logging_role" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.ingestion_service.email}"
}

resource "google_project_iam_member" "ingestion_ar_reader_role" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.ingestion_service.email}"
}

resource "time_sleep" "wait_for_ingestion_iam" {
  depends_on = [
    google_project_iam_member.ingestion_kafka_role,
    google_project_iam_member.ingestion_logging_role,
    google_project_iam_member.ingestion_ar_reader_role
  ]

  create_duration = "30s"
}

resource "google_compute_firewall" "allow_ingestion_to_kafka" {
  name    = var.ingestion_firewall_name
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = [tostring(var.kafka_port)]
  }

  source_tags = [local.ingestion_node_tag]
  # Managed Kafka targets cannot be tagged like compute instances.
  depends_on = [google_managed_kafka_cluster.bus_kafka]
}

resource "google_compute_instance" "ingestion_vm" {
  name         = var.ingestion_vm_name
  machine_type = var.ingestion_vm_machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
    }
  }

  metadata = {
    gce-container-declaration = replace(<<-EOT
      spec:
        containers:
          - name: bus-ingestion
            image: ${var.region}-docker.pkg.dev/${var.project_id}/${var.repo_name}/ingestion-app:latest
            env:
              - name: KAFKA_BROKERS
                value: ${local.kafka_bootstrap_host}
              - name: KAFKA_PORT
                value: ${tostring(var.kafka_port)}
            restartPolicy: Always
        restartPolicy: Always
    EOT
    , "\r", "")
  }

  network_interface {
    network = var.network_name
  }

  service_account {
    email  = google_service_account.ingestion_service.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  tags   = [local.ingestion_node_tag]
  labels = local.common_labels

  depends_on = [
    time_sleep.wait_for_ingestion_iam,
    time_sleep.wait_for_kafka,
    google_managed_kafka_topic.bus_topic
  ]
}

output "ingestion_vm_internal_ip" {
  description = "Internal IP of the ingestion VM"
  value       = google_compute_instance.ingestion_vm.network_interface[0].network_ip
}

output "ingestion_service_account_email" {
  description = "Email of the ingestion service account"
  value       = google_service_account.ingestion_service.email
}
