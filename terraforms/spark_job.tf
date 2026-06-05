resource "google_dataproc_job" "hsl_bus_streaming_job" {
  region       = var.region
  force_delete = true

  placement {
    cluster_name = google_dataproc_cluster.spark_cluster.name
  }

  pyspark_config {
    main_python_file_uri = "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_main_script.name}"

    python_file_uris = [
      "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_shared_logic.name}",
      "gs://${google_storage_bucket.spark_worker_assets.name}/${google_storage_bucket_object.upload_src_zip.name}"
    ]

    properties = {
      "spark.driver.memory"   = "6G"
      "spark.executor.memory" = "6G"
      "spark.executor.cores"  = "2"

      "spark.hsl.kafka.brokers"  = local.kafka_bootstrap_address
      "spark.hsl.kafka.port"     = tostring(var.kafka_port)
      "spark.hsl.kafka.topic"    = google_managed_kafka_topic.bus_topic.topic_id
      "spark.hsl.redis.host"     = google_compute_instance.redis_server.network_interface[0].network_ip
      "spark.hsl.redis.port"     = tostring(var.redis_port)
      "spark.hsl.gcs.bronze"     = "gs://${google_storage_bucket.data_lake.name}/bronze_layer/"
      "spark.hsl.gcs.silver"     = "gs://${google_storage_bucket.data_lake.name}/silver_layer/"
      "spark.hsl.gcs.checkpoint" = "gs://${google_storage_bucket.data_lake.name}/checkpoints/"
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

resource "time_sleep" "wait_for_spark_job" {
  depends_on = [ google_dataproc_job.hsl_bus_streaming_job ]
  create_duration = "60s"
}