terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }

    time = {
      source  = "hashicorp/time"
      version = "~> 0.7"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

