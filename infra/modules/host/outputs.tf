output "host_id" { value = google_compute_instance.staging.name }
output "data_disk" { value = google_compute_disk.data.id }
output "policy" {
  value = {
    public_addresses    = length(google_compute_instance.staging.network_interface[0].access_config)
    status              = google_compute_instance.staging.desired_status
    deletion_protection = google_compute_instance.staging.deletion_protection
    machine_type        = google_compute_instance.staging.machine_type
    oslogin             = google_compute_instance.staging.metadata["enable-oslogin"]
    disk_size_gb        = google_compute_disk.data.size
  }
}
