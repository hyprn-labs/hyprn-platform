# Secret containers per agent; values are added by the owner from the password
# manager (see runbooks/agents/slack.md), never through Terraform or Git.
# Read access is granted per secret to the host (agent sessions, through the
# root-owned loader) and the wake service.

locals {
  agent_secrets = {
    for pair in setproduct(var.agents, ["slack-app-token", "slack-bot-token"]) :
    "${pair[0]}-${pair[1]}" => pair[0]
  }
}

resource "google_secret_manager_secret" "agent" {
  for_each  = local.agent_secrets
  secret_id = "agent-${each.key}"

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

resource "google_secret_manager_secret_iam_member" "host" {
  for_each  = google_secret_manager_secret.agent
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.host.email}"
}

resource "google_secret_manager_secret_iam_member" "wake" {
  for_each  = google_secret_manager_secret.agent
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.wake.email}"
}

# Slack user IDs allowed to instruct agents and approve their actions
# (JSON list). Kept out of Git; readable by the host loader and the wake service.
resource "google_secret_manager_secret" "slack_allowed_users" {
  secret_id = "agents-slack-allowed-users"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "allowed_users" {
  for_each = {
    host = google_service_account.host.email
    wake = google_service_account.wake.email
  }
  secret_id = google_secret_manager_secret.slack_allowed_users.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

# GitHub token per agent (interim machine account, ADR-0004); host only.
resource "google_secret_manager_secret" "agent_github" {
  for_each  = toset(var.agents)
  secret_id = "agent-${each.key}-github-token"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    agent      = each.key
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "host_github" {
  for_each  = google_secret_manager_secret.agent_github
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.host.email}"
}

# Per-agent secrets named <name>-agent-<purpose> (conventions/README.md).
# The agent-<name>-<purpose> resources above are removed once these hold the values.
locals {
  agent_slack_secrets = {
    for pair in setproduct(var.agents, ["slack-app-token", "slack-bot-token"]) :
    "${pair[0]}-agent-${pair[1]}" => pair[0]
  }
}

resource "google_secret_manager_secret" "agent_slack" {
  for_each  = local.agent_slack_secrets
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

resource "google_secret_manager_secret_iam_member" "agent_slack" {
  for_each = {
    for pair in setproduct(keys(local.agent_slack_secrets), ["host", "wake"]) :
    "${pair[0]}-${pair[1]}" => { secret = pair[0], reader = pair[1] }
  }
  secret_id = google_secret_manager_secret.agent_slack[each.value.secret].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.reader == "host" ? google_service_account.host.email : google_service_account.wake.email}"
}

resource "google_secret_manager_secret" "agent_github_token" {
  for_each  = toset(var.agents)
  secret_id = "${each.key}-agent-github-token"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    agent      = each.key
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "agent_github_token" {
  for_each  = google_secret_manager_secret.agent_github_token
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.host.email}"
}
