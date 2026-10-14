# Phase 6: Fleet as code and onboarding - Research

**Researched:** 2026-10-14
**Domain:** Fleet lifecycle automation (agent registry, onboarding/offboarding scripts, Workspace/Slack/GitHub vendor flows)
**Confidence:** HIGH (in-repo sources read this session); MEDIUM on vendor-API spike shapes (official docs cited, live behavior unprobed)

## Summary

Phase 6 turns the proven per-agent setup (Ada on a Claude seat, Codd on the OpenCode pattern) into one command. The in-repo investigation shows the phase is primarily a refactoring-plus-scripting phase, not a new-systems phase: every consumer of the future registry already exists and already parses the two legacy files, so the work is to insert `agents/fleet.yaml` as source of truth with a renderer, then wrap the documented manual runbooks (`runbooks/agents/slack.md`, `github.md`, `opencode.md`) in `agents/fleet add/remove` scripts that keep vendor approvals and secret values in owner hands.

The registry schema must cover three shapes already present in the repo: Ada (harness `claude`, Slack app, Workspace group-to-be-user, App on all repos), Codd (harness `opencode`, no Slack, no Workspace, App on two repos), and Boole (operations agent: Slack app, Workspace user, gateway key, App on one repo — declared-not-created in `infra/agents/boole.tf`). Vendor-API lookups confirm the three spike shapes are real probes with known constraints: Slack's `apps.icon.set` only works for apps created via `apps.manifest.create` by the calling manager app; Claude `setup-token` yields `CLAUDE_CODE_OAUTH_TOKEN` but interactive onboarding may still block headless start; a service account can hold the prebuilt User Management Admin role, but whether Directory `users.insert` works without domain-wide delegation (which the spec forbids) is the FLT-02 spike question.

**Primary recommendation:** Build `agents/fleet.yaml` + a stdlib-only renderer that emits `agents.txt`, `wake.json`, and Terraform inputs without changing any consumer; implement `fleet add/remove` as bash drivers over the existing `apply.sh` flows with dry-run owner checklists; time-box the three vendor spikes (Slack icon, setup-token, Workspace service-account creation) at ~2h each with recorded findings, not rabbit holes.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- `agents/fleet.yaml` is the single declaration (name, kind, runtime binding, identities, grants) and generates `agents.txt` and `wake.json` content — consumers (Terraform, provisioning, controller, checks) read the registry; the two legacy files become generated or are removed once nothing reads them directly.
- Current registry content: ada (claude/seat/Slack, UID 20001) + codd (opencode/terminal, UID 20002). Schema must cover both shapes plus operations agents (Boole).
- `agents/fleet add <name> --kind engineering|operations` creates identities and grants, loads secrets straight into Secret Manager paths (values by owner hands only — scripts take paths/handles, never values), provisions runtime, runs checks. `remove` revokes/deletes and prints remaining manual steps.
- Test onboarding/offboarding of each kind within 15 minutes and ~8 human actions is proven by dry-run where vendor steps are stubbed as explicit go-checklists; live vendor approvals are owner gates.
- Codd-pattern onboarding (GitHub App + Linux user + OpenCode + herdr control, CODD-02) is a first-class kind path, proven by dry-run.
- FLT-02: service-account-created users is code + role shape; the admin-role assignment and Ada's group→user move are owner console steps. Claude-seat invitation stays interactive (no member API) — engineering test stops before it.
- FLT-03/05 (Slack icon via API, setup-token sign-in) and FLT-02 API creation are time-boxed probes producing recorded findings (works / doesn't / manual step), not rabbit holes.

### Agent's Discretion

All Phase 6 answers at agent discretion under the autonomous-run direction. Planner must keep vendor/secret-value steps as owner checklists.

### Deferred Ideas (OUT OF SCOPE)

- Live vendor approvals (owner gates with trial onboardings).
- Ada's group→user move execution (owner console step).
- Further seat agents (FLEET-01, waits on Anthropic).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FLT-01 | `agents/fleet.yaml` declares every agent, replaces `agents.txt` + `wake.json`; Terraform, provisioning, controller, checks read it | Registry schema + renderer design; all consumers identified with exact read points |
| FLT-02 | Workspace users `<name>@agents.hyprn.ai` created/configured by a service account with user-management admin role; Ada group→user | Workspace automation shape; User Management Admin role verified; DWD question is the spike |
| FLT-03 | Slack app from reviewed manifest with generated icon; bot token straight to Secret Manager; Socket Mode token manual | Slack manifest precedent + `apps.icon.set` constraint verified; spike shape defined |
| FLT-04 | GitHub App via manifest flow; key straight to Secret Manager; IDs discovered by API | Runbook flow fully documented in-repo; `gh api` discovery commands verified |
| FLT-05 | Claude sign-in via `setup-token` in Secret Manager if channels work; else interactive stays + finding recorded | `setup-token`/`CLAUDE_CODE_OAUTH_TOKEN` verified in official docs; onboarding caveat known |
| FLT-06 | `fleet add` onboards a test agent of each kind in 15 min / ~8 actions; engineering stops before seat invite | Script design over existing apply flows; dry-run proof shape; no member API [ASSUMED] |
| FLT-07 | `fleet remove` offboards + prints remaining manual steps | Removal inventory (opencode.md contingency is the only precedent — extend it) |
| FLT-08 | `runbooks/agents/onboarding.md` describes add/remove + one-time prerequisites | Runbook structure; per-component runbooks to consolidate |
| CODD-02 | Codd pattern (App + Linux user + OpenCode, herdr-controlled) is the repeatable coding-agent setup, covered by fleet onboarding | Codd shape fully documented; `add_agent` opencode branch is the code to drive |

## Project Constraints (from AGENTS.md)

- Product code never enters this repository; platform infrastructure never enters a product repository.
- `hyprn-agents` is engineering tooling: no staging/prod access.
- Every step creating/changing/deleting cloud resources, IAM, org policy, billing, or GitHub/Slack/Claude org settings runs only after the platform owner's explicit go. Removals get their own go.
- Terraform: plan, review, apply exactly the reviewed plan.
- Never commit credentials, Terraform state/plan files, tfvars with secret values, service-account keys, session data. Secret values live in password manager (master) and Secret Manager (runtime). Never print a secret value; check by shape only.
- Run `gcloud`, Terraform, `gh` with HYPRN-dedicated configs (`CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`, `GH_CONFIG_DIR`).
- Repository content names roles, groups, agent identities — never people or personal accounts.
- Record what was done in the relevant runbook.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fleet registry + renderer | Repo / workstation | — | Static YAML + generator; no cloud component reads it directly |
| Host provisioning per agent | Agent host | — | `provision.sh add_agent` already owns Linux user, Docker, Git identity, harness |
| Wake service agent list | Controller VM | — | `wake.py` reads `/etc/hyprn-agents/wake.json`; only Slack-harness agents |
| Secret containers + grants | Terraform (`infra/agents/`) | — | Containers and IAM only; values never through Terraform |
| Secret values | Owner hands | Secret Manager | `pbpaste \| gcloud secrets versions add` pattern; scripts take handles |
| Workspace users | Google Workspace | — | Admin SDK via automation service account; admin-role grant is owner console |
| Slack/GitHub vendor objects | Vendor consoles | — | Manifest flows reduce but do not eliminate clicks; all are owner gates |
| Checks | Host + workstation | — | `tests/agents/run.sh` harness; fleet adds `checks/fleet.sh` |

## Standard Stack

### Core

No new libraries. The phase is bash + Python 3 stdlib + existing CLIs, matching every precedent in the repo.

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| bash (`set -euo pipefail`) | system | `agents/fleet` add/remove drivers, renderer glue | Every script in `agents/` and `tests/agents/` uses it [VERIFIED: agents/host/provision.sh:4, tests/agents/run.sh:7] |
| Python 3 stdlib (+ PyYAML via Debian `python3-yaml`) | 3.11 | Registry validator + renderer | Precedent: `agents/loops/validate.py` uses stdlib + `yaml` [VERIFIED: agents/loops/validate.py:9-13]; `wake.py` is stdlib + `python3-websocket` [VERIFIED: agents/wake/wake.py:20] |
| `gcloud` (with `CLOUDSDK_CONFIG`) | installed ✓ | Secret containers/versions, host/wake apply | Established apply path [VERIFIED: agents/host/apply.sh:5-14] |
| `gh` (with `GH_CONFIG_DIR`) | installed ✓ (repo wrapper) | GitHub App installation/bot ID discovery | Documented discovery commands [VERIFIED: runbooks/agents/github.md:12-14] |
| Terraform | owner workstation (absent here ✗) | Secret containers, IAM grants | `infra/agents/` owns all secret containers; plan-review-apply only |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| Google Admin SDK Directory API (`users.insert`) | FLT-02 service-account user creation | Only inside the FLT-02 spike; client library choice is the spike's decision [ASSUMED] |
| Slack Web API (`apps.manifest.create`, `apps.icon.set`, `apps.connections.open`) | FLT-03 automation probes | Spike only; manual manifest paste stays the fallback |
| `claude setup-token` | FLT-05 sign-in probe | Spike only; interactive `/login` stays the fallback |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Renderer emitting `agents.txt`/`wake.json` (committed) | Consumers parse `fleet.yaml` directly | Direct parsing touches 4+ consumers (provision.sh loop, host-checks.sh, wake provision, Terraform); renderer keeps the blast radius at one new script. Migrate consumers later. |
| bash `fleet` drivers | Python CLI (click/argparse) | Python is justified only for the validator/renderer; the add/remove flows are sequences of existing shell scripts — bash keeps them greppable and consistent |
| google-api-python-client for Workspace | `gam` / hand-rolled REST | New package needs legitimacy gate + install; hand-rolled REST reimplements auth. Spike decides; default to the official client library |

**Installation:** None. No new packages in the default plan. If the FLT-02 spike selects `google-api-python-client`, the planner must add a `checkpoint:human-verify` install task.

**Version verification:** No registry packages recommended. Toolchain versions are pinned in-repo: OpenCode 1.19.0, herdr 0.9.4, Claude Code 2.1.287 [VERIFIED: agents/host/provision.sh:8-14].

## Package Legitimacy Audit

No external packages are installed by this phase as planned. All automation uses the system toolchain (bash, Python 3.11 stdlib, Debian `python3-yaml`/`python3-websocket` precedents), `gcloud`, `gh`, and Terraform — each already established in the repo.

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| *(none)* | — | — | No installs; nothing to audit |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious (SUS):** none.
*If the FLT-02 spike selects a Workspace client library, that package must pass the Package Legitimacy Gate before the planner adds it — treat any such name as `[ASSUMED]` until then.*

## Architecture Patterns

### System Architecture Diagram

```text
agents/fleet.yaml  (single declaration — the only hand-edited file)
       │
       │  agents/fleet-render  (stdlib python; deterministic)
       ▼
 ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
 │ agents.txt  │  │  wake.json   │  │ tfvars (agents + │
 │ (generated) │  │ (generated,  │  │  slack_agents)   │
 └──────┬──────┘  │ Slack agents │  └────────┬─────────┘
        │         │  only)       │           │
        ▼         └──────┬───────┘           ▼
 agents/host/      agents/wake/       infra/agents/
 provision.sh      provision.sh       (var.agents,
 add_agent loop    wake.py Wakers      var.slack_agents)
        │                │                   │
        ▼                ▼                   ▼
   host checks      wake service      secret containers
 (host-checks.sh)  (Socket Mode)     + IAM grants

agents/fleet add <name> --kind ...        agents/fleet remove <name>
  1. validate name/conventions              1. confirm + owner go (removals
  2. append YAML entry (or take --dry-run)     get their own go)
  3. render + show diff                     2. delete cloud identities/grants
  4. terraform plan (owner reviews/applies) 3. delete host user, uninstall App
  5. owner checklist: vendor clicks +       4. remove YAML entry, re-render
     secret values (paths only in script)   5. PRINT remaining manual steps
  6. apply.sh flows + checks                6. run checks
```

### Recommended Project Structure

```text
agents/
├── fleet.yaml              # NEW: single declaration (hand-edited)
├── fleet                   # NEW: add/remove driver (bash)
├── fleet-render            # NEW: renderer fleet.yaml -> agents.txt, wake.json, tfvars (python stdlib)
├── fleet-validate          # NEW (or tests/agents/checks/fleet.sh): schema + sync check
├── host/agents.txt         # GENERATED (committed; regen must be clean)
├── wake/wake.json          # GENERATED (committed; regen must be clean)
└── loops/validate.py       # precedent for the validator pattern
runbooks/agents/onboarding.md  # NEW: FLT-08 (consolidates slack.md §1-2, github.md, opencode.md)
```

### Pattern 1: Registry with committed generated files + sync check

**What:** `fleet.yaml` is hand-edited; `agents.txt`, `wake.json`, and Terraform inputs are rendered and committed; a check fails if re-rendering produces a diff. This mirrors how `managed-settings.json` is the reviewed file and the console must diff clean against it.
**When to use:** For all three generated artifacts.
**Example (target schema sketch — field names are `[ASSUMED]`, values quoted from sources):**

```yaml
# agents/fleet.yaml (proposed; planner locks field names)
agents:
  - name: ada            # Linux user `ada` [VERIFIED: conventions/README.md:12]
    uid: 20001            # UIDs 20000-20999 are agent users [VERIFIED: agents/host/agents.txt:2]
    kind: engineering
    harness: claude       # harness: claude or opencode [VERIFIED: agents/host/agents.txt:3]
    display: "Ada (AI agent)"   # <Name> (AI agent) [VERIFIED: conventions/README.md:10]
    github: { app: ada-agent-hyprn, app_id: 5299141, installation_id: 170941397,
              bot_id: 341930344, repos: all }   # values [VERIFIED: agents/host/agents.txt:4]
    slack: true           # wake.json agents ["ada"] [VERIFIED: agents/wake/wake.json:5]
    workspace: user       # group until M3 move (spec §2)
  - name: codd
    uid: 20002
    kind: engineering
    harness: opencode
    display: "Codd (AI agent)"
    github: { app: codd-agent-hyprn, app_id: 5306008, installation_id: 171119571,
              bot_id: 342187193, repos: [hyprn-platform, hyprn-mvp] }  # [VERIFIED: agents/host/agents.txt:5]
    slack: false          # Codd: no Slack app [VERIFIED: runbooks/agents/opencode.md:15]
    workspace: none       # Codd signs in nowhere [VERIFIED: runbooks/agents/opencode.md:15]
```

Renderer mapping (all `[VERIFIED]` read points):
- `agents.txt` row ← `name uid harness github.app github.app_id github.installation_id github.bot_id display` (column order [VERIFIED: agents/host/agents.txt:1]).
- `wake.json` ← `{"project","zone","host"}` constants + `[name for agents if slack]` [VERIFIED: agents/wake/wake.json:1-6, agents/wake/wake.py:22,131].
- tfvars ← `agents=[names]`, `slack_agents=[names if slack]` feeding `var.agents` / `var.slack_agents` [VERIFIED: infra/agents/variables.tf:51-61].
- Secret inventory ← naming `<name>-agent-<purpose>` [VERIFIED: conventions/README.md:13, infra/agents/secrets.tf:6]: github-app-key for all; slack-app/bot-token + gateway-key only where applicable (Boole precedent adds `boole-agent-gateway-key` [VERIFIED: infra/agents/boole.tf:9-15]).

UID allocation: next free in 20000–20999 (20003 for first test agent — trivially derived, no registry lookup needed beyond the file).

### Pattern 2: Validator as static gate (loop-validator precedent)

**What:** A `validate`-style script asserts required keys, enum values (`kind`, `harness`), UID range/uniqueness, and cross-file sync; it runs in `checks/fleet.sh` before any consumer. Precedent: loop registry validator asserts required set + enum + non-empty allowlist [VERIFIED: agents/loops/validate.py:16-47].
**When to use:** Schema checks, enum checks, UID uniqueness, regen-clean check.

### Pattern 3: Owner-checklist dry-run proof (FLT-06/07)

**What:** `fleet add --dry-run` performs every automatable step (validate, render, diff, terraform plan, checklist print) and stubs vendor/secret steps as printed go-checklists with estimated action counts; the 15-minute / ~8-action claim is proven by timing the dry-run plus the documented owner actions, not by live vendor automation.
**When to use:** Both kind paths (engineering stops before seat invite; operations runs end-to-end dry).

### Anti-Patterns to Avoid

- **Parsing `fleet.yaml` in every consumer at once:** rewrites the provision loop, host checks, wake provision, and Terraform inputs simultaneously. Render committed files instead; migrate consumers one at a time.
- **Scripts accepting secret values:** any `--token <value>` flag puts values in shell history and process lists. Take paths/handles only; values travel `pbpaste | gcloud secrets versions add ... --data-file=-` in owner hands [VERIFIED: runbooks/agents/slack.md:16-19].
- **Automating the seat invite:** the Team plan has no member API (out-of-scope per REQUIREMENTS.md); the engineering flow must stop before it by design.
- **Deleting generated files before consumers migrate:** `agents.txt` is read by `provision.sh` [VERIFIED: agents/host/provision.sh:267] and `host-checks.sh` [VERIFIED: tests/agents/host-checks.sh:6,47]; `wake.json` is installed by wake provision [VERIFIED: agents/wake/provision.sh:15] and read at wake boot [VERIFIED: agents/wake/wake.py:22]. Remove only when nothing reads them (success criterion 1 means repo-level removal after migration, not mid-phase deletion).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML schema validation | Custom parser | Python `yaml.safe_load` + assert-set (loop precedent) | Injection-safe load, 60-line precedent, Debian package present |
| GitHub App creation | API automation from scratch | Manifest flow per runbook (owner confirms creation + install; IDs via `gh api`) | Webhook-off, perms Contents+PR read/write, installable-only-on-account steps are console clicks [VERIFIED: runbooks/agents/github.md:7-14] |
| Slack app creation | Raw `apps.create` | `apps.manifest.create` from reviewed `slack-app-manifest.yaml` + icon spike | Manifest pins scopes (`app_mentions:read`, `chat:write`, `im:history`, `im:write`, `reactions:write`, socket mode) [VERIFIED: agents/marketplace/plugins/slack/slack-app-manifest.yaml:14-31] |
| Claude sign-in automation | Credential-file fabrication | `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`, else interactive `/login` | Onboarding/theme-prompt edge cases are version-sensitive; probe, don't engineer around |
| Workspace user CRUD | Direct REST + hand-rolled OAuth | Official Admin SDK client (spike decides) + prebuilt User Management Admin role | Token handling, retries, and error shapes are the library's job |
| Acceptance proof | New harness | `tests/agents/run.sh` + new `checks/fleet.sh` | Guarded per-script runs, dated records, non-masking failures [VERIFIED: tests/agents/run.sh:20-62] |

**Key insight:** Phase 6's value is wiring, not invention. Every vendor flow already has a working manual procedure with dated records; the scripts' job is sequencing those procedures with owner gates, not reimplementing them.

## Common Pitfalls

### Pitfall 1: Renderer/consumer drift (generated files edited by hand)

**What goes wrong:** Someone edits `agents.txt` directly; the next render silently reverts it, or the sync check fails late.
**Why it happens:** Two sources of truth during migration.
**How to avoid:** Header-comment generated files (`# GENERATED from agents/fleet.yaml — do not edit`), and make `checks/fleet.sh` fail on any regen diff from day one.
**Warning signs:** Diffs to generated files without a matching `fleet.yaml` diff in the same PR.

### Pitfall 2: Secret values in script arguments or logs

**What goes wrong:** A `--bot-token` flag or `set -x` echo leaks a value into history, logs, or the dated check record.
**Why it happens:** Convenience flags; verbose tracing left on.
**How to avoid:** Scripts accept only secret *paths/handles*; verify by shape (`xapp-`, `xoxb-`) never by printing [VERIFIED: runbooks/agents/slack.md:58]; keep `set -u` without `-x` near handles.
**Warning signs:** Any `echo $TOKEN`, `--data-file=<value>`, or token-looking string in a record.

### Pitfall 3: UID / Linux-user collision

**What goes wrong:** A new agent reuses a UID or a stale home (`userdel` without `-r` leaves `/home/<name>`), breaking the private-home and subuid checks.
**Why it happens:** `add_agent` derives subuid ranges from UID (`100000 + (uid-20000)*65536`) [VERIFIED: agents/host/provision.sh:176] — a duplicate UID duplicates the subuid range.
**How to avoid:** Validator asserts UID uniqueness + range; `remove` deletes the user with `-r` (contingency precedent [VERIFIED: runbooks/agents/opencode.md:56]) and re-renders before checks run.
**Warning signs:** `host-checks.sh` home/subuid failures after an add.

### Pitfall 4: Wake list including a Slack-less agent

**What goes wrong:** `wake.py` builds a `Waker` per listed agent and reads `<agent>-agent-slack-app-token` at boot [VERIFIED: agents/wake/wake.py:79,131] — a Codd-pattern agent in `wake.json` crashes or log-spams the wake service.
**Why it happens:** Blindly rendering all agent names into `wake.json`.
**How to avoid:** Renderer filters on `slack: true`; validator asserts every wake-listed agent has Slack secrets declared; matches `var.slack_agents` semantics [VERIFIED: infra/agents/variables.tf:57-61].
**Warning signs:** Wake journal `connection refused` / secret-access errors naming a Slack-less agent.

### Pitfall 5: Terraform state churn on agent lists

**What goes wrong:** Reordering `var.agents` or renaming entries recreates secrets (`for_each` on name sets), orphaning live secret versions.
**Why it happens:** `for_each = toset(var.agents)` keys resources by name [VERIFIED: infra/agents/secrets.tf:46-48].
**How to avoid:** Renderer emits lists in stable sorted order; `remove` plan is reviewed for `destroy` scope (secret containers only after values are confirmed migrated/disabled, following the `agent-ada-*` deletion precedent [VERIFIED: runbooks/agents/slack.md:66]); removals get their own owner go.
**Warning signs:** A plan showing forces-replacement on secrets the phase did not intend to touch.

### Pitfall 6: Spike creep (FLT-02/03/05 become projects)

**What goes wrong:** The icon/setup-token/Workspace probes expand into retry loops, fallbacks, and version-specific workarounds.
**Why it happens:** Vendor APIs are close-to-working but edge-cased.
**How to avoid:** Time-box each at ~2h with a fixed finding template (works / doesn't / manual step + evidence); a "doesn't" is a complete result that locks the manual step into the runbook.
**Warning signs:** A spike branch older than a day without a recorded finding.

## Code Examples

### Rendering `agents.txt` rows (column order is load-bearing)

```bash
# Source: agents/host/agents.txt:1 (header), agents/host/provision.sh:267 (reader)
# name uid harness app_slug app_id installation_id bot_id display...
printf '%s %s %s %s %s %s %s %s\n' \
  "$name" "$uid" "$harness" "$app_slug" "$app_id" "$installation_id" "$bot_id" "$display"
# Reader skips comments/blank lines: grep -vE '^\s*(#|$)' [VERIFIED: agents/host/provision.sh:267]
```

### Renderer wake.json filter (Slack agents only)

```python
# Sources: agents/wake/wake.json:1-6 ; agents/wake/wake.py:22,79,131
doc = {"project": "hyprn-agents", "zone": "europe-west1-b",
       "host": "hyprn-agents-host-01",
       "agents": [a["name"] for a in agents if a.get("slack")]}
```

### Secret-container naming (Terraform must match)

```bash
# Convention: <name>-agent-<purpose> [VERIFIED: conventions/README.md:13]
# Containers only — values loaded by owner hands, never Terraform [VERIFIED: infra/agents/secrets.tf:1-4]
gcloud secrets versions add <name>-agent-github-app-key --project=hyprn-agents --data-file=<key.pem>
# then: rm the .pem; run agents/host/apply.sh [VERIFIED: runbooks/agents/github.md:19-24]
```

### GitHub App ID discovery (FLT-04, by API)

```bash
# Source: runbooks/agents/github.md:12-14
GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api orgs/hyprn-labs/installations \
  --jq '.installations[] | "\(.app_slug) app=\(.app_id) installation=\(.id)"'
GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api 'users/<app>%5Bbot%5D' --jq .id
```

### Codd-pattern host provisioning (what `fleet add --kind engineering` with harness `opencode` must drive)

```bash
# provision.sh add_agent branches on harness; opencode path installs the role
# file and returns before any Claude/Slack/session setup [VERIFIED: agents/host/provision.sh:221-226].
# herdr control + opencode-task launcher are the session layer [VERIFIED: runbooks/agents/opencode.md:30-36].
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Machine account (`ada-agent-hyprn` user + fine-grained token) | Per-agent GitHub App + one-hour broker tokens (ADR-0005) | 2026-10-13 [VERIFIED: runbooks/agents/github.md:42-43] | `fleet add` must create Apps, never accounts |
| `agent-ada-*` secret names | `<name>-agent-<purpose>` names | 2026-10-13 [VERIFIED: runbooks/agents/slack.md:65-66] | Renderer/validator must enforce the new pattern |
| tmux session (`hyprn-agent@.service`) | herdr (`herdr@.service`); tmux stays as disabled fallback | M1 direction [VERIFIED: agents/host/provision.sh:251-259] | Codd-pattern path includes herdr control (CODD-02) |
| Slack icon manual-only [ASSUMED] | `apps.icon.set` API (manager-app constraint) | Endpoint now documented [CITED: https://docs.slack.dev/reference/methods/apps.icon.set] | FLT-03 spike: create-via-manifest-API then set icon; manual upload is the fallback |
| Browser `/login` only [ASSUMED] | `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` | Documented for CI/scripts [CITED: https://code.claude.com/docs/en/env-vars.md] | FLT-05 spike: verify channels work under token auth; onboarding prompt is the known risk |

**Deprecated/outdated:**
- Machine-account onboarding steps (token with Write, rename runbooks): superseded by the App flow; do not copy into `fleet add`.
- `agent-ada-*` secret names: deleted [VERIFIED: runbooks/agents/slack.md:66]; validator must reject them.

## Investigation Details

### (1) fleet.yaml schema coverage

Three in-repo shapes bound the schema (see Pattern 1 example). Required per-agent fields: `name` (Linux user [VERIFIED: conventions/README.md:12]), `uid` (20000–20999 [VERIFIED: agents/host/agents.txt:2]), `kind` (`engineering|operations` — CLI contract from CONTEXT), `harness` (`claude|opencode` [VERIFIED: agents/host/agents.txt:3]), `display` (`<Name> (AI agent)` [VERIFIED: conventions/README.md:10]), `github` (slug per `<name>-agent-hyprn` [VERIFIED: conventions/README.md:11], app/installation/bot IDs, repo scope: all / list), `slack` (bool; drives wake list + `var.slack_agents` + token secrets), `workspace` (`user|none`; `group` only as Ada's transient pre-move state), `gateway` (bool; operations agents need a virtual key [VERIFIED: infra/agents/boole.tf:9-15]). Codd pattern = `{kind: engineering, harness: opencode, slack: false, workspace: none}` — no third kind value needed; the CLI keeps `--kind engineering|operations` and the harness selects the Codd path. Boole adds `{kind: operations, slack: true, workspace: user, gateway: true}`.

### (2) Generation of agents.txt / wake.json content

Column order and readers are quoted in Code Examples. Additional consumer: `agents/host/README.md` documents the `agents.txt` columns [VERIFIED: agents/host/README.md:7]. Terraform inputs `var.agents` (default `["ada", "codd"]`) and `var.slack_agents` (default `["ada"]`) [VERIFIED: infra/agents/variables.tf:51-61] become renderer outputs. Recommendation: renderer writes `agents.txt`, `wake.json`, and `infra/agents/fleet.auto.tfvars.json`; `variables.tf` keeps its shape (no consumer change); generated files are committed with `GENERATED` headers; `checks/fleet.sh` asserts regen-clean.

### (3) fleet add/remove script design

`add`: validate (name regex lowercase/digits/dashes per `opencode-task` precedent [VERIFIED: agents/host/files/bin/opencode-task:8]; UID next-free; conventions) → append YAML → render → show diff → emit Terraform delta (secret containers + grants, mirroring `secrets.tf`/`boole.tf` blocks) for owner plan-review-apply → print vendor checklist (Slack: config token, approve install, Socket Mode token [VERIFIED: docs/specs/agent-fleet.md:158-166]; GitHub: confirm creation, install [VERIFIED: runbooks/agents/github.md:7]; Workspace: 2FA enrol, OAuth consent [VERIFIED: docs/specs/agent-fleet.md:158-166]) → drive `apply.sh` flows (host + wake) → run `tests/agents/run.sh`. Secrets: scripts create empty containers / reference paths only; values loaded by owner via the `pbpaste` pattern [VERIFIED: runbooks/agents/slack.md:14-19]. `remove`: owner go (removals get their own go per AGENTS.md) → revoke/delete cloud identities and grants → `userdel -r` + App uninstall + secret disable (extend the opencode.md contingency [VERIFIED: runbooks/agents/opencode.md:56], which currently covers only the Codd shape) → remove YAML entry → re-render → print remaining manual steps (App deletion confirm, secret-version cleanup, Workspace user delete/suspend, group→user notes) → run checks.

### (4) Workspace user automation shape + admin-role needs

Shape: automation service account → Admin SDK Directory `users.insert` (`<name>@agents.hyprn.ai`, password/second-factor in password manager per spec §2) → configure settings. Admin-role need: prebuilt **User Management Admin** can create/delete users via console and Admin API [CITED: https://support.google.com/a/answer/2405986?hl=en]; any prebuilt/custom role except Super Admin can be assigned to a service account via Admin → Account → Admin roles (super-admin action) [CITED: https://knowledge.workspace.google.com/admin/users/assign-specific-admin-roles]. Open spike question: whether Directory `users.insert` succeeds with a directly role-assigned service account or requires domain-wide delegation + impersonation (community reports require `create_delegated`/`with_subject` [ASSUMED]); the spec forbids DWD (spec §12: "no domain-wide delegation"), so the spike must test the DWD-free path and, on failure, lock the console/API-delegated fallback. Admin-role assignment itself and Ada's group→user move stay owner console steps per CONTEXT.

### (5) FLT-03/05 spike shapes (time-boxed probes)

- **FLT-03 Slack icon:** `apps.icon.set` sets the app icon from file bytes or public URL [CITED: https://docs.slack.dev/reference/methods/apps.icon.set], scope `app_configurations:write`, with the hard constraint that a manager app may set icons only for apps it created via `apps.manifest.create` [CITED: https://docs.slack.dev/reference/methods/apps.icon.set]. Spike: create test app via manifest API → set icon via API → record. Fallback (already working): paste manifest in app settings + manual icon upload [VERIFIED: runbooks/agents/slack.md:7]. Socket Mode token creation stays manual regardless (spec §12). The reviewed manifest (scopes, socket mode, events) is the input artifact [VERIFIED: agents/marketplace/plugins/slack/slack-app-manifest.yaml:14-31].
- **FLT-05 setup-token:** `claude setup-token` prints a long-lived token without saving it; `CLAUDE_CODE_OAUTH_TOKEN` takes precedence over keychain credentials [CITED: https://code.claude.com/docs/en/env-vars.md]. Spike: load token into Secret Manager by shape, start session on test agent, verify the channel server connects and answers. Known risk: interactive onboarding (theme/auth picker) can still block headless start; community workaround is `hasCompletedOnboarding: true` in `~/.claude.json` [ASSUMED — issue reports, not official docs]. Finding "doesn't work with channels" locks interactive `/login` (B4 precedent [VERIFIED: runbooks/agents/host.md:29]) as the standing step.
- **Effort cap:** ~2h each; finding template: works / doesn't / manual step + evidence lines for the runbook.

### (6) Onboarding runbook structure (FLT-08)

`runbooks/agents/onboarding.md`: (a) one-time prerequisites (Workspace admin-role grant, Terraform apply rights, password-manager access, vendor console access, tool configs); (b) `fleet add` flow per kind with owner-checklist callouts and the seat-invite stop; (c) `fleet remove` flow + manual-remainder table; (d) per-vendor appendix consolidating (not duplicating) `slack.md` §1–2, `github.md` create/rotate, `opencode.md` Codd path, `host.md` provision; (e) Record table (dated rows, matching existing runbook style). Must state the out-of-scope items (seat automation, money/signing) per REQUIREMENTS.md.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Team plan has no member API (seat invite unstoppable-automation) | Standard Stack / add design | Low — locked by CONTEXT + out-of-scope table; if an API exists the engineering flow could automate one more step |
| A2 | Proposed `fleet.yaml` field names (`kind`, `harness`, `workspace`, `gateway`) | Architecture Patterns | Low — planner locks names; renderer/validator are new code either way |
| A3 | `apps.icon.set` general availability and `app_configurations:write` scope stability | Spikes | Low — spike has a working manual fallback; finding may be "manual step" |
| A4 | `hasCompletedOnboarding` workaround for token-auth start | Spikes | Low — community-sourced; spike verifies or locks interactive login |
| A5 | Directory API works DWD-free with role-assigned service account | Workspace shape | Medium — spec forbids DWD; spike must resolve; fallback is owner-executed creation |
| A6 | Workspace client library choice (official client vs alternatives) | Standard Stack | Low — spike decides; gated install task contains the risk |
| A7 | 15-minute / ~8-action budget composes from dry-run + documented owner steps | add/remove design | Medium — proven by dry-run per CONTEXT, not live; live trial is deferred scope |

## Open Questions

1. **DWD-free Directory writes?**
   - What we know: Role can be assigned to a service account (official docs); community flows use delegation+impersonation.
   - What's unclear: Whether `users.insert` succeeds with only the role grant.
   - Recommendation: FLT-02 spike tests it first; on failure, lock the owner-console/API-delegated fallback in the runbook.

2. **Does the token-authed Claude session join channels?**
   - What we know: Token auth works for CLI/SDK; onboarding prompts are the reported blocker.
   - What's unclear: Channel-server behavior under `CLAUDE_CODE_OAUTH_TOKEN`.
   - Recommendation: FLT-05 spike on a test agent; either result is a complete finding.

3. **Should generated files be committed or rendered at apply time?**
   - What we know: Both satisfy "registry is source of truth"; committed files give reviewable diffs.
   - What's unclear: Owner preference for repo noise vs apply-time derivation.
   - Recommendation: Commit + sync check (reviewability matches the policy-file precedent); revisit if noisy.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 + PyYAML | Validator/renderer | ✓ | 3.11.2, yaml OK | — |
| bash, jq | Scripts, checks | ✓ | system | — |
| gcloud | Secrets, apply | ✓ | installed | — |
| gh (repo wrapper) | App ID discovery | ✓ | wrapper present | Real `gh` with `GH_CONFIG_DIR` on owner workstation |
| Terraform | Secret containers/grants | ✗ (this machine) | — | Owner workstation applies; plan reviewed before apply |
| `tests/agents/checks/` harness | Fleet checks | ✓ | 17 check scripts present | — |
| Live vendor consoles | Spikes/trials | ✗ (owner-gated) | — | Dry-run with go-checklists (locked by CONTEXT) |

**Missing dependencies with no fallback:** none for planning/dry-run scope.
**Missing dependencies with fallback:** Terraform binary (owner workstation); live vendor access (dry-run stubs).

Step 2.6 environment probes were run on this machine (`command -v`, `python3 -c "import yaml"`); Terraform absence is expected — applies happen on the owner's workstation per AGENTS.md authority rules.

## Validation Architecture

Test framework: bash checks harness (no unit-test framework in repo).

| Property | Value |
|----------|-------|
| Framework | `tests/agents/run.sh` + `tests/agents/checks/*.sh` (bash, guarded per-script, dated record) |
| Config file | none — convention: executable `checks/<name>.sh`, runs after `host-checks.sh` |
| Quick run command | `tests/agents/run.sh` (full harness; per-script: `bash tests/agents/checks/fleet.sh`) |
| Full suite command | `tests/agents/run.sh` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLT-01 | Registry validates; regen of agents.txt/wake.json/tfvars is clean | static check | `bash tests/agents/checks/fleet.sh` | ❌ Wave 0 |
| FLT-01 | Consumers read generated files identically (provision loop, host checks, wake) | static check | `grep` read-points in `fleet.sh` | ❌ Wave 0 |
| FLT-02 | Workspace automation shape + role declared; spike finding recorded | spike record | manual (owner-gated) | ❌ Wave 0 (finding file) |
| FLT-03 | Manifest→icon spike finding recorded | spike record | manual (owner-gated) | ❌ Wave 0 (finding file) |
| FLT-04 | App IDs discoverable by API; key-to-Secret-Manager path takes handles only | static + checklist | `fleet.sh` asserts no `--*token` value flags | ❌ Wave 0 |
| FLT-05 | setup-token spike finding recorded | spike record | manual (owner-gated) | ❌ Wave 0 (finding file) |
| FLT-06 | `fleet add --dry-run` per kind completes; checklist ≤ ~8 actions | dry-run | `agents/fleet add test-<kind> --dry-run` (timed) | ❌ Wave 0 |
| FLT-07 | `fleet remove --dry-run` prints manual remainder | dry-run | `agents/fleet remove test-<kind> --dry-run` | ❌ Wave 0 |
| FLT-08 | Onboarding runbook exists, covers flows + prerequisites | doc check | `test -f runbooks/agents/onboarding.md` in `fleet.sh` | ❌ Wave 0 |
| CODD-02 | Codd-pattern dry-run covers App + user + OpenCode + herdr | dry-run | engineering-kind dry-run with harness=opencode | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `bash tests/agents/checks/fleet.sh` (static: validate + regen-clean + no-value-flags).
- **Per wave merge:** `agents/fleet add test-eng --dry-run` and `--kind operations` variant (timed, checklist counted).
- **Phase gate:** Full `tests/agents/run.sh` green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `agents/fleet-validate` (or `fleet-render --check`) — schema + UID + wake-filter + secret-name assertions.
- [ ] `tests/agents/checks/fleet.sh` — validate, regen-clean, no-secret-value-flags, runbook-exists.
- [ ] `agents/fleet-render` — YAML→agents.txt/wake.json/tfvars.json emitter.
- [ ] Spike finding records (workspace-slack-token) — short dated notes, not code.
- [ ] Framework install: none (bash + stdlib python + Debian python3-yaml already present).

## Security Domain

`security_enforcement` is enabled; ASVS L1 applies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Per-agent GitHub Apps (one-hour tokens), Workspace users, no shared accounts; broker patterns unchanged |
| V3 Session Management | partial | Claude seat sign-in stays interactive unless FLT-05 proves token path; OAuth tokens in Secret Manager only |
| V4 Access Control | yes | `fleet remove` must revoke grants + delete users; validator asserts wake/Slack filtering so Slack-less agents get no tokens |
| V5 Input Validation | yes | Registry validator (required keys, enums, UID range/uniqueness); agent names restricted to `[a-z0-9-]` |
| V6 Cryptography | yes | App private keys via Secret Manager paths only; scripts never accept/print values; Terraform owns containers, never values |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret value in shell history / logs / records | Information disclosure | Handles-only CLI; shape-only verification; no `set -x` near handles |
| Stale identity after offboarding (user, App install, secret version) | Elevation / repudiation | `remove` checklist + manual-remainder printer; removals get their own owner go |
| UID/home reuse across add/remove cycles | Tampering / spoofing | Uniqueness validation; `userdel -r`; re-render before checks |
| Wake service reading Slack-less agent's secrets | Information disclosure | Renderer `slack: true` filter + validator assertion |
| Terraform `for_each` secret recreation on reorder | Denial / disclosure | Stable sorted output; reviewed plans; destroy-scope check on remove |

## Sources

### Primary (HIGH confidence — read this session)

- `agents/host/agents.txt` — registry rows absorbed (columns, UIDs, harnesses, App IDs)
- `agents/wake/wake.json` + `agents/wake/wake.py` — wake config shape, per-agent secret reads, Waker construction
- `agents/host/provision.sh` (`add_agent`, opencode branch, subuid derivation, agents.txt loop) + `agents/host/apply.sh`
- `agents/wake/provision.sh` — wake.json install path
- `infra/agents/variables.tf`, `secrets.tf`, `boole.tf`, `host.tf` — Terraform inputs, secret containers, reader grants
- `conventions/README.md` — naming patterns for users, Apps, secrets, branches
- `runbooks/agents/slack.md`, `github.md`, `opencode.md`, `host.md`, `claude.md` — vendor procedures with dated records
- `agents/marketplace/plugins/slack/slack-app-manifest.yaml` — reviewed manifest (scopes, socket mode, events)
- `agents/host/files/opencode.json`, `agents/host/files/bin/opencode`, `opencode-task` — Codd-pattern constraints and launcher
- `agents/loops/validate.py` — validator precedent; `tests/agents/run.sh`, `host-checks.sh` — check harness
- `docs/specs/agent-fleet.md` §2, §12 — identity table, vendor automation matrix, human-action counts
- `.planning/REQUIREMENTS.md` (FLT-01..08, CODD-02), `.planning/ROADMAP.md` (Phase 6), `06-CONTEXT.md` (locked decisions)

### Secondary (MEDIUM confidence — official docs via web)

- [CITED: https://docs.slack.dev/reference/methods/apps.icon.set] — `apps.icon.set` (file/URL, `app_configurations:write`, manager-app-only constraint)
- [CITED: https://code.claude.com/docs/en/env-vars.md] — `CLAUDE_CODE_OAUTH_TOKEN` / `claude setup-token` semantics
- [CITED: https://support.google.com/a/answer/2405986?hl=en] — User Management Admin capabilities
- [CITED: https://knowledge.workspace.google.com/admin/users/assign-specific-admin-roles] — role assignment to service accounts

### Tertiary (LOW confidence — community reports, need spike confirmation)

- `hasCompletedOnboarding` workaround for token-authed headless start [ASSUMED]
- Directory API delegation/impersonation requirement vs direct role grant [ASSUMED]
- `apps.icon.set` availability/scope stability [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; every tool verified present or precedented in-repo.
- Architecture: HIGH — all consumers and read points verified by Read this session with line citations.
- Pitfalls: HIGH — derived from dated in-repo incident records (wrong secret values, token reload loss, metadata DNS block).
- Vendor spikes: MEDIUM — official docs cited; live behavior explicitly deferred to time-boxed probes.

**Research date:** 2026-10-14
**Valid until:** 2026-11-13 (stable domain; vendor API details re-check at spike time)
