# Workspace user automation shape (Phase 6, FLT-02): code plus role shape only.
#
# Agent users <name>@agents.hyprn.ai are created and configured through the
# automation service account below, which is intended to hold the prebuilt
# User Management Admin role (creates and deletes users via the Admin console
# and the Admin SDK Directory API).
#
# OWNER CONSOLE STEPS — this code does not perform them (AGENTS.md authority):
# - Assign the prebuilt User Management Admin role to the automation service
#   account via Google Admin -> Account -> Admin roles (a super-admin action).
# - Ada's group-to-user move (ada@agents.hyprn.ai from group to user).
#
# No domain-wide delegation anywhere: the specification forbids DWD, so the
# FLT-02 spike probes the DWD-free Directory users.insert path and, on
# failure, locks the owner-console fallback as the standing step (recorded in
# runbooks/agents/workspace-finding-2026-10-14.md).

resource "google_service_account" "workspace_user_admin" {
  account_id   = "workspace-user-admin"
  display_name = "Agent Workspace user automation (FLT-02)"
  description  = "Creates and configures <name>@agents.hyprn.ai users with the prebuilt User Management Admin role (owner-granted in the Admin console). No domain-wide delegation."
}

locals {
  # Shape of the Workspace automation (role grant itself is an owner step).
  workspace_user_domain = "agents.hyprn.ai"

  # Prebuilt role, assigned by display name in Google Admin -> Account ->
  # Admin roles by the owner; referenced here so plan review shows the
  # intended privilege (least privilege: user management only, never Super
  # Admin).
  workspace_admin_role = "User Management Admin (prebuilt Admin console role)"

  # Steady state per agent (fleet.yaml workspace field): user for operations
  # agents, none for terminal-only agents; group is Ada's transient pre-move
  # state until the owner performs the group-to-user move.
  workspace_steady_states = ["user", "none"]
}
