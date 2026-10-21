# The host verifies exclusive attachment; it cannot change compute resources.
resource "google_project_iam_custom_role" "runtime_fence_reader" {
  project     = var.project_id
  role_id     = "hyprnStagingFenceReader"
  title       = "HYPRN staging host fence reader"
  description = "Read the exact staging host and data disk before lifecycle operations."
  permissions = ["compute.instances.get", "compute.disks.get"]
}

locals {
  fence_resource_condition = join(" || ", [
    "(resource.type == \"compute.googleapis.com/Instance\" && resource.name == \"projects/${var.project_id}/zones/${var.zone}/instances/${google_compute_instance.staging.name}\")",
    "(resource.type == \"compute.googleapis.com/Disk\" && resource.name == \"projects/${var.project_id}/zones/${var.zone}/disks/${google_compute_disk.data.name}\")",
  ])
}

resource "google_project_iam_member" "runtime_fence_reader" {
  project = var.project_id
  role    = google_project_iam_custom_role.runtime_fence_reader.name
  member  = "serviceAccount:${var.runtime_service_account}"
  condition {
    title       = "staging-host-and-data-disk-only"
    description = "Read-only identity and attachment checks for these two resources."
    expression  = local.fence_resource_condition
  }
}
