locals {
  resource_prefix = "${var.environment}-${var.resource_name_prefix}"

  common_labels = merge(
    var.resource_labels,
    {
      environment = var.environment
      prefix      = local.resource_prefix
      created_at = formatdate("YYYY-MM-DD-hh-mm-ss", timestamp())
    }
  )

  kafka_location = var.kafka_location != "" ? var.kafka_location : var.region

  kafka_bootstrap_host    = format("bootstrap.kafka.%s.managedkafka.%s.cloud.goog", local.kafka_location, var.project_id)
  kafka_bootstrap_address = "${local.kafka_bootstrap_host}:${var.kafka_port}"

  redis_firewall_tag = "allow-redis-internal"
  ingestion_node_tag = "hsl-ingestion-node"
  dataproc_node_tag  = "bus-dataproc-node"
}
