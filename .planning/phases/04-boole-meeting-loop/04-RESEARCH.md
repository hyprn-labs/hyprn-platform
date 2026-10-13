# Phase 4: Boole and the meeting loop - Research

**Researched:** 2026-10-13
**Domain:** Operations loop — Notion-poll trigger, decision/action extraction, A1 approved Notion writes, Slack summary, per-run cost, Ada↔Boole isolation
**Confidence:** MEDIUM

## User Constraints (from CONTEXT.md)

### Locked Decisions
- LOOP-01 unsettled: plans target the settled seam — controller polls the Notion meetings database every 5 minutes, one run per new meeting page — and treat the Granola→Notion leg as a documented assumption with a file-drop/manual-page fallback for testing.
- No Granola credentials, scrapers, or unofficial APIs in plans. Settling LOOP-01 is an owner decision recorded before live runs, not an implementation task.
- Meeting loop at A1: extracts decisions/actions, proposes Notion updates, posts Slack summary; Notion writes need owner approval via Boole's Slack bot (approval-park pattern from Phase 3). Test with fakes (fake Notion pages, fake Slack answers).
- 10-meetings-in-two-weeks within $30/month is the live trial shape — plans deliver the metered path (cost per run visible via gateway budget path), the trial itself is an owner-go checkpoint.
- ACC-07: Ada and Boole cannot reach each other's homes, secrets, containers, tokens or bots — extend Phase 1's per-agent checks to Boole's declared identities (Linux user, secret names, container user, bot tokens) as static assertions + live checks gated on identities existing.
- Boole's GitHub App is Phase 5 (OPS-03) — not here.
- OPS-02 (Workspace user + Notion integration, tokens in Secret Manager) ships as declarations + manifests + owner checklists. Nothing created vendor-side in execution.

### Agent's Discretion
All Phase 4 answers at agent discretion under the autonomous-run direction. Planner must not select a Granola integration.

### Deferred Ideas (OUT OF SCOPE)
- Granola→Notion integration choice (owner decision, LOOP-01).
- Boole's GitHub App (Phase 5, OPS-03).
- Learning/evals (Phase 5); second loops.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPS-02 | Workspace user `boole@agents.hyprn.ai` + Notion integration limited to meetings DB, token in Secret Manager (declared, not created) | Notion integration shape + secret-container pattern + owner checklist |
| LOOP-01 | Granola→Notion leg unsettled; controller polls Notion meetings DB every 5 min, one run per new page | Trigger-seam design + poller pattern + file-drop fallback |
| LOOP-02 | Extract decisions/actions, propose Notion updates, Slack summary; Notion writes at A1 via Boole's Slack bot approval | Extraction flow + `park`/`resume` reuse + Notion PATCH shape |
| LOOP-03 | ≥10 real meetings / 2 weeks within $30/mo, cost per run visible | `record_cost` + gateway ledger path without live gateway |
| ACC-07 | Ada/Boole/Codd cannot reach each other's homes, secrets, containers, tokens, bots | host-checks cross-home loop + per-agent secret assertions, extended to Boole |

## Project Constraints (from AGENTS.md)

- Product code never enters this repository; platform infrastructure never enters a product repository.
- `hyprn-agents` is engineering tooling: no product workload, no staging/prod access.
- Every cloud/IAM/billing/GitHub/Slack/Claude-org step runs only after the platform owner's explicit go for that exact step. Removals get their own go.
- Terraform: plan, review, apply exactly the reviewed plan.
- Never commit credentials, Terraform state/plan files, tfvars with secret values, service-account keys, or session data. Secrets live in password manager (master) + Secret Manager (runtime).
- Never print a secret value; check tokens by shape only.
- Run `gcloud`/`terraform`/`gh` with HYPRN-dedicated configs.
- Repository content names roles/groups/agent identities, never people.
- Record what was done in the relevant runbook; dated records in `runbooks/agents/`.

## Summary

Phase 4 adds exactly one registered loop — the meeting loop — on top of the Phase 3 control plane, plus Boole's remaining declared identities and the isolation proof. No new infrastructure: the dispatcher (`enqueue`/`dispatch`/`park`/`resume`/`record_cost`), the loop validator, the credential broker, the rootless runner, the gateway budget path, and the Slack Socket-Mode bot all already exist as code patterns; Phase 4 wires a second YAML entry, a Notion poller, a pinned workflow script, and checks.

The unsettled Granola leg must not leak into implementation. The only settled trigger is: controller polls the Notion meetings database every 5 minutes, one envelope per new page id, idempotent on page id. The Granola→Notion path is a documented assumption plus a file-drop/manual-page fixture for tests — no credentials, no scrapers, no unofficial APIs anywhere in plans.

**Primary recommendation:** Ship `agents/loops/meeting.yaml` as the reference A1 loop (poll trigger, `notion-write: A1`), a stdlib-only Notion poller + workflow script reusing `park`/`resume` and `record_cost`, Boole Notion/Workspace declarations + owner checklist, and `checks/meeting.sh` + `checks/isolation.sh` in the one-command run — all green on fakes with live trial behind an owner-go checkpoint.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Notion poll trigger (5-min) | Controller VM | — | Always-on scheduler; owns queue + idempotency |
| Decision/action extraction | Run container (Boole user) | Gateway (model) | Judgment step runs on open model via gateway binding |
| Notion update proposal + approved write | Run container → controller park | Notion API | A1: propose, park, write only after owner `yes` |
| Slack summary + approval Q&A | Controller (Boole Socket Mode) | Run state DB | Parked runs hold DB rows, not compute |
| Per-run cost visibility | Dispatcher ledger + gateway logs | — | `cost_usd` per run readable without live gateway |
| Ada↔Boole isolation | Host (users/homes/secrets) | Checks | Same per-agent primitives as Phase 1, extended |
| Boole Workspace user + Notion integration | Vendor consoles (owner) | Terraform/secrets (declarations) | Vendors have no API for these; declare + checklist |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3 stdlib (`urllib`, `json`, `sqlite3`, `unittest`) | 3.11.2 [VERIFIED: `python3 --version` → 3.11.2 this session] | Poller, workflow script, Notion REST calls, unit tests | Matches `controller/dispatcher.py` ("Dependencies: Python 3 standard library only (sqlite3)" [VERIFIED: controller/dispatcher.py:17]) and `server.py` stdlib+websocket shape; zero new deps |
| PyYAML | already in tree for `validate.py` [VERIFIED: agents/loops/validate.py:13 `import yaml`] | Parse loop YAML in poller/broker | Spec-mandated file format; no alternative |
| Phase 3 control plane (dispatcher, broker, runner, gateway) | as built | Queue, approvals, budgets, credentials, containers | Reuse, not rebuild — CONTEXT binding |
| Notion REST API (`https://api.notion.com`) | `Notion-Version: 2026-03-11` header [CITED: developers.notion.com/guides/get-started/quick-start] | Query meetings DB, read pages/blocks, PATCH properties | Only official integration path; Bearer token auth |
| Boole Slack bot (server.py shape) | existing | Summary post + approval Q&A | Approval-park pattern already proven |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `curl` + `jq` in shell seams | host-present [ASSUMED] | Broker fetches, smoke probes | Same as broker's existing `curl`/`jq` use |
| Rootless Docker | 29.9.0 [VERIFIED: `docker --version` this session] | Run containers | Already on host; runner shape fixed |
| Bash `tests/agents/checks/*.sh` harness | n/a | `meeting.sh` + `isolation.sh` join `run.sh` | ACC-08 continuity |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `urllib` Notion calls | `notion-client` (npm) / `notion-database` (pip) SDKs | SDKs add deps + version churn for 3 endpoints; stdlib covers query/get/update with full header control — use stdlib |
| Polling (5-min) | Webhook receiver | Needs public endpoint + own ADR (WEB-01 deferred); polling is spec-settled — use polling |
| Any Granola integration | Official export, Zapier/Make, manual copy | LOOP-01 unsettled by owner decision; planner must not select — document assumption + fixture only |

**Installation:**
```bash
# No new packages. PyYAML already required by Phase 3 validator.
pip index versions pyyaml   # planner pins at plan time if touching it
```

**Version verification:** `python3 --version` → 3.11.2, `docker --version` → 29.9.0, `import yaml` OK [VERIFIED: probed this session]; `terraform` absent, `boole` user absent [VERIFIED: probed this session] — both expected pre-apply/pre-provisioning, plans must gate live checks on their existence.

## Package Legitimacy Audit

No new external packages installed by this phase. Workflow, poller, and checks are stdlib Python + Bash; Notion is reached over HTTPS with `urllib`, not an SDK.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | No installs; audit trivially clean |
| `pyyaml` (carry-over, Phase 3) | PyPI | ~18 yrs [ASSUMED] | ~100M/mo [ASSUMED] | github.com/yaml/pyyaml [ASSUMED] | OK (already in tree) | Approved, pin at plan time |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious (SUS):** none

## Architecture Patterns

### System Architecture Diagram

```text
Granola (people's app, NO agent access)
   │  (UNSETTLED leg — owner decision; assumption only)
   ▼
Notion meetings database (shared with Boole integration)
   │  poll every 5 min (controller; settled seam)
   ▼
poller: list new page ids since cursor ─► envelope {loop: meeting,
        idempotency_key: notion-page-<id>} ─► Dispatcher.enqueue
   │  (duplicate page id → same run id, enqueue-once)
   ▼
Dispatcher.dispatch (registry + budget + kill gates) ─► run runner
   │  (broker issues ONLY loop-declared secrets to per-run dir)
   ▼
workflow (container, boole user, allowlist: gateway + api.notion.com + slack.com):
  fetch page + blocks → extract {decisions, actions, owners, dates}
  → draft Notion property patch (NOT applied) → post Slack summary
  → park(run, "apply Notion patch?")  [A1 gate]
   │  owner `yes <id>` → resume → apply PATCH → record_cost
   │  owner `no <id>` / stranger → stay parked / ignore
   ▼
run log + cost_usd per run; feedback stored for Phase 5 evals
```

File-to-implementation mapping belongs in plans, not the diagram.

### Recommended Project Structure

```text
agents/loops/
├── meeting.yaml              # reference A1 loop (the registry entry)
├── meeting/
│   ├── prompts.md            # extraction rubric (judgment step)
│   └── skills/               # Notion-shape + Slack-shape notes
├── validate.py               # unchanged (Phase 3)
└── testdata/
    ├── test-loop.yaml        # unchanged fixture
    └── meeting-pages/        # 3 fake Notion pages (new, updated, malformed)
controller/
├── dispatcher.py             # unchanged; poller calls enqueue/record_cost
├── poll_notion.py            # NEW: 5-min poller (stdlib, fake-seam)
└── test_poll_notion.py       # NEW: cursor + idempotency + dedupe tests
agents/host/files/
├── hyprn-meeting-workflow    # NEW: pinned fetch→extract→propose→park script
├── hyprn-credential-broker   # extended tool map (notion-read/slack-post already shape-covered)
└── hyprn-run-runner          # unchanged
infra/agents/
└── boole-notion.tf           # NEW (declared-not-created): Notion + Workspace declarations
tests/agents/checks/
├── meeting.sh                # NEW: loop + trigger + A1 + cost + fallback checks
└── isolation.sh              # NEW: ACC-07 Ada/Boole(/Codd) assertions
runbooks/agents/
└── meeting-loop-go.md        # NEW: owner checklist (LOOP-01 settle, Workspace user, integration share, trial)
```

### Pattern 1: Meeting loop as reference registry entry
**What:** `agents/loops/meeting.yaml` carries the full REQUIRED set the validator enforces [VERIFIED: agents/loops/validate.py:16-18] —
```yaml
"name", "owner", "trigger", "steps", "tools", "autonomy",
"budget", "egress_allowlist", "runtime", "eval_set", "promotion_rule"
```
— with the test-loop's proven shape as template [VERIFIED: agents/loops/testdata/test-loop.yaml:1-33]:
```yaml
name: meeting-test
owner: platform-owner
trigger:
  type: poll
  source: notion-meetings
  interval: 5m
steps:
  - fetch-page
  - extract
  - propose
agent_steps:
  - extract
tools:
  - notion-read
  - slack-post
autonomy:
  notion-write: A1
  slack-post: A2
budget:
  amount_usd: 30
  period: 30d
egress_allowlist:
  - gateway.internal
  - api.notion.com
  - slack.com
runtime:
  binding: fireworks-open-model
  agent_user: boole
eval_set: agents/loops/meeting-test-eval.jsonl
promotion_rule:
  min_pass_rate: 0.9
  last_runs: 10
  max_corrections_per_run: 1
```
**When to use:** The meeting loop IS this pattern's first real instance; test-loop stays as the Phase 3 fixture. Meeting loop copies the field set, renames to `meeting`, keeps `interval: 5m`, `budget 30 USD / 30d` (LOOP-03 shape), `notion-write: A1`, `agent_user: boole`.

### Pattern 2: Poll-5min trigger seam with idempotency on page id
**What:** A `poll_notion.py` loop every 5 minutes queries the meetings data source for pages with `last_edited_time` after the stored cursor, and calls `Dispatcher.enqueue({"loop": "meeting", "idempotency_key": "notion-page-<page-id>", ...})`. Dispatcher records the key BEFORE dispatch and refuses unknown loops BEFORE credentials/compute [VERIFIED: controller/dispatcher.py:61-71 `key = envelope["idempotency_key"]` … `if loop not in self.registry(): … return None`], and duplicate keys enqueue once (`run-%s` + UNIQUE, IntegrityError → same run id) [VERIFIED: controller/dispatcher.py:72-81]. Cursor persists in run-state DB or a local state file; payloads stay untrusted (ADR-0006 rule 3 — registry is the only authority for tools/credentials/destinations).
**When to use:** Always for LOOP-01's settled seam. Poll interval constant lives beside `POLL_SECONDS = 15` [VERIFIED: controller/dispatcher.py:24]; the 5-minute Notion cadence is a loop-config value, not the dispatcher's kill-flag poll.

### Pattern 3: Extract → propose → park → approved-write
**What:** The container workflow fetches page + block children, extracts decisions/actions/owners/dates per `prompts.md`, drafts the Notion property patch, posts the Slack summary with the patch preview, then `park(run_id, question)` which "Holds a DB row, never a process" [VERIFIED: controller/dispatcher.py:107-114]. Resume accepts ONLY the loop owner's answer [VERIFIED: controller/dispatcher.py:116-128 `if sender != owner: … return False`], matching the Slack bot's owner-only verdict shape (`yes <id>`/`no <id>`, non-owner rejected) [VERIFIED: agents/marketplace/plugins/slack/server.py:210-217]. Only after `resume == True` does the workflow PATCH the page. Stranger answers leave the run parked [VERIFIED: controller/test_dispatcher.py:92-100].
**When to use:** Every Notion write in this loop (A1). Slack summary itself posts at A2 without parking (test-loop precedent: `slack-post: A2`).

### Pattern 4: Cost visibility without live gateway
**What:** Two layers, both testable with fakes: `record_cost(run_id, amount)` accumulates `cost_usd` per run [VERIFIED: controller/dispatcher.py:135-140; test accumulates 1.5+2.5=4.0 in controller/test_dispatcher.py:137-144], and `dispatch` refuses over-budget runs via `_spend_for` [VERIFIED: controller/dispatcher.py:101-103, 142-149]. The $30/30d loop budget in YAML is the trial envelope; gateway per-loop key budgets (Phase 3) are the live backstop. Checks assert the ledger path with a fake gateway dict — no keys needed.
**When to use:** LOOP-03 metering path ships in Phase 4; the 10-meeting live trial itself is owner-go.

### Anti-Patterns to Avoid
- **Selecting the Granola integration in plans:** LOOP-01 is an owner decision; any plan naming a Granola tool/API/credential violates CONTEXT. Document assumption + fixture.
- **Writing to Notion before approval:** A1 means propose-then-park; direct PATCH from the extraction step breaks LOOP-02 and the promotion story.
- **Trusting trigger payloads:** Page content is untrusted input (spec §7); tools/credentials/destinations come from YAML only, never from page fields.
- **Blocking compute while parked:** `park` holds a row; a workflow that sleeps-with-container burns host hours and breaks idle-stop. Exit after parking; resume re-queues.
- **Shared secrets between Ada and Boole:** Broker issues per-run dirs from loop-declared names only; any cross-agent secret read breaks ACC-07.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model access + budgets | Custom LLM client | Phase 3 LiteLLM gateway (`boole-default` binding) [VERIFIED: agents/gateway/litellm-config.yaml:5-8] | Per-loop keys, budgets, attribution already there |
| Queue, approvals, kill switch | New scheduler/state | `Dispatcher` enqueue/dispatch/park/resume/record_cost | Unit-tested (12 tests, fake clock/gateway); idempotency + owner-gate already correct |
| Per-run credentials | Env-var passing | `hyprn-credential-broker` (agent-owned 0500 dir, temp+chown+move, cleanup) [VERIFIED: agents/host/files/hyprn-credential-broker:89-103, 28-34] |tmpfs handoff, least-privilege-by-declaration, no agent-readable residue |
| Container execution | Ad-hoc docker calls | `hyprn-run-runner` (kill guards, idle-stop hold, allowlist→env, read-only `--rm`) [VERIFIED: agents/host/files/hyprn-run-runner:21-28, 42-49] | Kill/idle/egress semantics already encoded |
| Slack approvals | New bot framework | `server.py` Socket-Mode shape + `permission_request` card [VERIFIED: agents/marketplace/plugins/slack/server.py:287-306] | Allowlist, dedupe, owner verdicts proven |
| Notion CRUD SDK | HTTP wrapper lib | stdlib `urllib` + 3 REST calls | 3 endpoints suffice; avoids SDK churn across the data-source API migration |

**Key insight:** Phase 4 is a wiring phase — one YAML, one poller, one workflow script, two check scripts. Every hard problem (queue, auth, budget, isolation) already has a tested answer; the planner's job is reuse with narrow seams, not new systems.

## Common Pitfalls

### Pitfall 1: Notion data-source API migration (query endpoint moved)
**What goes wrong:** Code POSTs to `/v1/databases/{id}/query` with a new `Notion-Version` header and gets warnings/errors.
**Why it happens:** As of `Notion-Version: 2025-09-03`, `databases.query` is legacy; queries go to `POST /v1/data_sources/{id}/query` [CITED: developers.notion.com/reference/intro + notion-py-client docs]. Plan-era headers (`2022-06-28` in older guides) predate this.
**How to avoid:** Pin `Notion-Version: 2026-03-11` [CITED: developers.notion.com/guides/get-started/quick-start], query the data-source id, keep a fallback probe: if `databases.query` warns, resolve `GET /v1/databases/{id}` → `data_sources[]` → query that id. Planner must include this branch.
**Warning signs:** 400s on query with a fresh version header; empty results despite shared pages.

### Pitfall 2: Integration shares the wrong object
**What goes wrong:** Poller authenticates but sees zero pages.
**Why it happens:** Sharing the page that *contains a linked view* is not enough — "API access requires sharing the original database with the connection" [CITED: developers.notion.com/guides/data-apis/working-with-databases]. Same for templates (bot must have access to the template page in the same workspace) [CITED: developers.notion.com/reference/post-page].
**How to avoid:** Owner checklist: share the *original meetings database* (not a linked view) with Boole's integration; capability "Insert Content" required or writes 403 [CITED: developers.notion.com/reference/post-page]. Checks assert 403-vs-empty distinction in fixture.

### Pitfall 3: Approval-id confusion across bots
**What goes wrong:** Boole's approval answer resumes the wrong run, or Ada's bot eats Boole's `yes`.
**Why it happens:** Request ids are 5-char `[a-km-z]{5}` strings validated by regex [VERIFIED: agents/marketplace/plugins/slack/server.py:35, 289] and tracked in a per-process `pending` set [VERIFIED: server.py:129, 211-213]. Two bots = two processes = id collision possible in principle.
**How to avoid:** Scope approval questions with run id + page id in text; controller `resume` double-checks sender==owner; planner keeps Boole's Socket Mode on the controller (spec §5), never shared with Ada's channel.

### Pitfall 4: Cursor loss double-runs meetings
**What goes wrong:** Poller restart re-queues every recent page.
**Why it happens:** Cursor kept in memory only.
**How to avoid:** Persist cursor (DB or state file) AFTER successful enqueue; rely on idempotency keys as backstop (duplicate → same `run-<key>`). Unit test: same page twice → one row [VERIFIED pattern: controller/test_dispatcher.py:32-38].

### Pitfall 5: Extraction hallucinates decisions
**What goes wrong:** Loop "decides" things the meeting never said; owner corrections exceed the promotion bar (>1/meeting).
**Why it happens:** Free-form prompt with no output contract; Phase 5 evals don't exist yet.
**How to avoid:** `prompts.md` pins a JSON contract `{decisions[], actions[{text, owner, due}], open_questions[], patch{properties}}` with a "quote the source line" rule per item; malformed-page fixture proves graceful degrade (propose-nothing + Slack note). This is also the Phase 5 eval seed.

## Code Examples

### Notion poll — query new pages (stdlib)
```python
# Source: https://developers.notion.com/reference/intro (base URL, version header,
# data_sources/query) + https://developers.notion.com/guides/get-started/quick-start
import json, urllib.request

NOTION = "https://api.notion.com"
VERSION = "2026-03-11"  # [CITED: quickstart]

def query_meetings(token: str, data_source_id: str, start_cursor=None, since=None):
    body = {"page_size": 20}
    if since:
        body["filter"] = {"property": "Last edited", "last_edited_time": {"after": since}}
        # NOTE: replace "Last edited" with the meetings DB's actual property name
    if start_cursor:
        body["start_cursor"] = start_cursor
    req = urllib.request.Request(
        f"{NOTION}/v1/data_sources/{data_source_id}/query",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Notion-Version": VERSION,
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)
```

### Notion approved write — PATCH page properties
```python
# Source: https://developers.notion.com/reference/patch-page
import json, urllib.request

def apply_patch(token: str, page_id: str, properties: dict):
    # properties keys MUST match the parent data source schema [CITED: patch-page]
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=json.dumps({"properties": properties}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Notion-Version": "2026-03-11",
                 "Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)
    # No DELETE exists: removals archive via PATCH {"archived": True} [CITED: API-endpoints reference]
```

### Trigger seam — enqueue one run per page (reuses dispatcher)
```python
# Source: controller/dispatcher.py (enqueue/dispatch) — symbols read this session
dispatcher.enqueue({
    "loop": "meeting",                       # must be in registry or refused
    "idempotency_key": f"notion-page-{page_id}",  # duplicate page → same run
    "budget_usd": 30.0,
})
dispatcher.record_cost(run_id, model_cost_usd)  # per-run ledger, no gateway needed
```

### Approval park — propose then wait (reuses park/resume)
```python
# Source: controller/dispatcher.py park/resume — symbols read this session
dispatcher.park(run_id, f"Apply Notion patch to {page_id}?\n{preview}")
# ... Boole bot posts question; owner replies `yes <id>` / `no <id>` ...
dispatcher.resume(run_id, answer="yes", sender=msg_user, owner="platform-owner")
```

### File-drop fallback fixture (no Granola)
```bash
# A test meeting = a JSON file dropped in agents/loops/testdata/meeting-pages/.
# The poller in --fixture mode reads the dir instead of the API; a manual-page
# variant pastes the same JSON. No credentials, no network, no Granola.
ls agents/loops/testdata/meeting-pages/
# new.json  updated.json  malformed.json
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `POST /v1/databases/{id}/query` | `POST /v1/data_sources/{id}/query` | `Notion-Version 2025-09-03` [CITED] | Poller must resolve data-source id; keep legacy fallback probe |
| Notion personal tokens `secret_*` | Token prefix `ntn_*` in newest quickstart [CITED] | 2026 docs refresh | Shape-checks accept both; never log values |
| Meeting loop as new infra | Meeting loop as registry entry + scripts | ADR-0006 (proposed) | No harness build; binding-only provider switch |

**Deprecated/outdated:**
- `databases.query` under new version headers: legacy, warns/errors — use `dataSources.query` [CITED].
- Granola-side automation in Phase 4: out of scope by CONTEXT — any plan including it is wrong.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | LOOP-01 Granola→Notion leg resolves to *some* owner-settled path writing pages into the shared meetings DB | Architecture diagram | Poller has nothing to read; mitigated by file-drop fallback for all tests |
| A2 | Meetings DB exposes a sortable `last_edited_time`/created-time for cursor polling | Code Examples | Poller falls back to full-list + seen-set dedupe; extra reads, same correctness |
| A3 | `curl`/`jq` present on host for broker/smoke paths | Standard Stack | Provisioning adds them; checks skip-with-reason otherwise |
| A4 | PyYAML age/download figures (~18 yrs, ~100M/mo) | Standard Stack | Cosmetic; planner re-confirms via `pip index` |
| A5 | 10 meetings fit $30/mo on Fireworks open-model binding | LOOP-03 | Trial overruns; mitigated by per-run ledger + dispatcher pre-check + gateway backstop; binding-only switch to cheaper model |

## Open Questions

1. **How do Granola notes reach Notion (LOOP-01)?**
   - What we know: Spec says "None: people use it; notes reach agents through Notion" [VERIFIED: docs/specs/agent-fleet.md:106]; ADR-0006 lists it as an open question before the meeting loop [VERIFIED: docs/adr/0006-agent-first-operating-model.md:135-138].
   - What's unclear: The chosen mechanism (manual, Granola export, automation vendor).
   - Recommendation: Owner decision recorded in `meeting-loop-go.md` before live runs; plans proceed on the poll seam + fixture regardless.

2. **Meetings DB schema (property names/ids)?**
   - What we know: Notion requires property names/ids to match the parent schema [CITED: patch-page].
   - What's unclear: Actual Title/Status/Date property names until the owner shares the DB.
   - Recommendation: Workflow reads schema via `GET /v1/databases/{id}` at plan time; patch builder maps by id, not display name.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 + `yaml` | Poller, workflow, validator | ✓ | 3.11.2 / import ok | — |
| Docker | Runner live dry-run | ✓ (binary) | 29.9.0 | Static assertions; live proof at owner-go |
| `boole` Linux user | Runner + isolation live checks | ✗ | — | Static assertions now; live checks gated on `id boole` |
| Terraform | `boole-notion.tf` validate | ✗ | — | Reviewed-not-applied; validate at owner-go apply |
| Notion API + token | Poller live path | ✗ (no token, by design) | `2026-03-11` header | Fixture dir + manual-page fallback; live at owner-go |
| Slack Boole bot | Approval live path | ✗ (Phase 3 vendor step) | — | Fake `park`/`resume` + recorded answers |
| Gateway/Cloud SQL | Live cost path | ✗ (Phase 3 pending) | — | `record_cost` ledger with fake spend dict |

**Missing dependencies with no fallback:** none (all live legs have fakes by design).
**Missing dependencies with fallback:** `boole` user, Terraform, Notion token, Slack bot, gateway — each with a fake/static path above; planner gates live proofs behind the owner-go checkpoint.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python 3 stdlib `unittest` + Bash `tests/agents/checks/*.sh` |
| Config file | none — `run.sh` auto-discovers `checks/*.sh` [VERIFIED: tests/agents/run.sh:41-46] |
| Quick run command | `python3 -m unittest discover -s controller && bash tests/agents/checks/meeting.sh` |
| Full suite command | `bash tests/agents/run.sh` (appends dated record to `runbooks/agents/`) [VERIFIED: tests/agents/run.sh:48-62] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOOP-01 | Poller emits one envelope per new page; dup page → one run | unit | `python3 -m unittest discover -s controller -p "test_poll*"` | ❌ Wave 0 |
| LOOP-02 | Extract→propose→park; write only after owner yes; stranger ignored | unit + check | `python3 -m unittest discover -s controller` + `bash tests/agents/checks/meeting.sh` | ❌ Wave 0 (extend existing park/resume tests) |
| LOOP-03 | Cost accumulates per run; over-budget refused | unit | existing `TestBudgetKill` pattern [VERIFIED: controller/test_dispatcher.py:109-144] | ❌ Wave 0 (meeting-budget case) |
| OPS-02 | Notion/Workspace declarations carry no values; checklist complete | check | `bash tests/agents/checks/meeting.sh` (grep `xox\|ntn_\|secret_` = 0) | ❌ Wave 0 |
| ACC-07 | Boole↔Ada↔Codd homes/secrets/containers/tokens/bots mutually unreachable | check | `bash tests/agents/checks/isolation.sh` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m unittest discover -s controller && bash tests/agents/checks/meeting.sh tests/agents/checks/isolation.sh`
- **Per wave merge:** `bash tests/agents/run.sh`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `controller/poll_notion.py` + `controller/test_poll_notion.py` — covers LOOP-01
- [ ] `agents/loops/meeting.yaml` + `agents/loops/meeting/prompts.md` + `agents/loops/testdata/meeting-pages/{new,updated,malformed}.json` — covers LOOP-02 fixtures
- [ ] `agents/host/files/hyprn-meeting-workflow` — covers LOOP-02 run path
- [ ] `infra/agents/boole-notion.tf` (declared-not-created) — covers OPS-02
- [ ] `tests/agents/checks/meeting.sh` — covers LOOP-01/02/03 + OPS-02 static assertions
- [ ] `tests/agents/checks/isolation.sh` — covers ACC-07
- [ ] `runbooks/agents/meeting-loop-go.md` — owner-go checklist (LOOP-01 settle, Workspace user, integration share, trial)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Per-agent secrets in Secret Manager; broker issues loop-declared only; no Granola creds anywhere |
| V3 Session Management | no | No interactive sessions; parked runs are DB rows, not sessions |
| V4 Access Control | yes | Dispatcher registry gate; `resume` owner-only; Notion integration scoped to meetings DB |
| V5 Input Validation | yes | Meeting content untrusted (spec §7); schema-match patch keys; malformed fixture degrades to propose-nothing |
| V6 Cryptography | no new | Reuse Phase 3 broker/token flows; never hand-roll |

### Known Threat Patterns for stdlib-poller + Notion + Slack stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious meeting text injects instructions ("approve all writes") | Tampering / Elevation | Payloads are data, never authority (ADR-0006 rule 3); prompts.md carries the untrusted-input boundary; registry-only tools/creds |
| Approval spoofing from non-owner | Spoofing | `resume` sender==owner + Slack allowlist + `seen.json` dedupe; stranger answers ignored |
| Token exfiltration via logs/summaries | Information disclosure | Never print secret values (AGENTS.md); Slack summaries carry patch preview, never tokens; broker `unset`s key material |
| Runaway polling cost | Denial of service | 5-min cadence + idempotency + dispatcher budget pre-check + gateway per-loop budget + kill flags |
| Cross-agent secret/container reach | Elevation | ACC-07 isolation checks (homes 0700, secret files `agent:400`, no cross-reads — host-checks pattern [VERIFIED: tests/agents/host-checks.sh:38-46]) |

## Sources

### Primary (HIGH confidence)
- `controller/dispatcher.py` + `controller/test_dispatcher.py` + `controller/schema.sql` — enqueue/idempotency, park/resume, budget/kill, cost ledger (read this session)
- `agents/loops/validate.py` + `agents/loops/testdata/test-loop.yaml` — REQUIRED set, A-levels, reference loop shape (read this session)
- `agents/host/files/hyprn-credential-broker` + `hyprn-run-runner` — per-run creds, container shape (read this session)
- `agents/marketplace/plugins/slack/server.py` + `slack-app-manifest.yaml` — bot shape, verdict regex, scopes (read this session)
- `tests/agents/{run.sh,host-checks.sh,checks/*.sh}` — harness + isolation patterns (read this session)
- `docs/specs/agent-fleet.md` §2/§5/§7 + ADR-0006 — loop model, triggers, tools table, Granola boundary (read this session)

### Secondary (MEDIUM confidence)
- https://developers.notion.com/reference/patch-page — PATCH properties must match schema; Insert Content capability or 403
- https://developers.notion.com/reference/intro — base URL, version headers, `data_sources/query`
- https://developers.notion.com/guides/get-started/quick-start — `Notion-Version: 2026-03-11`, Bearer auth
- https://developers.notion.com/guides/data-apis/working-with-databases — share the original DB, not a linked view

### Tertiary (LOW confidence)
- PyYAML age/download figures — cosmetic, planner re-confirms
- Host `curl`/`jq` presence — assumed, checked at plan time

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - in-repo reuse verified by Read; Notion shapes cited to official docs but not live-probed (no token by design)
- Architecture: MEDIUM - all seams exist as tested code; meeting wiring is new but narrow
- Pitfalls: MEDIUM - data-source migration + share-scope failure modes confirmed in official docs; extraction-hallucination rate unknowable pre-trial

**Research date:** 2026-10-13
**Valid until:** 30 days (stable domain; re-check Notion-Version header if docs announce a newer version)
