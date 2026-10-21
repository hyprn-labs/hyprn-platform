output "host_id" { value = google_compute_instance.staging.name }
output "data_disk" { value = google_compute_disk.data.id }
output "policy" {
  value = {
    fence_permissions   = google_project_iam_custom_role.runtime_fence_reader.permissions
    fence_condition     = google_project_iam_member.runtime_fence_reader.condition[0].expression
    public_addresses    = length(google_compute_instance.staging.network_interface[0].access_config)
    status              = google_compute_instance.staging.desired_status
    deletion_protection = google_compute_instance.staging.deletion_protection
    machine_type        = google_compute_instance.staging.machine_type
    oslogin             = google_compute_instance.staging.metadata["enable-oslogin"]
    disk_size_gb        = google_compute_disk.data.size
  }
}
