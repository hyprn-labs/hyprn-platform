# Boole runtime identities (Phase 3, OPS-01 + ACC-09): secret containers
# plus key blocks, declared NOT created. Values are added by the owner from
# the password manager (see runbooks/agents/control-plane-go.md), never
# through Terraform or Git. Vendor-side objects (Slack app install) are
# owner checklists in the go-runbook, not resources here.

# Boole Slack app token pair plus the gateway virtual-key placeholder and
# the agent key, following the host-only reader block.
locals {
  boole_secrets = {
    "boole-agent-slack-app-token" = "boole"
    "boole-agent-slack-bot-token" = "boole"
    "boole-agent-gateway-key"     = "boole"
  }
}

resource "google_secret_manager_secret" "boole" {
  for_each  = local.boole_secrets
  secret_id = each.key

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    agent      = each.value
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "boole" {
  for_each  = google_secret_manager_secret.boole
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.host.email}"
}

# Boole GitHub App private key (ADR-0005); read by the root token broker on
# the host only, never by the agent.
resource "google_secret_manager_secret" "boole_github_app_key" {
  secret_id = "boole-agent-github-app-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    agent      = "boole"
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "boole_github_app_key" {
  secret_id = google_secret_manager_secret.boole_github_app_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.host.email}"
}

# Linux user boole is declared in host provisioning alongside the existing
# agent list inputs (var.agents gains "boole" at apply review).

# COST-01 budget placeholder (owner-set at the go checkpoint, never applied):
# budget_amount_usd = 200  # revised hyprn-agents monthly figure, owner confirms
