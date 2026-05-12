# 1. Tạo mới Subnet dành riêng cho Kafka (Thay thế cho block data cũ)
# Nơi đây sẽ là "vùng xanh" hoàn toàn cách ly, chuyên chứa lõi dữ liệu
resource "google_compute_subnetwork" "kafka_subnet" {
  name          = var.kafka_subnet_name
  ip_cidr_range = "10.10.1.0/24" # Dải IP độc lập (bạn có thể thay đổi tùy ý, miễn không trùng với bus_subnet)
  region        = var.region

  # LƯU Ý: Đảm bảo biến này trỏ đúng vào resource VPC tổng của bạn
  network = google_compute_network.vpc_network.id

  # Bật Private Google Access để các dịch vụ Managed hoạt động trơn tru
  private_ip_google_access = true
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
        # Đã cập nhật: Trỏ thẳng vào resource subnet vừa tạo ở trên thay vì data
        subnet = google_compute_subnetwork.kafka_subnet.id
      }
    }
  }

  rebalance_config {
    mode = "AUTO_REBALANCE_ON_SCALE_UP"
  }

  # Thêm nhãn để dễ quản lý và phân loại tài nguyên
  labels = local.common_labels
}

resource "time_sleep" "wait_for_kafka" {
  depends_on      = [google_managed_kafka_cluster.bus_kafka]
  create_duration = "120s"
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