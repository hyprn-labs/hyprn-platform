# Gateway (Phase 3, CP-01 + ACC-09): LiteLLM proxy on Cloud Run with
# internal-only ingress and a managed Postgres for key, budget and spend
# state. REVIEWED ONLY — NOT APPLIED. Depends on accepted ADR-0006.
# No `terraform apply`, no key creation, no Secret Manager writes here;
# full validate plus plan plus apply runs at the owner-go step (terraform
# binary is absent on this machine). Secret values are owner-supplied from
# the password manager, never through Terraform or Git.

# Per-loop virtual keys plus dollar budgets with per-run spend attribution
# (Pitfall 1: budgets silently do nothing without the database below).
locals {
  loop_keys = {
    "meeting-test" = 30
  }
}

resource "google_service_account" "gateway" {
  account_id   = "hyprn-agents-gateway"
  display_name = "hyprn agents gateway"
  description  = "Identity of the model gateway; reads its own secrets and writes spend state."
}

resource "google_project_iam_member" "gateway" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_sql_database_instance" "gateway" {
  name             = "hyprn-gateway-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.agents.id
    }
  }

  labels = {
    component  = "agents"
    role       = "gateway-db"
    managed_by = "terraform"
  }
}

resource "google_cloud_run_v2_service" "gateway" {
  name     = "hyprn-gateway"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    containers {
      # Version tag below; the owner pins the exact digest at the apply
      # review (digest unverifiable from this machine — see go-runbook).
      image = "ghcr.io/berriai/litellm:main-v1.52.14"

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gateway_db_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "LITELLM_MASTER_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gateway_master_key.secret_id
            version = "latest"
          }
        }
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.gateway.connection_name]
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 3
    }
  }

  labels = {
    component  = "agents"
    role       = "gateway"
    managed_by = "terraform"
  }
}

# No google_cloud_run_v2_service_iam_member with roles/run.invoker for
# allUsers or allAuthenticatedUsers: the gateway stays unreachable from
# the internet (ACC-09). Invoker grants, if ever needed, go to named
# service accounts only.

resource "google_secret_manager_secret" "gateway_db_url" {
  secret_id = "gateway-db-url"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    role       = "gateway"
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret" "gateway_master_key" {
  secret_id = "gateway-master-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    role       = "gateway"
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "gateway_secrets" {
  for_each = {
    db_url     = google_secret_manager_secret.gateway_db_url.id
    master_key = google_secret_manager_secret.gateway_master_key.id
  }
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.gateway.email}"
}
