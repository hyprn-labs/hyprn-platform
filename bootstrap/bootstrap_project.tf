# Created with gcloud before the first apply (see README.md), then adopted.
import {
  to = google_project.bootstrap
  id = "hyprn-bootstrap"
}

resource "google_project" "bootstrap" {
  name            = "hyprn bootstrap"
  project_id      = var.bootstrap_project_id
  org_id          = var.org_id
  billing_account = var.billing_account
  deletion_policy = "PREVENT"

  labels = {
    component  = "bootstrap"
    managed_by = "terraform"
  }
}

locals {
  bootstrap_services = toset([
    "billingbudgets.googleapis.com",
    "cloudasset.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudidentity.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "essentialcontacts.googleapis.com",
    "iam.googleapis.com",
    "orgpolicy.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ])
}

resource "google_project_service" "bootstrap" {
  for_each = local.bootstrap_services

  project            = google_project.bootstrap.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_project_iam_member" "bootstrap_admins_owner" {
  project = google_project.bootstrap.project_id
  role    = "roles/owner"
  member  = "group:${var.admins_group}"
}

resource "google_storage_bucket" "bootstrap_tfstate" {
  name                        = "${var.bootstrap_project_id}-tfstate"
  project                     = google_project.bootstrap.project_id
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      with_state         = "ARCHIVED"
      num_newer_versions = 20
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    component  = "bootstrap"
    managed_by = "terraform"
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.bootstrap]
}
