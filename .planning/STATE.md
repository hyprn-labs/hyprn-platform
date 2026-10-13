---
gsd_state_version: '1.0'
status: planning
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-13)

**Core value:** Agents do HYPRN's engineering and operations work — on request and on their own triggers — safely, with costs known, and they get better from feedback; adding an agent is one command.
**Current focus:** Phase 1 - Security baseline

## Current Position

Phase: 1 of 7 (Security baseline, M1)
Plan: 0 of 0 in current phase
Status: Ready to plan
Last activity: 2026-10-13 - Documents reviewed: spec, ADR-0006, requirements (57) and roadmap aligned; Boole named as the operations agent

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

Decisions are logged in PROJECT.md (Key Decisions). Recent decisions affecting current work:

- ADR-0001 as amended by ADR-0002, ADR-0003 and ADR-0005 is locked; ADR-0004 is superseded by ADR-0005; ADR-0006 is proposed and must be accepted before Phase 3.
- Milestones in value order: M1 safe engineering agent, M2 Boole (operations agent on open models at Fireworks) with a learning meeting loop, M3 scale the fleet.
- Run state lives in its own database on the gateway's Cloud SQL instance.
- The GitHub Team plan ruleset is in Phase 1 (GHE-01, GHE-03); deny rules (POL-04) stay as a second layer.
- Boole's run containers are egress-restricted from their first run (EGR-03, Phase 3).
- Codd (AI agent), Linux user `codd`, runs OpenCode 1.19.0 with Muse Spark 1.3 Contributor Free on OpenCode Zen, steered by the owner in the terminal or herdr. Meta may train on its prompts and completions; accepted for `hyprn-platform` only, enforced by its GitHub App being installed there only and by the Linux user boundary. No Slack app and no Workspace user (Codd pattern, spec §2–§3). Not retired: model moves to protective terms on the company move (`runbooks/agents/opencode.md`).
- Meeting loop targets: at least 10 meetings in two weeks, 30 USD a month; promotion to A2 at ≥ 90 % eval pass over the last 10 runs and < 1 correction per meeting.

### Inventory

| Item | Value |
|---|---|
| Organization | `hyprn.ai`, ID `1071176223527` |
| Billing account | `01CF81-DB21A5-2DAFB0` (EUR) |
| Admin group | `gcp-admins@hyprn.ai` (security group) |
| Projects | `hyprn-bootstrap` (`398807288756`), `hyprn-agents` (`605123398847`, folder `agents` `86446816109`) |
| Terraform state | `gs://hyprn-bootstrap-tfstate/bootstrap/`, `gs://hyprn-agents-tfstate/agents/` |
| VMs | `hyprn-agents-host-01` (`t2d-standard-8`, 10.10.0.3, on demand), `hyprn-agents-wake-01` (`e2-micro`, 10.10.0.2, always on) |
| Secrets | `ada-agent-slack-app-token`, `ada-agent-slack-bot-token`, `ada-agent-github-app-key`, `codd-agent-github-app-key` (v1 each), `agents-slack-allowed-users` (v3) |
| Claude Code on host | 2.1.287, plugin `slack@hyprn-agents` 0.1.1 |
| GitHub | organization `hyprn-labs` (Free plan); repositories `hyprn-platform`, `hyprn-mvp`; GitHub Apps `ada-agent-hyprn` (App ID 5299141, installation 170941397, all repositories) and `codd-agent-hyprn` (App ID 5306008, installation 171119571, `hyprn-platform` only); interim machine account removed |

### Operational Notes

Gotchas met while building the fleet; read before operating it.

- Org Policy API: concurrent writes on one organization fail with `CONCURRENT_POLICY_CHANGES`; run `bootstrap/` with `-parallelism=1`.
- User credentials need a quota project for several APIs (Cloud Identity, Org Policy, Budgets); Terraform sets `billing_project` to `hyprn-bootstrap`, gcloud takes `--billing-project=hyprn-bootstrap`. Without it, Cloud Identity group lookups report "no such group".
- On Google Cloud the metadata server address `169.254.169.254` is also the DNS resolver: blocking it for agent users must keep port 53 open.
- Claude Code may replace a channel server a few seconds after start; work done in that first instance is lost. The Slack server therefore repeats its catch-up at 5, 30 and 90 s.
- The desktop terminal pane does not pass Ctrl-D to a command: load secrets with `pbpaste | gcloud secrets versions add … --data-file=-`, never by typing into standard input. Check values by shape only.
- A Slack App ID (`A…`) looks like a member ID; allowlist entries must start with `U` (or `W`).
- A GitHub App installation token never exceeds the App's permissions or its installation's repositories; the broker mints it with an explicit permission set. A token minted just before a secret reload is lost, so the loader mints on every start.
- Workstation tools default to other identities: use the hyprn gcloud configuration and `GH_CONFIG_DIR`; this repository's `.git/config` resets inherited credential helpers and uses only the hyprn `gh` login. Shell aliases are unavailable in non-interactive shells.
- Idle stop: an open SSH terminal keeps the host on only while it gets input (`/dev/pts` access time); SSH connections without a terminal count only while a command runs, because a laptop's SSH tooling may hold idle connections open.
- Plain `gcloud projects delete` in a shell without the hyprn configuration fails with "no active account"; that is the safeguard working.

### Pending Todos

- Monthly until company terms: re-check Codd's free-tier model, cost and data terms against the Zen list (CODD-03).
- On the company move: shift Codd's model binding to protective terms by configuration; IP transfers to the company (CODD-03). Codd is not retired.
- Purchases arrive later (owner, 2026-10-13): GitHub Team plan, revised budget (COST-01), Fireworks/Anthropic/OpenAI keys; phases proceed on deny-rules and prototyping terms until then.
- Before Phase 3: accept ADR-0006; Fireworks account and key; Anthropic Console organization linked to the Team plan, with its key; OpenAI API key; Boole's Slack app; revised budget (COST-01). Choose the harness for Boole's runs (OpenCode or a workflow script) during Phase 3 planning (RT-01).
- Before Phase 4: settle how Granola notes reach Notion (LOOP-01).
- Phase 1: GitHub Team plan (owner purchase).
- Phase 6 spikes: channels with a `setup-token` sign-in (FLT-05); Slack icon through `apps.icon.set` (FLT-03); Workspace user creation by API (FLT-02).

### Blockers/Concerns

- GitHub Free: no ruleset on private repositories; Ada's App writes to all repositories and Codd's to `hyprn-platform`, so deny rules are the only control until the Team plan (purchases arrive later).
- Prototyping accounts: all current development is under the owner's personal accounts with free-tier training-use terms; IP moves to the future company, then bindings move to protective terms.
- `strictKnownMarketplaces` is not evidenced as set (POL-03).
- Slack Free allows 10 apps in total: the fleet tops out around eight agents (FLEET-05).
- Vendor limits on automation (checked 2026-10-13): no Claude Team member API; Slack Socket Mode tokens and app installs need a human; GitHub App installation and logo need a human.
- Owner steps (admin console, GitHub settings, Secret Manager values) need the platform owner's explicit go for each step; infrastructure applies need authorization for the exact plan.
- Worktree isolation is complete only once the product reads port, Compose project and database overrides from the environment (product work).

## Deferred Items

| Category | Item | Trigger | Recorded |
|----------|------|---------|----------|
| Fleet | Further engineering agents on Claude seats (FLEET-01) | Anthropic's answer on agent seats | 2026-10-12 |
| Fleet | GitHub Issues intake, Slack plan (FLEET-04, FLEET-05) | Queued work across agents; nearing 10 Slack apps | 2026-10-13 |
| Tools | Finance and e-signature (TOOL-01); webhook receiver (WEB-01) | First loop that needs them; polling not enough | 2026-10-13 |
| Platform | Staging and prod build-out (PLAT-01, PLAT-02) | The product's local edition | 2026-10-12 |

## Session Continuity

Last session: 2026-10-13
Stopped at: Value-first milestones and agent fleet specification reviewed; ready for `/gsd-plan-phase 1`
Resume file: None
