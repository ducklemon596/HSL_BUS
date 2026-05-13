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
    project    = "hsl-bus-streaming"
    managed_by = "terraform"
  }
}

variable "analytics_dataset_id" {
  description = "BigQuery dataset for analytics external tables"
  type        = string
  default     = "bus_analytics"
  validation {
    condition     = length(var.analytics_dataset_id) > 0
    error_message = "Analytics dataset ID cannot be empty."
  }
}

variable "bucket_folders" {
  description = "Structure of folders to create in spark worker bucket"
  type = object({
    libs = string
    code = string
  })
  default = {
    libs = "libs"
    code = "code"
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

variable "spark_job_jars_packages" {
  description = "Comma-separated Spark packages required by the Dataproc job"
  type        = string
  default     = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,com.google.cloud.hosted.kafka:managed-kafka-auth-login-handler:1.0.6"
}

variable "dataproc_cluster_name" {
  description = "Dataproc cluster name"
  type        = string
  default     = "hsl-spark-cluster"
}

variable "dataproc_master_machine_type" {
  description = "Machine type for the Dataproc master node"
  type        = string
  default     = "n1-highmem-2"
}

variable "dataproc_master_disk_size_gb" {
  description = "Boot disk size for the Dataproc master node"
  type        = number
  default     = 50
  validation {
    condition     = var.dataproc_master_disk_size_gb > 0
    error_message = "Dataproc master disk size must be greater than zero."
  }
}

variable "dataproc_master_disk_type" {
  description = "Boot disk type for the Dataproc master node"
  type        = string
  default     = "pd-standard"
}

variable "dataproc_worker_machine_type" {
  description = "Machine type for Dataproc worker nodes"
  type        = string
  default     = "n1-highmem-2"
}

variable "dataproc_worker_num_instances" {
  description = "Number of Dataproc worker nodes"
  type        = number
  default     = 2
  validation {
    condition     = var.dataproc_worker_num_instances >= 0
    error_message = "Dataproc worker count must be zero or greater."
  }
}

variable "dataproc_worker_disk_size_gb" {
  description = "Boot disk size for Dataproc worker nodes"
  type        = number
  default     = 50
  validation {
    condition     = var.dataproc_worker_disk_size_gb > 0
    error_message = "Dataproc worker disk size must be greater than zero."
  }
}

variable "dataproc_worker_disk_type" {
  description = "Boot disk type for Dataproc worker nodes"
  type        = string
  default     = "pd-standard"
}

variable "dataproc_image_version" {
  description = "Dataproc image version for the cluster"
  type        = string
  default     = "2.1-debian11"
}

variable "dataproc_enable_component_gateway" {
  description = "Enable Dataproc component gateway for UI access"
  type        = bool
  default     = true
}

variable "kafka_cluster_id" {
  description = "Managed Kafka cluster identifier"
  type        = string
  default     = "hsl-bus-kafka-cluster"
  validation {
    condition     = length(var.kafka_cluster_id) > 0
    error_message = "Kafka cluster id cannot be empty."
  }
}

variable "kafka_topic_id" {
  description = "Managed Kafka topic identifier"
  type        = string
  default     = "hsl-bus-stream"
  validation {
    condition     = length(var.kafka_topic_id) > 0
    error_message = "Kafka topic id cannot be empty."
  }
}

variable "kafka_location" {
  description = "Deployment region for Kafka resources, falls back to var.region if unset"
  type        = string
  default     = ""
}

variable "kafka_subnet_name" {
  description = "Name of the subnet to attach Kafka resources to"
  type        = string
  default     = "hsl-kafka-subnet"
}

variable "kafka_vcpu_count" {
  description = "Number of vCPUs for the Kafka cluster"
  type        = number
  default     = 3
  validation {
    condition     = var.kafka_vcpu_count > 0
    error_message = "Kafka vCPU count must be greater than zero."
  }
}

variable "kafka_memory_bytes" {
  description = "Memory size for the Kafka cluster in bytes"
  type        = number
  default     = 12884901888
  validation {
    condition     = var.kafka_memory_bytes > 0
    error_message = "Kafka memory_bytes must be greater than zero."
  }
}

variable "kafka_partition_count" {
  description = "Number of partitions for the Kafka topic"
  type        = number
  default     = 8
  validation {
    condition     = var.kafka_partition_count > 0
    error_message = "Kafka partition count must be greater than zero."
  }
}

variable "kafka_replication_factor" {
  description = "Replication factor for the Kafka topic"
  type        = number
  default     = 3
  validation {
    condition     = var.kafka_replication_factor > 0
    error_message = "Kafka replication factor must be greater than zero."
  }
}

# ============================================================================
# INGESTION SERVICE VM CONFIGURATION
# ============================================================================

variable "ingestion_vm_machine_type" {
  description = "Machine type for ingestion service VM (small, cost-efficient)"
  type        = string
  default     = "e2-micro"
}

variable "ingestion_vm_disk_size_gb" {
  description = "Boot disk size in GB for ingestion VM"
  type        = number
  default     = 20
  validation {
    condition     = var.ingestion_vm_disk_size_gb > 0
    error_message = "Disk size must be greater than zero."
  }
}

variable "ingestion_vm_disk_type" {
  description = "Boot disk type for ingestion VM"
  type        = string
  default     = "pd-standard"
}

# ============================================================================
# CLOUD RUN SERVICE CONFIGURATION
# ============================================================================

# Đã đổi từ backend_api_image sang backend_image
variable "backend_image" {
  description = "Docker image URI for backend Cloud Run service"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
  validation {
    condition     = length(var.backend_image) > 0
    error_message = "Backend image cannot be empty."
  }
}

variable "frontend_service_image" {
  description = "Docker image URI for frontend Cloud Run service"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
  validation {
    condition     = length(var.frontend_service_image) > 0
    error_message = "Frontend service image cannot be empty."
  }
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run service (e.g., '256Mi', '512Mi', '1Gi')"
  type        = string
  default     = "512Mi"
  validation {
    condition     = contains(["128Mi", "256Mi", "512Mi", "1Gi", "2Gi", "4Gi"], var.cloud_run_memory)
    error_message = "Memory must be one of: 128Mi, 256Mi, 512Mi, 1Gi, 2Gi, 4Gi."
  }
}

variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run service"
  type        = number
  default     = 1
  validation {
    condition     = contains([1, 2, 4], var.cloud_run_cpu)
    error_message = "CPU must be one of: 1, 2, 4."
  }
}

variable "cloud_run_timeout_seconds" {
  description = "Request timeout in seconds for Cloud Run service"
  type        = number
  default     = 3600
  validation {
    condition     = var.cloud_run_timeout_seconds > 0 && var.cloud_run_timeout_seconds <= 3600
    error_message = "Timeout must be between 1 and 3600 seconds."
  }
}

variable "cloud_run_min_instances" {
  description = "Minimum number of instances for Cloud Run (0 = scale to zero when idle)"
  type        = number
  default     = 0
  validation {
    condition     = var.cloud_run_min_instances >= 0
    error_message = "Min instances must be >= 0."
  }
}

variable "cloud_run_max_instances" {
  description = "Maximum number of instances for Cloud Run auto-scaling"
  type        = number
  default     = 100
  validation {
    condition     = var.cloud_run_max_instances > 0
    error_message = "Max instances must be > 0."
  }
}

variable "network_name" {
  description = "Name of the VPC network to deploy resources into"
  type        = string
  default     = "default"
}

# Đã đổi từ backend_api_vpc_connector_name sang backend_vpc_connector_name và cập nhật giá trị an toàn
variable "backend_vpc_connector_name" {
  description = "VPC connector name for the backend Cloud Run service"
  type        = string
  default     = "bus-backend-vpc-conn"
}

# Đã đổi từ backend_api_vpc_cidr_range sang backend_vpc_cidr_range
variable "backend_vpc_cidr_range" {
  description = "CIDR range assigned to the backend Cloud Run VPC connector"
  type        = string
  default     = "10.10.0.0/28"
}

variable "redis_port" {
  description = "Redis service port"
  type        = number
  default     = 6379
}

variable "resource_name_prefix" {
  description = "Common prefix used for generated resource names"
  type        = string
  default     = "hsl"
}

variable "repo_name" {
  description = "Artifact Registry repository name used by the ingestion VM container"
  type        = string
  default     = "hsl-bus-repo"
}

variable "redis_machine_type" {
  description = "Machine type for the Redis server"
  type        = string
  default     = "e2-micro"
}

variable "redis_disk_size_gb" {
  description = "Boot disk size in GB for Redis server"
  type        = number
  default     = 20
  validation {
    condition     = var.redis_disk_size_gb > 0
    error_message = "Redis disk size must be greater than zero."
  }
}

variable "redis_disk_type" {
  description = "Boot disk type for Redis server"
  type        = string
  default     = "pd-standard"
}

variable "kafka_port" {
  description = "Primary Kafka broker port"
  type        = number
  default     = 9092
  validation {
    condition     = var.kafka_port > 0
    error_message = "Kafka port must be greater than zero."
  }
}

variable "ingestion_vm_image" {
  description = "Boot image for the ingestion VM"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "mqtt_broker" {
  description = "MQTT broker host for ingestion service"
  type        = string
  default     = "mqtt.hsl.fi"
}

variable "mqtt_port" {
  description = "MQTT broker port for ingestion service"
  type        = number
  default     = 8883
}

variable "mqtt_topic" {
  description = "MQTT topic subscription for ingestion service"
  type        = string
  default     = "/hfp/v2/journey/ongoing/vp/bus/#"
}

variable "ingestion_service_account_id" {
  description = "Service account id for ingestion VM"
  type        = string
  default     = "hsl-ingestion-service"
}

variable "ingestion_vm_name" {
  description = "Name of the ingestion VM"
  type        = string
  default     = "hsl-ingestion-vm"
}

variable "ingestion_firewall_name" {
  description = "Firewall rule name for ingestion VM Kafka access"
  type        = string
  default     = "hsl-allow-ingestion-to-kafka"
}