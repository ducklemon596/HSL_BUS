# DATAPROC (SPARK) - 1 MASTER + 2 WORKERS
resource "google_dataproc_cluster" "spark_cluster" {
  name   = var.dataproc_cluster_name
  region = var.region

  labels = local.common_labels

  cluster_config {
    # Master node
    master_config {
      num_instances = 1
      machine_type  = var.dataproc_master_machine_type
      disk_config {
        boot_disk_size_gb = var.dataproc_master_disk_size_gb
        boot_disk_type    = var.dataproc_master_disk_type
      }
    }

    # Worker nodes
    worker_config {
      num_instances = var.dataproc_worker_num_instances
      machine_type  = var.dataproc_worker_machine_type
      disk_config {
        boot_disk_size_gb = var.dataproc_worker_disk_size_gb
        boot_disk_type    = var.dataproc_worker_disk_type
      }
    }

    # OS and jar dependencies
    software_config {
      image_version = var.dataproc_image_version
    }

    # Initialization actions for cluster setup
    initialization_action {
      script      = "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_setup_script.name}"
      timeout_sec = 120 # 2 minutes timeout
    }

    # Service Account & IAM Scopes
    gce_cluster_config {
      service_account = google_service_account.spark_worker.email
      service_account_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]

      subnetwork = google_compute_subnetwork.bus_subnet.id

      # BẢO MẬT: Không cấp IP Public cho cụm Spark.
      # Nó sẽ dùng Cloud NAT của bus_subnet để ra mạng tải thư viện.
      internal_ip_only = true

      tags = [local.dataproc_node_tag]
    }

    # Enable component gateway (Spark UI, YARN)
    endpoint_config {
      enable_http_port_access = true
    }
  }

  depends_on = [
    time_sleep.wait_for_iam,
    google_storage_bucket_object.upload_setup_script
  ]

  lifecycle {
    ignore_changes = [
      cluster_config[0].software_config[0].image_version,
      cluster_config[0].software_config[0].properties,
      cluster_config[0].gce_cluster_config[0].service_account_scopes,
      cluster_config[0].bucket,
    ]
  }
}

resource "time_sleep" "wait_for_dataproc" {
  depends_on      = [google_dataproc_cluster.spark_cluster]
  create_duration = "120s"
}

resource "google_compute_firewall" "allow_dataproc_internal" {
  name    = "hsl-allow-dataproc-internal"
  network = google_compute_network.vpc_network.id

  allow {
    protocol = "icmp" # Cho phép ping
  }
  allow {
    protocol = "tcp"
    ports    = ["0-65535"] # Mở hết cổng cho nội bộ Dataproc
  }
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  # Quan trọng: Chỉ cho phép các máy có tag Dataproc nói chuyện với nhau
  source_tags = [local.dataproc_node_tag]
  target_tags = [local.dataproc_node_tag]
}

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

# Kafka Admin role for Spark to consume from Kafka
resource "google_project_iam_member" "spark_kafka_role" {
  project = var.project_id
  role    = "roles/managedkafka.admin"
  member  = "serviceAccount:${google_service_account.spark_worker.email}"
}

# Sleep to synchronize IAM role propagation before creating the cluster
resource "time_sleep" "wait_for_iam" {
  depends_on = [
    google_project_iam_member.dataproc_worker_role,
    google_project_iam_member.storage_admin_role
  ]

  create_duration = "45s"
}