resource "google_dataproc_job" "hsl_bus_streaming_job" {
  region       = var.region
  force_delete = true

  placement {
    cluster_name = google_dataproc_cluster.spark_cluster.name
  }

  pyspark_config {
    main_python_file_uri = "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_main_script.name}"

    archive_uris = [
      "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_shared_logic.name}"
    ]

    properties = {
      "spark.hsl.kafka.brokers" = local.kafka_bootstrap_host
      "spark.hsl.kafka.port"    = tostring(var.kafka_port)
      "spark.hsl.kafka.topic"   = google_managed_kafka_topic.bus_topic.topic_id
      "spark.hsl.redis.host"    = google_compute_instance.redis_server.network_interface[0].network_ip
      "spark.hsl.redis.port"    = tostring(var.redis_port)
    }
  }

  depends_on = [
    google_managed_kafka_cluster.bus_kafka,
    google_managed_kafka_topic.bus_topic,
    google_dataproc_cluster.spark_cluster,
    google_compute_instance.redis_server,
    google_storage_bucket_object.upload_main_script,
    google_storage_bucket_object.upload_shared_logic,
    time_sleep.wait_for_dataproc,
    time_sleep.wait_for_kafka,
    time_sleep.wait_for_redis
  ]
}