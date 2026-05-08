resource "google_dataproc_job" "hsl_bus_streaming_job" {
  region       = var.region
  force_delete = true

  placement {
    cluster_name = google_dataproc_cluster.spark_cluster.name
  }

  pyspark_config {
    main_python_file_uri = "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_main_script.name}"

    properties = {
      "spark.hsl.kafka.servers" = "placeholder-kafka-bootstrap-address"
      "spark.hsl.kafka.topic"   = google_managed_kafka_topic.bus_topic.topic_id
      "spark.hsl.redis.host"    = google_compute_instance.redis_server.network_interface[0].network_ip
    }
  }

  depends_on = [
    google_managed_kafka_cluster.bus_kafka,
    google_managed_kafka_topic.bus_topic,
    google_dataproc_cluster.spark_cluster,
    google_compute_instance.redis_server,
    google_storage_bucket_object.upload_main_script
  ]
}