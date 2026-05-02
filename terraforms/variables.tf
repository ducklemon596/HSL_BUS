variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Deployment region for Google Cloud resources"
  type        = string
  default     = "asia-southeast1"
}

variable "data_lake_bucket" {
  description = "Name of the bucket for storing data lake (bronze & silver)"
  type        = string
}

variable "spark_worker_bucket" {
  description = "Name of the bucket for storing assets for Spark worker"
  type        = string
}

variable "shared_logic_folder" {
  description = "Name of the local folder containing shared logic code to be uploaded to Spark Worker Assets bucket"
  type        = string
}   