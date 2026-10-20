resource "google_storage_bucket" "staging_state" {
  name                        = var.state_bucket_name
  project                     = "hyprn-bootstrap"
  location                    = var.location
  storage_class               = "STANDARD"
  force_destroy               = false
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  labels = {
    component  = "staging-state"
    managed_by = "terraform"
  }

  lifecycle {
    prevent_destroy = true
  }
}

output "staging_state_bucket" {
  value = google_storage_bucket.staging_state.name
}
