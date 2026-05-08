# ============================================================================
# INGESTION SERVICE - MQTT to Kafka Bridge
# Small VM instance for consuming MQTT data and publishing to Kafka
# ============================================================================

# Service Account for Ingestion VM
resource "google_service_account" "ingestion_service" {
  account_id   = "hsl-ingestion-service"
  display_name = "Service Account for HSL Bus Ingestion"
  description  = "Service account for MQTT to Kafka ingestion service on VM"
}

# Grant Kafka Admin role to ingestion service account
# This allows the ingestion service to authenticate with Managed Kafka
resource "google_project_iam_member" "ingestion_kafka_role" {
  project = var.project_id
  role    = "roles/managedkafka.admin"
  member  = "serviceAccount:${google_service_account.ingestion_service.email}"
}

# Grant Compute Instance Admin role for lifecycle management
resource "google_project_iam_member" "ingestion_compute_role" {
  project = var.project_id
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.ingestion_service.email}"
}

# Grant Cloud Logging permissions for application logs
resource "google_project_iam_member" "ingestion_logging_role" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.ingestion_service.email}"
}

# Firewall rule to allow ingestion VM to connect to Kafka (port 9092 - Kafka broker)
resource "google_compute_firewall" "allow_ingestion_to_kafka" {
  name    = "hsl-allow-ingestion-to-kafka"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["9092", "9093", "9094"]  # Kafka broker ports
  }

  source_tags = ["hsl-ingestion-node"]
  target_tags = []  # Applied to Kafka subnet resources

  depends_on = [google_managed_kafka_cluster.bus_kafka]
}

# Ingestion Service VM Instance
resource "google_compute_instance" "ingestion_vm" {
  name         = "hsl-ingestion-vm"
  machine_type = var.ingestion_vm_machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.ingestion_vm_disk_size_gb
      type  = var.ingestion_vm_disk_type
    }
  }

  network_interface {
    network = "default"
    # Request internal IP only (private instance)
  }

  # Service account for API authentication
  service_account {
    email  = google_service_account.ingestion_service.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  # Startup script to initialize ingestion service with Kafka authentication
  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e
    
    # Update system packages
    apt-get update
    apt-get install -y python3 python3-pip python3-venv git
    
    # Create virtual environment
    python3 -m venv /opt/ingestion-env
    source /opt/ingestion-env/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install paho-mqtt kafka-python python-dotenv
    
    # Create environment file for ingestion service
    cat > /etc/environment.d/hsl-ingestion.sh <<ENVEOF
    export KAFKA_BROKER="${google_managed_kafka_cluster.bus_kafka.bootstrap_config[0].vpc_configs[0].bootstrap_address}"
    export KAFKA_TOPIC="${google_managed_kafka_topic.bus_topic.topic_id}"
    export MQTT_BROKER="mqtt.hsl.fi"
    export MQTT_PORT="8883"
    export MQTT_TOPIC="/hfp/v2/journey/ongoing/vp/bus/#"
    export LOG_LEVEL="INFO"
    ENVEOF
    
    # Setup ingestion service systemd unit
    cat > /etc/systemd/system/hsl-ingestion.service <<SVCEOF
    [Unit]
    Description=HSL Bus MQTT to Kafka Ingestion Service
    After=network.target
    
    [Service]
    Type=simple
    User=root
    WorkingDirectory=/opt/ingestion
    Environment="PATH=/opt/ingestion-env/bin"
    ExecStart=/opt/ingestion-env/bin/python run_ingestion.py
    Restart=always
    RestartSec=30
    
    [Install]
    WantedBy=multi-user.target
    SVCEOF
    
    # Enable and start the service
    systemctl daemon-reload
    systemctl enable hsl-ingestion
    systemctl start hsl-ingestion
  EOF

  # Tag for firewall rule identification
  tags = ["hsl-ingestion-node"]

  # Labels for resource tracking
  labels = var.resource_labels

  # Ensure Kafka cluster is fully initialized before creating VM
  depends_on = [
    google_managed_kafka_cluster.bus_kafka,
    google_managed_kafka_topic.bus_topic,
    google_service_account.ingestion_service,
    google_project_iam_member.ingestion_kafka_role
  ]

  # Add time delay for IAM propagation
  provisioner "local-exec" {
    command = "sleep 30"
  }
}

# ============================================================================
# OUTPUTS - Ingestion Service Information
# ============================================================================

output "ingestion_vm_internal_ip" {
  description = "Internal IP of the ingestion VM"
  value       = google_compute_instance.ingestion_vm.network_interface[0].network_ip
}

output "ingestion_service_account_email" {
  description = "Email of the ingestion service account"
  value       = google_service_account.ingestion_service.email
}
