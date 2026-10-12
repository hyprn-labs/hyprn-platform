# Wake service (ADR-0002): a small always-on VM that listens to Slack over
# Socket Mode while the host is stopped and starts it on the owner's message.
# It can only read, start and stop the host instance.

resource "google_service_account" "wake" {
  account_id   = "hyprn-agents-wake"
  display_name = "hyprn agents wake"
  description  = "Identity of the wake VM; may only get, start and stop the agent host."
}

resource "google_project_iam_member" "wake" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.wake.email}"
}

resource "google_project_iam_custom_role" "host_power" {
  role_id     = "agentHostPower"
  title       = "Agent host power control"
  description = "Read, start and stop one instance; granted on the instance only."
  permissions = [
    "compute.instances.get",
    "compute.instances.start",
    "compute.instances.stop",
  ]
}

resource "google_compute_instance_iam_member" "wake_host_power" {
  zone          = var.zone
  instance_name = google_compute_instance.host.name
  role          = google_project_iam_custom_role.host_power.id
  member        = "serviceAccount:${google_service_account.wake.email}"
}

resource "google_service_account_iam_member" "admins_use_wake" {
  service_account_id = google_service_account.wake.name
  role               = "roles/iam.serviceAccountUser"
  member             = "group:${var.admins_group}"
}

resource "google_compute_instance" "wake" {
  name                      = "hyprn-agents-wake-01"
  machine_type              = var.wake_machine_type
  zone                      = var.zone
  allow_stopping_for_update = true

  boot_disk {
    auto_delete = true
    initialize_params {
      image = var.host_image
      size  = 10
      type  = "pd-standard"
    }
  }

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
    email  = google_service_account.wake.email
    scopes = ["cloud-platform"]
  }

  labels = {
    component  = "agents"
    role       = "wake"
    managed_by = "terraform"
  }

  depends_on = [
    google_project_iam_member.wake,
    google_compute_router_nat.agents,
  ]
}
