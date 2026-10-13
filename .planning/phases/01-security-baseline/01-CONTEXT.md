# Phase 1: Security baseline - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove the platform's safety controls in one check command (`tests/agents/run.sh`, greenfield): repository protection, enforced agent policy, visible outbound traffic, misuse alerts, account safeguards — for Ada and Codd. The GitHub Team plan purchase is deferred, so the enforcing ruleset (GHE-01) cannot be satisfied in this phase; the phase proves everything else and leaves a reviewed ruleset definition ready to apply.

</domain>

<decisions>
## Implementation Decisions

### Team-plan-less scope (user approved autonomous run; decisions at agent discretion)

- **D-01:** GHE-01 enforcement is deferred to the Team-plan purchase (owner decision 2026-10-13, purchases arrive later). Phase 1 delivers a reviewed ruleset definition ready to apply plus proven Claude Code deny rules (POL-04) as the interim control. The planner MUST reshape success criterion 1 accordingly instead of planning an impossible apply.
- **D-02:** GHE-03 (refuse merge/push to `main` by Apps) is provable now through deny rules in both repositories; only its ruleset half is deferred with GHE-01.

### Codd repo scope (user approved autonomous run; decisions at agent discretion)

- **D-03:** The App-scope check covers both `hyprn-platform` and `hyprn-mvp` — Codd's App installation on both was verified 2026-10-13 by a branch push to each (commit `30ee1b1`). The stale "platform-only" lines merged earlier (REQUIREMENTS CODD-01, spec §2 GitHub row, README, PROJECT.md) are corrected inside Phase 1 as CODD-01 groundwork.
- **D-04:** `hyprn-mvp` carries no secrets and no staging/prod. Host-level controls (managed OpenCode policy, egress, Linux user boundary) cover both repositories identically; repo-level assertions (App scope, deny-rule refusals) are checked per repository.

### Egress observation (user approved autonomous run; decisions at agent discretion)

- **D-05:** Observe mode means per-agent, per-destination connection logs to Cloud Logging with no blocking. In scope: the `ada` and `codd` Linux users and their containers, plus wake-service traffic. DNS stays allowed — the metadata-server address is also the resolver, so blocking it must keep port 53 open (known gotcha).
- **D-06:** Observation runs continuously from Phase 1; allowlist enforcement stays Phase 7 (EGR-02). Phase 1 is done when logs flow per agent and the direct-connection drop test passes (existing success criterion 4).

### Checks shape (user approved autonomous run; decisions at agent discretion)

- **D-07:** Build `tests/agents/run.sh` on top of `tests/agents/host-checks.sh` (40 pass). Every check writes a dated record to `runbooks/agents/`. `agents/policy/` currently holds only a README — `managed-settings.json` and the egress allowlist file are created in this phase.
- **D-08:** Live-test deny-rule refusals (Ada session and Codd), the egress drop, and alert delivery. Owner-hand steps — break-glass admin, 2FA, admin-console policy match, alert test actions, IAM search with owner credentials — are explicit owner-go checklists the plan requests; the plan MUST NOT automate them. POL-03 (`strictKnownMarketplaces` evidence) is a must-verify item (flagged unevidenced in STATE.md).

### Agent's Discretion

The user approved all four areas beforehand and asked for an autonomous run. All decisions above were taken at agent discretion within locked prior decisions (deny-rules as interim control, deferred purchases, Codd on both repos, owner go per infra step). Anything the planner finds unimplementable should come back as a planning question, not a silent scope change.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition and requirements

- `.planning/ROADMAP.md` (Phase 1: goal, requirements, owner actions, success criteria 1–7)
- `.planning/REQUIREMENTS.md` (GHE-01, GHE-03, POL-01..04, EGR-01, DET-01/02, SEC-01/02, DOC-01, ACC-01..06, ACC-08, CODD-01)
- `.planning/PROJECT.md` (Context: prototyping terms, residual risks; Constraints: authority, secrets, separation)

### Target and decisions

- `docs/specs/agent-fleet.md` §13 — security invariants (ruleset, deny rules, egress, alerts, one-command checks)
- `docs/specs/agent-fleet.md` §1, §2, §3 — Codd pattern, App scope, runtimes
- `docs/adr/0001-agent-fleet.md` — fleet baseline (as amended)
- `docs/adr/0002-agent-host-on-demand.md` — host and wake service shape
- `docs/adr/0005-agent-github-app.md` — per-agent App with one-hour tokens
- `docs/adr/0006-agent-first-operating-model.md` (proposed) — gates Phase 3, not this phase
- `docs/adr/0007-codd-pattern-coding-agents.md` (proposed) — Codd pattern, both-repo scope, no retirement

### Runbooks and existing code

- `runbooks/agents/opencode.md` — Codd identity, managed config, both-repo verification record
- `runbooks/agents/claude.md` — Claude policy change record (POL-01 console side)
- `agents/host/files/egress.nft` — existing nftables ruleset to extend
- `agents/host/files/opencode.json` — managed OpenCode policy (CODD-01 evidence)
- `agents/host/files/hyprn-agents-egress.service` — egress service unit
- `agents/policy/README.md` — policy directory (managed-settings.json to be created here)
- `tests/agents/host-checks.sh` — 40 passing checks to build on
- `tests/agents/README.md` — test layout and conventions
- `.planning/codebase/ARCHITECTURE.md` — system design and control points
- `.planning/codebase/STRUCTURE.md` — directory layout and key locations
- `.planning/codebase/CONCERNS.md` — fragile areas (org-policy concurrency, quota project, metadata DNS)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `tests/agents/host-checks.sh`: 40 passing host checks — the foundation `run.sh` orchestrates (ACC-08).
- `agents/host/files/egress.nft` + `hyprn-agents-egress.service`: existing firewall base for EGR-01 observation work.
- `agents/host/files/hyprn-agent-secrets@.service` + `hyprn-agent-github-token@.service`: root-owned secret/token loaders relevant to DET-01 alert subjects.
- `agents/host/files/opencode.json`: managed, non-overridable OpenCode policy — CODD-01 evidence and POL-04-adjacent control for Codd.
- `agents/host/files/bin/gh`: App-token `gh` wrapper (ADR-0005) — the identity checks use.

### Established Patterns

- One command proves a domain: host checks run from a single script with counted passes — `run.sh` follows the same shape.
- `set -euo pipefail` scripts; root-owned marketplace and managed configs; dated records per run in `runbooks/agents/`.
- Terraform roots own cloud resources with reviewed plans; the host owns rendered runtime; neither rewrites the other.

### Integration Points

- `tests/agents/run.sh` (greenfield): orchestrates host checks plus new security checks.
- `agents/policy/` (greenfield except README): home for `managed-settings.json` and the egress allowlist.
- Cloud Logging (egress destinations per agent) and `gcp-admins@hyprn.ai` email (DET-01/02 alerts).
- GitHub deny rules in both repositories (interim enforcement point until the ruleset).

</code>

<specifics>
## Specific Ideas

- No specific requirements — open to standard approaches. Owner's standing direction: every infra/vendor step needs explicit per-step go; purchases arrive later; Codd's App covers both repositories.

</specifics>

<deferred>
## Deferred Ideas

- GHE-01 ruleset enforcement at Team-plan purchase time (deferred requirement, not in this phase).
- Boole, gateway, and control-plane work (Phases 3–5); fleet-as-code onboarding of Codd-pattern agents (Phase 6, CODD-02).

</deferred>

---

*Phase: 1-Security baseline*
*Context gathered: 2026-10-13*
