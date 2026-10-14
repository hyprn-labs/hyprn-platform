# Misuse detection (agent fleet specification section 13; DET-01, DET-02):
# Secret Manager data-read audit logs, an email channel to the admins group,
# and two log-based alerts on the hyprn-agents project.

# Secret reads (AccessSecretVersion) are data-read events, off by default.
resource "google_project_iam_audit_config" "secretmanager_data_read" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
  audit_log_config {
    log_type = "DATA_READ"
  }
}

resource "google_monitoring_notification_channel" "admins_email" {
  project      = var.project_id
  display_name = "hyprn agents: admins"
  type         = "email"
  labels = {
    email_address = var.admins_group
  }
}

# Any secret read, creation, deletion or reader grant by a principal other
# than the host and wake identities. Identities added in later phases are
# excluded here by a reviewed change, never by widening the filter.
resource "google_monitoring_alert_policy" "secret_unexpected_access" {
  project      = var.project_id
  display_name = "hyprn agents: unexpected secret access"
  combiner     = "OR"
  conditions {
    display_name = "Unexpected secret read, creation, deletion or grant"
    condition_matched_log {
      filter = <<-EOT
        protoPayload.serviceName="secretmanager.googleapis.com"
        (protoPayload.methodName:"AccessSecretVersion" OR protoPayload.methodName:"CreateSecret" OR protoPayload.methodName:"DeleteSecret" OR protoPayload.methodName:"SetIamPolicy")
        protoPayload.authenticationInfo.principalEmail!="${google_service_account.host.email}"
        protoPayload.authenticationInfo.principalEmail!="${google_service_account.wake.email}"
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
  user_labels = {
    component = "agents"
  }
}

# Any IAM policy change on the agents project.
resource "google_monitoring_alert_policy" "agents_iam_change" {
  project      = var.project_id
  display_name = "hyprn agents: IAM policy change"
  combiner     = "OR"
  conditions {
    display_name = "SetIamPolicy on the agents project"
    condition_matched_log {
      filter = <<-EOT
        protoPayload.methodName="SetIamPolicy"
        protoPayload.serviceName!="secretmanager.googleapis.com"
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
  user_labels = {
    component = "agents"
  }
}
