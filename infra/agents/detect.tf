# Misuse detection (DET-01/02, Phase 1 security baseline).
#
# Reviewed definition; the apply itself is an owner-go step recorded in
# runbooks/agents/gcp.md (never automated, per AGENTS.md authority rules).
# No secret value, key file, or credential literal appears in this file.
#
# Design: DATA_READ audit logging for Secret Manager (disabled by default —
# alerts never fire without it), two log-based alert policies emailing the
# admins group, and a folder-level log sink into the agents project so
# folder-level IAM changes feed the same IAM alert path.

variable "agents_folder_id" {
  description = "Numeric ID of the agents folder (bootstrap output agents_folder); the folder sink's source."
  type        = string
}

# DET-01 half 1: DATA_READ audit logs for Secret Manager cover
# secretmanager.versions.access (= AccessSecretVersion reads).
resource "google_project_iam_audit_config" "secretmanager_data_read" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
  audit_log_config {
    log_type = "DATA_READ"
  }
}

# Email channel to the admins group (deliverability proven by canary alerts).
resource "google_monitoring_notification_channel" "admins_email" {
  project      = var.project_id
  display_name = "hyprn agents admin email"
  type         = "email"
  labels = {
    email_address = var.admins_group
  }
}

# DET-01: unexpected secret reads plus secret creation, deletion, and
# new-reader grants, excluding the declared host and wake identities.
# Controller and gateway identities do not exist yet (Phases 3-5); their
# exclusions are added with those identities, never as silent widenings.
resource "google_monitoring_alert_policy" "secret_unexpected_access" {
  project      = var.project_id
  display_name = "hyprn agents: unexpected secret access"
  combiner     = "OR"
  conditions {
    display_name = "unexpected read, create, delete, or grant"
    condition_matched_log {
      filter = <<-EOT
        protoPayload.@type = "type.googleapis.com/google.cloud.audit.AuditLog"
        protoPayload.serviceName = "secretmanager.googleapis.com"
        (protoPayload.methodName =~ "AccessSecretVersion$" OR protoPayload.methodName = "CreateSecret" OR protoPayload.methodName = "DeleteSecret" OR (protoPayload.methodName = "SetIamPolicy" AND protoPayload.request.policy.bindings.role = "roles/secretmanager.secretAccessor"))
        -protoPayload.authenticationInfo.principalEmail = "${google_service_account.host.email}"
        -protoPayload.authenticationInfo.principalEmail = "${google_service_account.wake.email}"
      EOT
    }
  }
  notification_channels = [google_monitoring_notification_channel.admins_email.id]
  alert_strategy {
    auto_close = "86400s"
    notification_rate_limit {
      period = "300s"
    }
  }
  labels = {
    component  = "agents"
    managed_by = "terraform"
  }
}

# DET-02: any IAM policy change in the agents project.
resource "google_monitoring_alert_policy" "agents_iam_change" {
  project      = var.project_id
  display_name = "hyprn agents: IAM policy change"
  combiner     = "OR"
  conditions {
    display_name = "SetIamPolicy in the agents project"
    condition_matched_log {
      filter = <<-EOT
        protoPayload.@type = "type.googleapis.com/google.cloud.audit.AuditLog"
        protoPayload.methodName = "SetIamPolicy"
        resource.labels.project_id = "${var.project_id}"
      EOT
    }
  }
  notification_channels = [google_monitoring_notification_channel.admins_email.id]
  alert_strategy {
    auto_close = "86400s"
    notification_rate_limit {
      period = "300s"
    }
  }
  labels = {
    component  = "agents"
    managed_by = "terraform"
  }
}

# DET-02 second half: folder-level agents changes sink into the agents
# project so they travel the same IAM alert path.
resource "google_logging_folder_sink" "agents_folder_to_project" {
  name        = "agents-folder-iam-to-project"
  folder      = var.agents_folder_id
  destination = "logging.googleapis.com/projects/${var.project_id}"
  filter      = "protoPayload.methodName = \"SetIamPolicy\""
}
