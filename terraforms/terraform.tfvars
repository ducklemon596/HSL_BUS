project_id            = "hsl-bus-streaming-495014"
environment           = "dev"
region                = "asia-southeast1"
zone                  = "asia-southeast1-a"
data_lake_bucket      = "hsl-bus-data-lake"
spark_worker_bucket   = "hsl-bus-spark-worker"

bucket_storage_class  = "STANDARD"
enable_versioning     = true
force_destroy_bucket  = true # Set to false in production

shared_logic_folder   = "shared_lib"
source_code_folder    = "spark_service/src"

resource_labels = {
  project    = "hsl-bus-streaming"
  managed_by = "terraform"
  team       = "data-engineering"
}

bucket_folders = {
  libs    = "libs"
  code    = "code"
}

source_code_artifacts = {
  shared_logic_path = "libs/shared_logic.zip"
  main_script_path  = "code/main.py"
  source_code_path  = "code/src.zip"
  setup_script_path = "scripts/setup_env.sh"
}