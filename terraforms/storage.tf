/*
  Terraform configuration for Google Cloud Storage buckets used in the HSL Bus Streaming project.
  This file defines two buckets: one for the data lake and another for Spark worker assets.
*/

/*
    Bucket Data Lake: This bucket is used to store the data lake, which includes the bronze and silver layers of data. 
    It is configured with uniform bucket-level access and public access prevention to enhance security. 
    The force_destroy option allows for the bucket to be deleted even if it contains objects, which can be useful during development and testing.
*/
resource "google_storage_bucket" "data_lake" {
  name                        = var.data_lake_bucket
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

/*
    Bucket Spark Worker Assets
*/
resource "google_storage_bucket" "spark_worker_assets" {
  name                        = var.spark_worker_bucket
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

/*
    Create empty folders in Spark Worker Assets bucket
*/
resource "google_storage_bucket_object" "libs_folder" {
  name    = "libs/"
  content = " "
  bucket  = google_storage_bucket.spark_worker_assets.name
}

resource "google_storage_bucket_object" "scripts_folder" {
  name    = "scripts/"
  content = " "
  bucket  = google_storage_bucket.spark_worker_assets.name
}

/*
    Package the shared logic code into a zip file. 
*/
data "archive_file" "shared_logic_zip" {
  type       = "zip"
  source_dir = "${path.module}/../${var.shared_logic_folder}"

  output_path = "${path.module}/shared_logic.zip"
}

/*
    Upload the shared logic zip file to the Spark Worker Assets bucket
*/
resource "google_storage_bucket_object" "upload_shared_logic" {
  name   = "libs/shared_logic.zip"
  bucket = var.spark_worker_bucket

  source = data.archive_file.shared_logic_zip.output_path

  depends_on = [
    data.archive_file.shared_logic_zip,
    google_storage_bucket_object.libs_folder
  ]
}



