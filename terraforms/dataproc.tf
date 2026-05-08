# DATAPROC (SPARK) - 1 MASTER + 2 WORKERS
resource "google_dataproc_cluster" "spark_cluster" {
  name   = "hsl-spark-cluster"
  region = "asia-southeast1"

  cluster_config {
    # Master node
    master_config {
      num_instances = 1
      machine_type  = "e2-standard-2" # 2 vCPU, 8GB RAM
      disk_config {
        boot_disk_size_gb = 50
        boot_disk_type    = "pd-standard"
      }
    }

    # Worker nodes
    worker_config {
      num_instances = 2
      machine_type  = "e2-standard-2" # 4 vCPU, 16GB RAM 
      disk_config {
        boot_disk_size_gb = 50
        boot_disk_type    = "pd-standard"
      }
    }

    # OS
    software_config {
      image_version = "2.1-debian11"
    }

    # Initialization actions for cluster setup
    initialization_action {
      script      = "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_setup_script.name}"
      timeout_sec = 600 # 10 minutes timeout
    }

    # Service Account & IAM Scopes
    gce_cluster_config {
      service_account = google_service_account.spark_worker.email
      service_account_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]

      tags = ["bus-dataproc-node"]
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
}

# Sleep to synchronize IAM role propagation before creating the cluster
resource "time_sleep" "wait_for_iam" {
  depends_on = [
    google_project_iam_member.dataproc_worker_role,
    google_project_iam_member.storage_admin_role
  ]

  create_duration = "45s"
}