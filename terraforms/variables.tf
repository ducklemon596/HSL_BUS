variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
  validation {
    condition     = length(var.project_id) > 0
    error_message = "Project ID cannot be empty."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "region" {
  description = "Deployment region for Google Cloud resources"
  type        = string
  default     = "asia-southeast1"
  validation {
    condition     = length(var.region) > 0
    error_message = "Region cannot be empty."
  }
}

variable "zone" {
  description = "Deployment zone for Google Cloud resources"
  type        = string
  default     = "asia-southeast1-a"
}

variable "data_lake_bucket" {
  description = "Name of the bucket for storing data lake (bronze & silver)"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]*[a-z0-9]$", var.data_lake_bucket)) && length(var.data_lake_bucket) >= 3 && length(var.data_lake_bucket) <= 63
    error_message = "Bucket name must follow GCS naming rules: 3-63 chars, lowercase, numbers, hyphens, underscores, dots."
  }
}

variable "spark_worker_bucket" {
  description = "Name of the bucket for storing assets for Spark worker"
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]*[a-z0-9]$", var.spark_worker_bucket)) && length(var.spark_worker_bucket) >= 3 && length(var.spark_worker_bucket) <= 63
    error_message = "Bucket name must follow GCS naming rules: 3-63 chars, lowercase, numbers, hyphens, underscores, dots."
  }
}

variable "shared_logic_folder" {
  description = "Local folder path containing shared logic code"
  type        = string
  default     = "shared_lib"
}

variable "source_code_folder" {
  description = "Local folder path containing Spark job code"
  type        = string
  default     = "spark_service"
}

variable "bucket_storage_class" {
  description = "Storage class for buckets (STANDARD, NEARLINE, COLDLINE, ARCHIVE)"
  type        = string
  default     = "STANDARD"
  validation {
    condition     = contains(["STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"], var.bucket_storage_class)
    error_message = "Storage class must be one of: STANDARD, NEARLINE, COLDLINE, ARCHIVE."
  }
}

variable "enable_versioning" {
  description = "Enable versioning on storage buckets"
  type        = bool
  default     = true
}

variable "force_destroy_bucket" {
  description = "Allow Terraform to destroy non-empty buckets (should be false in production)"
  type        = bool
  default     = false
}

variable "resource_labels" {
  description = "Common labels to apply to all resources"
  type        = map(string)
  default = {
    project     = "hsl-bus-streaming"
    managed_by  = "terraform"
  }
}

variable "bucket_folders" {
  description = "Structure of folders to create in spark worker bucket"
  type = object({
    libs    = string
    code    = string
  })
  default = {
    libs    = "libs"
    code    = "code"
  }
}

variable "source_code_artifacts" {
  description = "Configuration for source code artifacts to upload"
  type = object({
    shared_logic_path = string
    main_script_path  = string
    source_code_path  = string
    setup_script_path = string
  })
  default = {
    shared_logic_path = "libs/shared_logic.zip"
    main_script_path  = "code/main.py"
    source_code_path  = "code/src.zip"
    setup_script_path = "scripts/setup_env.sh"
  }
}  