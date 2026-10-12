output "host_name" {
  value = google_compute_instance.host.name
}

output "host_internal_ip" {
  value = google_compute_instance.host.network_interface[0].network_ip
}

output "host_service_account" {
  value = google_service_account.host.email
}

output "ssh_command" {
  value = "gcloud compute ssh ${google_compute_instance.host.name} --zone=${var.zone} --project=${var.project_id} --tunnel-through-iap"
}

output "wake_name" {
  value = google_compute_instance.wake.name
}

output "start_command" {
  value = "gcloud compute instances start ${google_compute_instance.host.name} --zone=${var.zone} --project=${var.project_id}"
}
