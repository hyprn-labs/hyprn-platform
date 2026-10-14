# Runbook: agent onboarding with fleet as code (FLT-08)

Adding or removing an engineering or operations agent is one command:
`agents/fleet.yaml` declares every agent and `agents/fleet add` / `agents/fleet
remove` onboard and offboard. Vendor approvals and secret values stay in owner
hands throughout: scripts take secret paths and handles only, never values.

This runbook consolidates the per-component procedures (it does not duplicate
them): Slack app and token loading ([slack.md](slack.md) sections 1-2), GitHub
App creation and rotation ([github.md](github.md)), the Codd pattern and the
remove contingency ([opencode.md](opencode.md)), host provisioning
([host.md](host.md)). Ada runs as a Workspace user; the group-to-user move is
an owner console step (M3).

## One-time prerequisites

- Workspace: owner grants the prebuilt User Management Admin role to the
  automation service account (`workspace-user-admin@hyprn-agents.iam.gserviceaccount.com`)
  via Google Admin → Account → Admin roles (super-admin action).
- Terraform: owner workstation with apply rights; plan, review, apply exactly
  the reviewed plan. Staging and prod have separate state and authority.
- Password manager access (master copy of every secret value; runtime copy is
  Secret Manager).
- Vendor console access: Slack workspace admin, GitHub organization owner,
  Claude organization admin.
- Tool configs: `CLOUDSDK_CONFIG` pointing at the HYPRN gcloud configuration
  and `GH_CONFIG_DIR` at the HYPRN GitHub configuration (without them a
  command runs as the wrong identity).

Out of scope: automating Claude seat invitations (no member API on the Team
plan), agents moving money or signing (never delegated), further seat agents
(FLEET-01, waits on Anthropic).

## Add an agent

Dry-run first (static, local, no cloud or vendor calls):

```bash
agents/fleet add <name> --kind engineering|operations [--harness claude|opencode] --dry-run
```

The dry-run validates the name and next-free UID, validates and renders a
provisional registry entry, shows the diff, prints the Terraform delta intent
and the numbered owner checklist (8 human actions), then changes nothing.

### Engineering, Claude harness (default)

`agents/fleet add <name> --kind engineering --dry-run`, then with an explicit
owner go for the real run. Owner checklist callouts:

1. Confirm the fleet.yaml entry (UID, App slug, kind, harness).
2. GitHub: confirm App creation plus install via the manifest flow
   ([github.md](github.md) create steps 1-3); discover IDs with
   `GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api orgs/hyprn-labs/installations`
   and the bot ID lookup ([github.md](github.md) step 4).
3. GitHub: load the App private key straight to `<name>-agent-github-app-key`
   by owner hands; delete the local `.pem` ([github.md](github.md) step 5).
4. Slack: paste the reviewed manifest, approve install ([slack.md](slack.md)
   step 1).
5. Slack: load the Socket Mode and bot tokens by owner hands to the
   `<name>-agent-slack-*` paths ([slack.md](slack.md) step 2); values travel
   `pbpaste | gcloud secrets versions add ... --data-file=-`, verified by
   shape only.
6. Workspace: owner-console user steps for `<name>@agents.hyprn.ai`.
7. Terraform: review the plan, apply exactly the reviewed plan.
8. Run `agents/host/apply.sh` (plus `agents/wake/apply.sh` for Slack agents),
   then `tests/agents/run.sh`.

STOP: the engineering test stops before the Claude seat invitation (no member
API; out of scope). Sign-in stays interactive `/login` until the setup-token
probe proves otherwise (see the vendor appendix).

### Engineering, Codd pattern (harness opencode)

`agents/fleet add <name> --kind engineering --harness opencode --dry-run`:
GitHub App plus Linux user plus OpenCode plus herdr control, proven by
dry-run ([opencode.md](opencode.md) use and model sections). The
`provision.sh add_agent` opencode branch is driven (it returns before
Claude/Slack setup); there is no Slack app, no Workspace user, no seat. The
agent is steered in the terminal via `opencode-task` and opens draft pull
requests the owner reviews and merges.

### Operations

`agents/fleet add <name> --kind operations --dry-run`: Slack app plus gateway
virtual key (`<name>-agent-gateway-key` placeholder per `infra/agents/boole.tf`),
Workspace user, App installed on the repositories its loops change. Runs the
checklist end to end in dry-run (no seat stop applies).

## Remove an agent

```bash
agents/fleet remove <name> --dry-run   # prints what would happen, touches nothing
agents/fleet remove <name> --owner-go  # removals get their own go
```

Order: revoke cloud identities and grants first, then `userdel -r` plus App
uninstall plus secret disable, then remove the YAML entry and re-render all
three generated files, then run `tests/agents/checks/fleet.sh`. The command
prints the remaining manual-steps table (generalized from the
[opencode.md](opencode.md) remove contingency):

- App deletion confirm (uninstall and delete `<name>-agent-hyprn`).
- Secret-version cleanup (disable `<name>-agent-*` versions after values are
  confirmed migrated or disabled).
- Workspace user delete or suspend in the owner console.
- Group-to-user notes recorded below.
- Host `userdel -r <name>`; Terraform destroy scope reviewed (secret
  containers only after values are confirmed migrated/disabled).

## Vendor appendix

- Workspace users: created and configured by the automation shape
  (`infra/agents/workspace.tf`); the admin-role grant and Ada's group-to-user
  move are owner console steps. DWD-free probe: [workspace-finding-2026-10-14.md](workspace-finding-2026-10-14.md)
  (verdict: manual step until proven live).
- Slack icon: generated icon handling resolved to manual upload until the API
  path is proven live: [slack-icon-finding-2026-10-14.md](slack-icon-finding-2026-10-14.md)
  (verdict: manual step; Socket Mode token creation stays manual regardless).
- Claude sign-in: setup-token path unresolved until a live channel test;
  interactive `/login` stays: [setup-token-finding-2026-10-14.md](setup-token-finding-2026-10-14.md)
  (verdict: manual step).
- Key rotation: per [github.md](github.md) (new key, new secret version,
  apply, confirm checks, delete old key, disable old version).

## Record

| Date | Action | Result |
|---|---|---|
| 2026-10-14 | Fleet registry proven (06-01): fleet.yaml renders regen-clean agents.txt, wake.json, tfvars; fleet.sh 15 checks green | Tracer committed; ada + codd round-trip with zero diff |
| 2026-10-14 | fleet add/remove drivers proven (06-02): timed dry-runs per kind, 8-action checklists, fail-closed without owner go | Dry-run evidence in fleet.sh output (0s, 8 actions per kind) |
| 2026-10-14 | Vendor spikes recorded as findings (06-03): Workspace, Slack icon, setup-token | All three verdict manual step; live probes are owner gates |
