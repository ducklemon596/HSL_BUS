resource "google_compute_instance" "redis_server" {
  name         = "${local.resource_prefix}-redis-server"
  machine_type = var.redis_machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.redis_disk_size_gb
      type  = var.redis_disk_type
    }
  }

  network_interface {
    network = var.network_name
  }

  metadata_startup_script = replace(<<-EOF
    #!/bin/bash
    set -e
    
    apt-get update
    apt-get install -y redis-server
    
    sed -i 's/^bind .*/bind 0.0.0.0/' /etc/redis/redis.conf
    sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf
    
    systemctl restart redis-server
  EOF
  , "\r", "")

  tags   = [local.redis_firewall_tag]
  labels = local.common_labels
}

resource "time_sleep" "wait_for_redis" {
  depends_on      = [google_compute_instance.redis_server]
  create_duration = "90s"
}

# 2. Tường lửa CHỈ mở cho mạng nội bộ VPC (Bảo mật tuyệt đối)
resource "google_compute_firewall" "allow_redis" {
  name    = "hsl-allow-redis-internal"
  network = var.network_name

  allow {
    protocol = "tcp"
    ports    = [tostring(var.redis_port)]
  }

  source_tags = [local.dataproc_node_tag]
  target_tags = [local.redis_firewall_tag]
}

# ==========
# OUTPUTS
# ==========

output "redis_internal_ip" {
  description = "Internal IP used by Dataproc and Cloud Run to connect to Redis"
  value       = google_compute_instance.redis_server.network_interface[0].network_ip
}
