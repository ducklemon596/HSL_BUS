# 1. Tạo máy ảo Redis Server
resource "google_compute_instance" "redis_server" {
  name         = "hsl-redis-server"
  machine_type = "e2-micro"
  zone         = "asia-southeast1-a" # Đảm bảo cùng khu vực với Dataproc

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    
    # Vẫn giữ access_config để lấy Public IP cho bạn dễ debug từ máy cá nhân
    access_config {} 
  }

  # Startup script tự động cài đặt và cấu hình
  # Dùng <<-EOF (có dấu trừ) để Terraform tự động format thụt lề chuẩn xác
  metadata_startup_script = replace(<<-EOF
    #!/bin/bash
    set -e
    
    # Cập nhật và cài đặt Redis
    apt-get update
    apt-get install -y redis-server
    
    # Dùng Regex thay thế toàn bộ dòng bắt đầu bằng chữ 'bind' và 'protected-mode'
    sed -i 's/^bind .*/bind 0.0.0.0/' /etc/redis/redis.conf
    sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf
    
    # Khởi động lại dịch vụ để ăn cấu hình mới
    systemctl restart redis-server
  EOF
  , "\r", "")

  # Gắn thẻ để Tường lửa nhận diện
  tags = ["allow-redis-internal"]
}

# 2. Tường lửa CHỈ mở cho mạng nội bộ VPC (Bảo mật tuyệt đối)
resource "google_compute_firewall" "allow_redis" {
  name    = "hsl-allow-redis-internal"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  source_tags = ["bus-dataproc-node"]
  target_tags   = ["allow-redis-internal"]
}

# =====================================================================
# 3. KẾT QUẢ ĐẦU RA (DÙNG CHO TỰ ĐỘNG HÓA)
# =====================================================================

# IP NỘI BỘ: Đây là "Trái tim" của sự tự động hóa. Dataproc sẽ dùng IP này.
output "redis_internal_ip" {
  description = "IP Nội bộ để Dataproc kết nối tốc độ cao"
  value       = google_compute_instance.redis_server.network_interface[0].network_ip
}

# IP PUBLIC: Chỉ dùng cho bạn mở phần mềm Redis Insight trên máy cá nhân để soi data
output "redis_public_ip" {
  description = "IP Public để debug (Sẽ không vào được nếu bạn không kết nối VPN GCP)"
  value       = google_compute_instance.redis_server.network_interface[0].access_config[0].nat_ip
}