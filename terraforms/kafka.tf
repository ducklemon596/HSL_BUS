locals {
  kafka_location = var.kafka_location != "" ? var.kafka_location : var.region
}

# 1. Gọi mạng default của Google theo vùng cấu hình
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

  labels = var.resource_labels
}

# 3. Tạo Topic hứng dữ liệu ngay khi cụm vừa khởi động xong
resource "google_managed_kafka_topic" "bus_topic" {
  provider = google-beta
  cluster  = google_managed_kafka_cluster.bus_kafka.cluster_id
  location = google_managed_kafka_cluster.bus_kafka.location
  topic_id = var.kafka_topic_id

  partition_count    = var.kafka_partition_count
  replication_factor = var.kafka_replication_factor
}