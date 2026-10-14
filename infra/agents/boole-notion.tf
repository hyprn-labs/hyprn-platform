# Boole Notion identities (Phase 4, OPS-02): secret containers declared
# NOT created. Values are added by the owner from the password manager
# (see runbooks/agents/meeting-loop-go.md), never through Terraform or
# Git. Vendor-side objects (Workspace user, Notion integration share) are
# owner checklists in the go-runbook, not resources here. No GitHub App
# in this file (Phase 5, OPS-03).

# Boole Workspace user: hand-created object boole at agents.hyprn.ai.
# Automation of user provisioning is deferred to FLT-02; nothing here
# creates or manages the user.

# Boole Notion token container plus the meetings-database reader note,
# following the host-only reader block.
locals {
  boole_notion_secrets = {
    "boole-agent-notion-token" = "boole"
  }
}

resource "google_secret_manager_secret" "boole_notion" {
  for_each  = local.boole_notion_secrets
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

resource "google_secret_manager_secret_iam_member" "boole_notion" {
  for_each  = google_secret_manager_secret.boole_notion
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.host.email}"
}
