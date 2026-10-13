# Controller scheduler wiring (Phase 3, CP-02/03/04 + ACC-09): dedicated
# least-privilege identity plus Cloud Scheduler transport to the queue.
# The SQLite poll loop in controller/dispatcher.py stays as the interim
# transport. REVIEWED ONLY — NOT APPLIED. Depends on accepted ADR-0006
# (the controller holding ops Socket Mode connections assumes it).
# Full validate plus plan plus apply runs at the owner-go step.

resource "google_service_account" "controller" {
  account_id   = "hyprn-agents-controller"
  display_name = "hyprn agents controller"
  description  = "Identity of the fleet controller; may only read run-state and the queue."
}

resource "google_project_iam_member" "controller" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/cloudsql.client",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.controller.email}"
}

resource "google_project_iam_custom_role" "queue_reader" {
  role_id     = "agentQueueReader"
  title       = "Agent run-queue reader"
  description = "Read queued runs; granted on the run-state database only."
  permissions = [
    "cloudsql.instances.get",
    "cloudsql.instances.connect",
  ]
}

resource "google_cloud_scheduler_job" "controller_poll" {
  name        = "hyprn-controller-poll"
  description = "Queue transport for the fleet controller (interim: SQLite poll loop in dispatcher)."
  schedule    = "*/1 * * * *"
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${google_cloud_run_v2_service.gateway.uri}/queue/poll"
  }

  labels = {
    component  = "agents"
    role       = "controller"
    managed_by = "terraform"
  }
}
