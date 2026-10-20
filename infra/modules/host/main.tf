terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "8.6.0" }
  }
}
resource "google_compute_disk" "data" {
  project = var.project_id
  name    = "hyprn-staging-data"
  zone    = var.zone
  type    = "pd-balanced"
  size    = 100
  labels  = { environment = "staging", product = "hyprn-mvp", managed_by = "terraform" }
  lifecycle { prevent_destroy = true }
}
resource "google_compute_instance" "staging" {
  project                   = var.project_id
  name                      = "hyprn-staging-host"
  zone                      = var.zone
  machine_type              = "e2-standard-4"
  deletion_protection       = true
  allow_stopping_for_update = true
  desired_status            = "TERMINATED"
  can_ip_forward            = false
  boot_disk {
    initialize_params {
      image = var.host_image
      size  = 30
      type  = "pd-balanced"
    }
  }
  attached_disk {
    source      = google_compute_disk.data.id
    device_name = "hyprn-data"
    mode        = "READ_WRITE"
  }
  network_interface {
    subnetwork = var.subnetwork
    stack_type = "IPV4_ONLY"
  }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
  metadata = { enable-oslogin = "TRUE", block-project-ssh-keys = "TRUE" }
  service_account {
    email  = var.runtime_service_account
    scopes = ["cloud-platform"]
  }
  labels = { environment = "staging", product = "hyprn-mvp", managed_by = "terraform" }
  lifecycle { prevent_destroy = true }
}
resource "google_iap_tunnel_instance_iam_member" "operator" {
  project  = var.project_id
  zone     = var.zone
  instance = google_compute_instance.staging.name
  role     = "roles/iap.tunnelResourceAccessor"
  member   = "group:${var.operator_group}"
  condition {
    title      = "ssh-only"
    expression = "destination.port == 22"
  }
}
resource "google_project_iam_member" "operator" {
  project = var.project_id
  role    = "roles/compute.osAdminLogin"
  member  = "group:${var.operator_group}"
}
resource "google_service_account_iam_member" "operator" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.runtime_service_account}"
  role               = "roles/iam.serviceAccountUser"
  member             = "group:${var.operator_group}"
}
