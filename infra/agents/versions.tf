terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.6"
    }
  }

  # Bucket created by bootstrap/.
  backend "gcs" {
    bucket = "hyprn-agents-tfstate"
    prefix = "agents"
  }
}
