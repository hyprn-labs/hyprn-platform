terraform {
  required_version = "= 1.16.5"
  required_providers {
    google = { source = "hashicorp/google", version = "8.6.0" }
  }
  backend "gcs" {}
}

provider "google" {
  project               = "hyprn-bootstrap"
  billing_project       = "hyprn-bootstrap"
  user_project_override = true
}
