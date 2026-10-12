resource "google_compute_instance" "host" {
  name                      = "hyprn-agents-host-01"
  machine_type              = var.host_machine_type
  zone                      = var.zone
  deletion_protection       = true
  allow_stopping_for_update = true

  boot_disk {
    auto_delete = true
    initialize_params {
      image = var.host_image
      size  = var.host_disk_gb
      type  = "pd-balanced"
    }
  }

  # No access_config: no public IP. Outbound through Cloud NAT.
  network_interface {
    subnetwork = google_compute_subnetwork.agents.id
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
  }

  service_account {
    email  = google_service_account.host.email
    scopes = ["cloud-platform"]
  }

  labels = {
    component  = "agents"
    role       = "host"
    managed_by = "terraform"
  }

  depends_on = [
    google_project_iam_member.host,
    google_compute_router_nat.agents,
  ]
}
