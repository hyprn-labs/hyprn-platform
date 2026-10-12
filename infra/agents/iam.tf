# VM identity. Secret access is granted per secret when secrets are added
# (parts C and D), never project-wide.
resource "google_service_account" "host" {
  account_id   = "hyprn-agents-host"
  display_name = "hyprn agents host"
  description  = "Identity of the agent host VM; logs, metrics and named secrets only."
}

resource "google_project_iam_member" "host" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.host.email}"
}

# Administrator access to the host, explicit rather than implied by Owner.
resource "google_project_iam_member" "admins" {
  for_each = toset([
    "roles/iap.tunnelResourceAccessor",
    "roles/compute.osAdminLogin",
  ])

  project = var.project_id
  role    = each.key
  member  = "group:${var.admins_group}"
}

resource "google_service_account_iam_member" "admins_use_host" {
  service_account_id = google_service_account.host.name
  role               = "roles/iam.serviceAccountUser"
  member             = "group:${var.admins_group}"
}
