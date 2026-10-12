terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.6"
    }
  }

  # The bucket is created by this configuration; the first apply used local
  # state, migrated here afterwards (see README.md).
  backend "gcs" {
    bucket = "hyprn-bootstrap-tfstate"
    prefix = "bootstrap"
  }
}
