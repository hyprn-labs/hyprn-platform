# Phase 6: Fleet as code and onboarding - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning
**Mode:** Auto-discussed (user directed autonomous run without stops; all answers at agent discretion)

<domain>
## Phase Boundary

Adding or removing an engineering or operations agent is one command: `agents/fleet.yaml` declares every agent and replaces `agents/host/agents.txt` and `agents/wake/wake.json`; `fleet add`/`fleet remove` onboard and offboard test agents of each kind (incl. the Codd pattern, CODD-02); Workspace users per agent; Terraform, provisioning, controller and checks read the registry. Vendor approvals during test onboardings are owner checklists.

</domain>

<decisions>
## Implementation Decisions

### Registry replaces two files (auto-accepted at agent discretion)

- `agents/fleet.yaml` is the single declaration (name, kind, runtime binding, identities, grants) and generates `agents.txt` and `wake.json` content — consumers (Terraform, provisioning, controller, checks) read the registry; the two legacy files become generated or are removed once nothing reads them directly.
- Current registry content: ada (claude/seat/Slack, UID 20001) + codd (opencode/terminal, UID 20002). Schema must cover both shapes plus operations agents (Boole).

### fleet add/remove as scripts first (auto-accepted at agent discretion)

- `agents/fleet add <name> --kind engineering|operations` creates identities and grants, loads secrets straight into Secret Manager paths (values by owner hands only — scripts take paths/handles, never values), provisions runtime, runs checks. `remove` revokes/deletes and prints remaining manual steps.
- Test onboarding/offboarding of each kind within 15 minutes and ~8 human actions is proven by dry-run where vendor steps are stubbed as explicit go-checklists; live vendor approvals are owner gates.
- Codd-pattern onboarding (GitHub App + Linux user + OpenCode + herdr control, CODD-02) is a first-class kind path, proven by dry-run.

### Workspace users via automation account (auto-accepted at agent discretion)

- FLT-02: service-account-created users is code + role shape; the admin-role assignment and Ada's group→user move are owner console steps. Claude-seat invitation stays interactive (no member API) — engineering test stops before it.

### Spikes stay spikes (auto-accepted at agent discretion)

- FLT-03/05 (Slack icon via API, setup-token sign-in) and FLT-02 API creation are time-boxed probes producing recorded findings (works / doesn't / manual step), not rabbit holes.

### Agent's Discretion

All Phase 6 answers at agent discretion under the autonomous-run direction. Planner must keep vendor/secret-value steps as owner checklists.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `agents/host/agents.txt` (ada + codd rows with UIDs, harness, App IDs): source rows the registry absorbs.
- `agents/wake/wake.json` (project/zone/host/agents list): absorbed into registry; wake service reads registry next.
- `agents/host/provision.sh` + `apply.sh`: per-agent provisioning the add-flow drives.
- `infra/agents/` Terraform (variables, host, secrets): reads registry for `var.agents`-style inputs.
- `agents/host/files/bin/opencode-task` + `gh` wrapper: identity/tooling patterns new agents reuse.

### Established Patterns

- One command proves a domain; dated records; owner-go checklists never automated; secrets by shape/handles only.

### Integration Points

- Registry → Terraform/provisioning/controller/checks; add/remove → Secret Manager paths, host users, App manifests.

</code>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Standing direction: vendor approvals are owner gates; Codd pattern is a first-class onboarding path.

</specifics>

<deferred>
## Deferred Ideas

- Live vendor approvals (owner gates with trial onboardings).
- Ada's group→user move execution (owner console step).
- Further seat agents (FLEET-01, waits on Anthropic).

</deferred>

---

*Phase: 6-Fleet as code and onboarding*
*Context gathered: 2026-10-13*
