project_id          = "hsl-bus-streaming-495014"
environment         = "dev"
region              = "asia-southeast1"
zone                = "asia-southeast1-a"
data_lake_bucket    = "hsl-bus-data-lake"
spark_worker_bucket = "hsl-bus-spark-worker"

bucket_storage_class = "STANDARD"
enable_versioning    = true
force_destroy_bucket = true # Set to false in production

shared_logic_folder = "libs"
source_code_folder  = "spark_service"

resource_labels = {
  project    = "hsl-bus-streaming"
  managed_by = "terraform"
  team       = "data-engineering"
}

bucket_folders = {
  libs = "libs"
  code = "code"
}

source_code_artifacts = {
  shared_logic_path = "libs/shared_lib.zip"
  main_script_path  = "code/main.py"
  source_code_path  = "code/src.zip"
  setup_script_path = "scripts/setup_env.sh"
}

# Networking and runtime variables
network_name              = "default"
app_service_name          = "hsl-bus-web-app"
app_service_account_id    = "hsl-app-service"
app_vpc_connector_name    = "hsl-app-vpc-connector-v2"
app_vpc_cidr_range        = "10.10.0.0/28"
redis_port                = 6379
repo_name                 = "hsl-repo"
app_allow_unauthenticated = false

# MQTT ingestion configuration
mqtt_broker = "mqtt.hsl.fi"
mqtt_port   = 8883
mqtt_topic  = "/hfp/v2/journey/ongoing/vp/bus/#"

# Ingestion VM naming and image
ingestion_service_account_id = "hsl-ingestion-service"
ingestion_vm_name            = "hsl-ingestion-vm"
ingestion_vm_image           = "ubuntu-os-cloud/ubuntu-2204-lts"


# ============================================================================
# KAFKA CONFIGURATION
# ============================================================================
# kafka_partition_count: Number of partitions for the Kafka topic (8 partitions)
kafka_partition_count = 4
# kafka_replication_factor: Replication factor ensures 3 copies of each message
kafka_replication_factor = 3

# ============================================================================
# INGESTION SERVICE VM CONFIGURATION
# ============================================================================
# Small VM instance for MQTT to Kafka ingestion service
ingestion_vm_machine_type = "e2-micro" # Small, cost-efficient instance
ingestion_vm_disk_size_gb = 20         # Boot disk size
ingestion_vm_disk_type    = "pd-standard"

# ============================================================================
# CLOUD RUN APP SERVICE CONFIGURATION
# ============================================================================
# Docker image for the web application service
app_service_image = "asia-southeast1-docker.pkg.dev/hsl-bus-streaming-495014/hsl-repo/hsl-bus-web:latest"
# Memory: 512MB provides good balance for Flask SocketIO app
cloud_run_memory = "512Mi"
# CPU: 1 CPU sufficient for lightweight web app
cloud_run_cpu = 1
# Timeout: 1 hour max request timeout
cloud_run_timeout_seconds = 3600
# Min instances: 0 = auto-scale to zero when no requests (cost savings)
cloud_run_min_instances = 0
# Max instances: Scale up to 20 for high load
cloud_run_max_instances = 2