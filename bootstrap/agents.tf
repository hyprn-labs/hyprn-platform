# Agent fleet project (ADR-0001, section 3). Tooling, not an environment.

resource "google_folder" "agents" {
  display_name        = "agents"
  parent              = local.org
  deletion_protection = true
}

resource "google_org_policy_policy" "agents_no_external_ip" {
  name   = "${google_folder.agents.name}/policies/compute.vmExternalIpAccess"
  parent = google_folder.agents.name

  spec {
    rules {
      deny_all = "TRUE"
    }
  }
}

resource "google_project" "agents" {
  name                = "hyprn agents"
  project_id          = var.agents_project_id
  folder_id           = google_folder.agents.folder_id
  billing_account     = var.billing_account
  auto_create_network = false
  deletion_policy     = "PREVENT"

  labels = {
    component  = "agents"
    managed_by = "terraform"
  }

  depends_on = [
    google_org_policy_policy.enforced,
    google_org_policy_policy.resource_locations,
    google_org_policy_policy.agents_no_external_ip,
  ]
}

locals {
  agents_services = toset([
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iap.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "oslogin.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
  ])
}

resource "google_project_service" "agents" {
  for_each = local.agents_services

  project            = google_project.agents.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_project_iam_member" "agents_admins_owner" {
  project = google_project.agents.project_id
  role    = "roles/owner"
  member  = "group:${var.admins_group}"
}

# The admins group manages the agents folder's log sinks (infra/agents/detect.tf)
# and reads its logs.
resource "google_folder_iam_member" "agents_admins_logging" {
  for_each = toset(["roles/logging.configWriter", "roles/logging.viewer"])
  folder   = google_folder.agents.name
  role     = each.key
  member   = "group:${var.admins_group}"
}

moved {
  from = google_folder_iam_member.agents_admins_logging
  to   = google_folder_iam_member.agents_admins_logging["roles/logging.configWriter"]
}

# State for infra/agents/, kept inside the agents project.
resource "google_storage_bucket" "agents_tfstate" {
  name                        = "${var.agents_project_id}-tfstate"
  project                     = google_project.agents.project_id
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      with_state         = "ARCHIVED"
      num_newer_versions = 20
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    component  = "agents"
    managed_by = "terraform"
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.agents]
}

resource "google_billing_budget" "agents" {
  billing_account = var.billing_account
  display_name    = "${var.agents_project_id} monthly"

  budget_filter {
    projects = ["projects/${google_project.agents.number}"]
  }

  amount {
    specified_amount {
      currency_code = "EUR"
      units         = tostring(var.agents_monthly_budget_eur)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.8
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}
