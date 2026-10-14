# Finding: FLT-02 Workspace user automation probe (DWD-free Directory users.insert)

**Date:** 2026-10-14
**Probe:** FLT-02 — can a directly role-assigned service account create
`<name>@agents.hyprn.ai` users via Directory `users.insert` with no
domain-wide delegation (which the specification forbids)?
**Time-box:** ~2h, static evidence only (no live vendor access from this environment).

## Verdict: MANUAL STEP

Standing verdict: manual step. Owner-console user creation (or an API-delegated
call under owner credentials) is the standing procedure until a DWD-free
`users.insert` is proven from an environment holding the User Management Admin
grant.

## Evidence

- This environment has no Terraform binary (applies happen on the owner's
  workstation per AGENTS.md) and no Workspace admin credentials, so no live
  Directory API call was possible here; the probe is recorded as blocked, not
  as a negative result.
- Official docs confirm the prebuilt User Management Admin role can
  create/delete users via console and Admin API, and that a prebuilt role can
  be assigned to a service account via Admin → Account → Admin roles
  (super-admin action) — the grant path exists.
- Community flows for service-account Directory writes use delegation plus
  impersonation [ASSUMED]; whether `users.insert` succeeds with only the role
  grant (the DWD-free path the spec requires) is unproven and needs one live
  call from the owner's workstation.
- `infra/agents/workspace.tf` declares the automation service account plus the
  role shape; the admin-role grant and Ada's group→user move are marked there
  as owner console steps that code does not perform.

## Standing procedure

1. Owner assigns the prebuilt User Management Admin role to
   `workspace-user-admin@hyprn-agents.iam.gserviceaccount.com` in the Admin
   console (one-time prerequisite, see runbooks/agents/onboarding.md).
2. Until the DWD-free probe succeeds live, agent users are created in the
   owner console (or one API-delegated call under owner credentials); passwords
   and second factors live in the company password manager.
3. Ada's address moves from group to user as an owner console step (M3).

## Secrets

None handled: no tokens or credentials were created, printed, or stored.
