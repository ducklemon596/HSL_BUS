/*
    Create a Redis server running on e2-micro instance
*/
resource "google_compute_instance" "redis_server" {
  name         = "hsl-redis-server"
  machine_type = "e2-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    access_config {} # public IP when VM is running
  }

  # Dùng hàm replace để ép xóa bỏ ký tự \r của Windows
  metadata_startup_script = replace(<<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y redis-server
    sed -i 's/bind 127.0.0.1 -::1/bind 0.0.0.0/g' /etc/redis/redis.conf
    sed -i 's/protected-mode yes/protected-mode no/g' /etc/redis/redis.conf
    systemctl restart redis-server
  EOF
  , "\r", "")

  tags = ["allow-redis"]
}

# 2. Tạo tường lửa mở cổng 6379
resource "google_compute_firewall" "allow_redis" {
  name    = "hsl-allow-redis-port"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["allow-redis"]
}

# 3. In ra màn hình IP Public để bạn sử dụng
output "redis_public_ip" {
  value = google_compute_instance.redis_server.network_interface[0].access_config[0].nat_ip
}