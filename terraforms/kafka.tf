# Managed Kafka cluster created in the selected subnet.
# Managed Kafka cannot receive compute tags directly, so network restrictions
# are enforced through source ranges and private VPC connectivity.
data "google_compute_subnetwork" "kafka_subnet" {
  name   = var.kafka_subnet_name
  region = var.region
}

# 2. Tạo cụm Managed Kafka với cấu hình từ biến
resource "google_managed_kafka_cluster" "bus_kafka" {
  provider   = google-beta
  cluster_id = var.kafka_cluster_id
  location   = local.kafka_location

  capacity_config {
    vcpu_count   = var.kafka_vcpu_count
    memory_bytes = var.kafka_memory_bytes
  }

  gcp_config {
    access_config {
      network_configs {
        subnet = data.google_compute_subnetwork.kafka_subnet.id
      }
    }
  }

  labels = local.common_labels
}

resource "time_sleep" "wait_for_kafka" {
  depends_on      = [google_managed_kafka_cluster.bus_kafka]
  create_duration = "180s"
}

output "kafka_bootstrap_address" {
  description = "Managed Kafka bootstrap broker address."
  value       = local.kafka_bootstrap_address
}

output "kafka_port" {
  description = "Primary Kafka broker port."
  value       = var.kafka_port
}

# Managed Kafka cannot accept compute-target tags, so network-level restrictions
# are enforced by source ranges and private VPC connectivity.

# 3. Tạo Topic hứng dữ liệu ngay khi cụm vừa khởi động xong
resource "google_managed_kafka_topic" "bus_topic" {
  provider = google-beta
  cluster  = google_managed_kafka_cluster.bus_kafka.cluster_id
  location = google_managed_kafka_cluster.bus_kafka.location
  topic_id = var.kafka_topic_id

  partition_count    = var.kafka_partition_count
  replication_factor = var.kafka_replication_factor

  depends_on = [time_sleep.wait_for_kafka]
}