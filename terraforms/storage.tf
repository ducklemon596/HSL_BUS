/**
 * Terraform configuration for Google Cloud Storage buckets used in the HSL Bus Streaming project.
 * 
 * This module manages:
 * - Data Lake bucket: Stores bronze and silver layer data
 * - Spark Worker Assets bucket: Stores code, libraries, and scripts for Spark workers
 * 
 * Features:
 * - Versioning and lifecycle management
 * - Environment-based security settings
 * - Resource tagging for management and cost tracking
 * - Automated artifact packaging and upload
 */

# Local variables to reduce code repetition and centralize configuration
locals {
  common_labels = merge(
    var.resource_labels,
    {
      environment = var.environment
      created_at  = timestamp()
    }
  )

  data_lake_labels = merge(
    local.common_labels,
    {
      purpose = "data-lake"
    }
  )

  spark_worker_labels = merge(
    local.common_labels,
    {
      purpose = "spark-assets"
    }
  )
}

/**
 * Data Lake Bucket
 * 
 * Stores raw and processed data in bronze and silver layers.
 * - Uniform bucket-level access: Consistent access control
 * - Public access prevention: Enhanced security
 * - Versioning: Maintain historical versions of objects
 * - Lifecycle rules: Transition old data to cheaper storage classes
 */
resource "google_storage_bucket" "data_lake" {
  name          = var.data_lake_bucket
  location      = var.region
  force_destroy = var.force_destroy_bucket
  storage_class = var.bucket_storage_class

  labels = local.data_lake_labels

  uniform_bucket_level_access = true
  public_access_prevention = "enforced"

  # Enable versioning for data protection
  versioning {
    enabled = var.enable_versioning
  }

  # Lifecycle rules for cost optimization
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 180
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }
}

/**
 * Spark Worker Assets Bucket
 * 
 * Stores code, libraries, and scripts required for Spark job execution.
 * - Quick access needed (STANDARD storage class)
 * - Version control for artifact tracking
 * - Public access prevention for security
 */
resource "google_storage_bucket" "spark_worker_assets" {
  name          = var.spark_worker_bucket
  location      = var.region
  force_destroy = var.force_destroy_bucket
  storage_class = "STANDARD"

  labels = local.spark_worker_labels

  uniform_bucket_level_access = true
  public_access_prevention = "enforced"

  versioning {
    enabled = var.enable_versioning
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }
}

# ============================================================================
# Source Code Packaging
# ============================================================================

/**
 * Package the shared logic code into a zip file
 * Used for common utilities and shared functions across Spark workers
 */
data "archive_file" "shared_logic_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../${var.shared_logic_folder}"
  output_path = "${path.module}/tmp/shared_logic.zip"

  depends_on = []
}

/**
 * Package the main Spark job code into a zip file
 * Excludes main.py as it's uploaded separately
 */
data "archive_file" "source_code_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../${var.source_code_folder}"
  output_path = "${path.module}/tmp/src.zip"

  excludes = [
    "__pycache__",
    "*.pyc",
    ".pytest_cache"
  ]
}

# ============================================================================
# Artifact Upload
# ============================================================================

/**
 * Upload shared logic library to Spark Worker Assets bucket
 * Makes common code available to all Spark workers
 */
resource "google_storage_object" "upload_shared_logic" {
  name   = var.source_code_artifacts.shared_logic_path
  bucket = google_storage_bucket.spark_worker_assets.name
  source = data.archive_file.shared_logic_zip.output_path

  depends_on = [
    data.archive_file.shared_logic_zip,
    google_storage_object.libs_folder
  ]
}

/**
 * Upload main Spark worker script
 * Entry point for Spark job execution
 */
resource "google_storage_object" "upload_main_script" {
  name   = var.source_code_artifacts.main_script_path
  bucket = google_storage_bucket.spark_worker_assets.name
  source = "${path.module}/../${var.source_code_folder}/run_spark_worker.py"

  depends_on = [google_storage_object.code_folder]
}

/**
 * Upload compressed source code
 * Contains the main Spark data processing logic
 */
resource "google_storage_object" "upload_src_zip" {
  name   = var.source_code_artifacts.source_code_path
  bucket = google_storage_bucket.spark_worker_assets.name
  source = data.archive_file.source_code_zip.output_path

  depends_on = [
    data.archive_file.source_code_zip,
    google_storage_object.code_folder
  ]
}

/**
 * Upload setup environment script for Dataproc initialization
 * Used as startup script to install dependencies and configure Spark environment
 */
resource "google_storage_object" "upload_setup_script" {
  name   = var.source_code_artifacts.setup_script_path
  bucket = google_storage_bucket.spark_worker_assets.name
  source = "${path.module}/../${var.source_code_folder}/setup_env.sh"

  depends_on = [google_storage_object.code_folder]
}

# ============================================================================
# Outputs
# ============================================================================

output "data_lake_bucket_name" {
  description = "Name of the data lake bucket"
  value       = google_storage_bucket.data_lake.name
}

output "data_lake_bucket_url" {
  description = "URL of the data lake bucket"
  value       = "gs://${google_storage_bucket.data_lake.name}"
}

output "spark_worker_bucket_name" {
  description = "Name of the Spark worker assets bucket"
  value       = google_storage_bucket.spark_worker_assets.name
}

output "spark_worker_bucket_url" {
  description = "URL of the Spark worker assets bucket"
  value       = "gs://${google_storage_bucket.spark_worker_assets.name}"
}

output "artifact_paths" {
  description = "Paths to uploaded artifacts in Spark worker bucket"
  value = {
    shared_logic = google_storage_object.upload_shared_logic.name
    main_script  = google_storage_object.upload_main_script.name
    source_code  = google_storage_object.upload_src_zip.name
    setup_script = google_storage_object.upload_setup_script.name
  }
}





