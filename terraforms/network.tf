# 1. Tạo mạng VPC chính (Căn nhà tổng)
resource "google_compute_network" "vpc_network" {
  name                    = "hsl-bus-vpc"
  auto_create_subnetworks = false # Tắt tự động để chúng ta tự quản lý dải IP
}

# 2. Tạo Subnet (Phân khu trong nhà)
resource "google_compute_subnetwork" "bus_subnet" {
  name          = "hsl-bus-subnet"
  ip_cidr_range = "10.10.0.0/24" # Dải IP nội bộ cho các máy ảo
  region        = var.region
  network       = google_compute_network.vpc_network.id

  # CỰC KỲ QUAN TRỌNG: Cho phép các máy trong subnet này 
  # truy cập dịch vụ Google (như Artifact Registry) mà không cần IP Public.
  private_ip_google_access = true
}

# Create cloud router for NAT
resource "google_compute_router" "bus_router" {
  name    = "hsl-bus-router"
  network = google_compute_network.vpc_network.id # Hãy đảm bảo biến này trỏ đúng vào VPC của bạn
  region  = var.region
}

# Create Cloud NAT to allow outbound internet access without public IPs
resource "google_compute_router_nat" "bus_nat" {
  name   = "hsl-bus-nat"
  router = google_compute_router.bus_router.name
  region = google_compute_router.bus_router.region

  # Google sẽ tự động mua và quản lý các địa chỉ IP Public dùng cho việc NAT
  nat_ip_allocate_option = "AUTO_ONLY"

  # Áp dụng cho tất cả các subnet trong VPC này
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  # (Tùy chọn) Bật log để dễ debug nếu gọi API bị lỗi
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Cho phép SSH thông qua IAP
resource "google_compute_firewall" "allow_ssh_iap" {
  name    = "hsl-allow-ssh-iap"
  network = google_compute_network.vpc_network.id

  direction = "INGRESS"
  priority  = 1000

  # Dải IP NÀY LÀ CỐ ĐỊNH của Google IAP, không được thay đổi
  source_ranges = ["35.235.240.0/20"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # Áp dụng cho tất cả các máy ảo trong hệ thống để bạn có thể SSH vào bất cứ đâu
  # Hoặc bạn có thể dùng target_tags để chỉ giới hạn cho Redis/Ingestion
  target_tags = [
    local.redis_firewall_tag,
    local.ingestion_node_tag,
    local.dataproc_node_tag
  ]
}