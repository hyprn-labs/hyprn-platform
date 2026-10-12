---
gsd_state_version: '1.0'
status: planning
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-12)

**Core value:** The platform owner gives Ada a task in Slack and receives a reviewable draft pull request, and no path exists from the agent fleet to staging or prod credentials.
**Current focus:** Phase 1 - Enforced agent policy

## Current Position

Phase: 1 of 4 (Enforced agent policy)
Plan: 0 of 0 in current phase
Status: Ready to plan
Last activity: 2026-10-12 - Roadmap created from ingest of 9 documents; 19 v1 requirements mapped to 4 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- ADR-0001 as amended by ADR-0002, ADR-0003 and ADR-0004 is locked.
- ADR-0003 is accepted (DOC-01 complete): our own Slack channel server is the plugin.
- Until the organization has a paid GitHub plan, Claude Code deny rules for merge and push to `main` are the enforcing control (POL-04).

### Inventory

| Item | Value |
|---|---|
| Organization | `hyprn.ai`, ID `1071176223527` |
| Billing account | `01CF81-DB21A5-2DAFB0` (EUR) |
| Admin group | `gcp-admins@hyprn.ai` (security group) |
| Projects | `hyprn-bootstrap` (`398807288756`), `hyprn-agents` (`605123398847`, folder `agents` `86446816109`) |
| Terraform state | `gs://hyprn-bootstrap-tfstate/bootstrap/`, `gs://hyprn-agents-tfstate/agents/` |
| VMs | `hyprn-agents-host-01` (`t2d-standard-8`, 10.10.0.3, on demand), `hyprn-agents-wake-01` (`e2-micro`, 10.10.0.2, always on) |
| Secrets | `ada-agent-slack-app-token`, `ada-agent-slack-bot-token`, `ada-agent-github-token` (v1 each), `agents-slack-allowed-users` (v3); former `agent-ada-*` secrets pending deletion |
| Claude Code on host | 2.1.287, plugin `slack@hyprn-agents` 0.1.1 |
| GitHub | organization `hyprn-labs` (Free plan); repositories `hyprn-platform`, `hyprn-mvp`; agent account `ada-agent-hyprn` (Write on both) |

### Operational Notes

Gotchas met while building the fleet; read before operating it.

- Org Policy API: concurrent writes on one organization fail with `CONCURRENT_POLICY_CHANGES`; run `bootstrap/` with `-parallelism=1`.
- User credentials need a quota project for several APIs (Cloud Identity, Org Policy, Budgets); Terraform sets `billing_project` to `hyprn-bootstrap`, gcloud takes `--billing-project=hyprn-bootstrap`. Without it, Cloud Identity group lookups report "no such group".
- On Google Cloud the metadata server address `169.254.169.254` is also the DNS resolver: blocking it for agent users must keep port 53 open.
- Claude Code may replace a channel server a few seconds after start; work done in that first instance is lost. The Slack server therefore repeats its catch-up at 5, 30 and 90 s.
- The desktop terminal pane does not pass Ctrl-D to a command: load secrets with `pbpaste | gcloud secrets versions add … --data-file=-`, never by typing into standard input. Check values by shape only.
- A Slack App ID (`A…`) looks like a member ID; allowlist entries must start with `U` (or `W`).
- A fine-grained GitHub token reaches organization repositories only with resource owner `hyprn-labs`, selected repositories, and organization approval when required; it never exceeds the account's own repository role.
- Workstation tools default to other identities: use the hyprn gcloud configuration and `GH_CONFIG_DIR`; this repository's `.git/config` resets inherited credential helpers and uses only the hyprn `gh` login. Shell aliases are unavailable in non-interactive shells.
- Plain `gcloud projects delete` in a shell without the hyprn configuration fails with "no active account"; that is the safeguard working.

### Pending Todos

- Delete the former `agent-ada-*` secrets (Terraform) and the two earlier tokens in the agent account (Phase 2, GH-03).
- Land the branches `feat/ada-github` and `docs/sharpen` on `main` through pull requests.

### Blockers/Concerns

- The GitHub organization is on the Free plan: no ruleset or branch protection on private repositories. `ada-agent-hyprn` has Write on two repositories, so Phase 1 deny rules are the only control until the plan is upgraded (deferred GHE-01).
- Draft-pull-request test from Slack is not yet done (Phase 2).
- `strictKnownMarketplaces` is not evidenced as set (POL-03).
- Owner steps (admin console, GitHub settings, Secret Manager changes) need the platform owner's explicit go for each step; infrastructure applies need authorization for the exact plan.
- Worktree isolation is complete only once the product reads port, Compose project and database overrides from the environment (product work).

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| GitHub | Team plan, ruleset on `main`, CODEOWNERS (GHE-01) | Waiting on plan upgrade | 2026-10-12 | Agent fleet operational |
| GitHub | GitHub App replacing the machine account (GHE-02) | Waiting on GHE-01 | 2026-10-12 | Agent fleet operational |
| Fleet | Agent #2 (FLEET-01) | Gated on Anthropic's human answer on agent seats | 2026-10-12 | Agent fleet operational |
| Platform | Staging and prod build-out (PLAT-01) | Follows the product's local edition | 2026-10-12 | Agent fleet operational |

## Session Continuity

Last session: 2026-10-12
Stopped at: Roadmap and state initialized; ready for `/gsd-plan-phase 1`
Resume file: None
