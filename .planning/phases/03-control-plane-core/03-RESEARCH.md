# Phase 3: Control plane core - Research

**Researched:** 2026-10-13
**Domain:** Fleet control plane — loop registry, queue/dispatcher/run-state, LiteLLM gateway, credential broker, run runner, approvals/budgets/kill-switch, Boole identities
**Confidence:** MEDIUM

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Deliver the loop registry schema (`agents/loops/<name>.yaml`: trigger, steps, agent steps, tools, autonomy per action, budget, eval set, promotion rule, owner), dispatcher/queue/run-state logic, credential-broker interface, and run runner as code with unit-testable seams (fake queue, fake gateway, fake broker).
- A test loop definition exists and passes static validation; its live run waits for keys and is an explicit owner-go checkpoint, not attempted here.
- Gateway (LiteLLM on Cloud Run, internal ingress, Cloud SQL for keys/budgets/spend) and controller wiring ship as reviewed Terraform + config, apply deferred to owner go when keys arrive. Kill switch and budget enforcement live in code paths testable with fakes.
- No `terraform apply`, no key creation, no Secret Manager writes in this phase's execution.
- Declare Boole's runtime identities (Linux user, Terraform blocks, Slack app manifest, gateway key placeholder) without creating vendor-side objects. Vendor steps are owner checklists in the runbook.
- ADR-0006 acceptance stays a Phase 3 dependency — plans must flag any build that assumes its acceptance.
- EGR-03: loop definitions carry the destination allowlist; the runner enforces it from the first run. Prove the enforcement shape with a local container dry-run where possible (rootless, no creds); otherwise static assertion on the runner code + schema validation.

### Agent's Discretion
All Phase 3 answers taken at agent discretion under the autonomous-run direction. Planner must keep every key/cloud-gated step an explicit owner-go checkpoint.

### Deferred Ideas (OUT OF SCOPE)
- Live test-loop run on Fireworks (needs keys + owner go).
- Boole vendor objects (Slack app install, Workspace user is Phase 4).
- Webhook receiver (WEB-01, needs own ADR).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CP-01 | Model gateway (LiteLLM on Cloud Run, internal ingress, Cloud SQL), one virtual key + dollar budget per loop, cost logs per run | LiteLLM virtual-key + budget design; Cloud Run/Cloud SQL Terraform shape |
| CP-02 | Fleet controller: queue + dispatcher + run state (own DB on gateway's Cloud SQL), idempotency keys, run log; starts host when pending | SQLite-schema-now/Cloud-SQL-at-apply pattern; idempotency via UNIQUE constraint |
| CP-03 | Approval as tool call; run parked hours without compute; resume on owner's Slack-bot answer; controller holds ops Socket Mode connections | Parked-state (no process held) + wake.py Socket Mode extension pattern |
| CP-04 | Budgets stop over-limit runs; kill switch per loop/agent/fleet within a minute | Two-layer budget (dispatcher pre-check + LiteLLM max_budget backstop); polled kill flags |
| CP-05 | Loops declared in `agents/loops/<name>.yaml`; dispatcher runs only registered loops | Registry schema + static validator + registry-gated dispatch |
| CP-06 | Credential broker gives each run only its loop's declared credentials, short-lived where possible, from Secret Manager | Token-loader-pattern broker interface with fake seam |
| RT-01 | Run runner on host: pending runs as agent's Linux user in fresh rootless container behind egress proxy, Fireworks via gateway; binding-only provider switch; running containers block idle-stop | Rootless container shape; allowlist enforcement; idle-stop inhibition |
| EGR-03 | Run containers reach only gateway + loop's declared tool hosts from first run; rest refused + logged | Allowlist-in-loop-definition + runner translation to container network config |
| OPS-01 | Boole runtime identities: Linux user `boole`, Slack app `Boole (AI agent)` tokens in Secret Manager, gateway key; Terraform-declared where vendor allows | Declared-not-created identity blocks + owner checklist runbook |
| COST-01 | Owner sets revised monthly budget for `hyprn-agents` | Budget values as config/placeholder, owner-go step |
| ACC-09 | Controller + gateway identities hold exactly declared roles; gateway unreachable from internet; run container holds only its loop's credentials | IAM least-privilege blocks; INGRESS internal-only; per-run tmpfs credential dirs |

## Project Constraints (from AGENTS.md)

- Product code never enters this repository; platform infrastructure never enters a product repository.
- `hyprn-agents` is engineering tooling: no product workload, no staging/prod access.
- Every cloud/IAM/billing/GitHub/Slack/Claude-org step runs only after the platform owner's explicit go for that exact step. Removals get their own go.
- Terraform: plan, review, apply exactly the reviewed plan. Staging and prod separate (not applicable here — `hyprn-agents` only).
- Never commit credentials, Terraform state/plan files, tfvars with secret values, service-account keys, or session data. Secret values live in password manager (master) + Secret Manager (runtime).
- Never print a secret value; check tokens by shape only.
- Run `gcloud`/`terraform`/`gh` with HYPRN-dedicated configs (`CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`, `GH_CONFIG_DIR`).
- Repository content names roles/groups/agent identities, never people.
- Record what was done in the relevant runbook; dated records in `runbooks/agents/`.

## Summary

The control plane is a thin layer over bought harnesses (ADR-0006 build-or-buy: LiteLLM, managed Cloud SQL, official SDKs) plus three small built pieces: a YAML loop registry with static validation, a queue/dispatcher/run-state controller with fake-testable seams, and a per-run credential broker plus rootless-container runner that extend the existing host token-loader pattern. Everything key- or cloud-gated ships as reviewed-not-applied code and config; enforcement logic (budgets, kill switch, egress allowlist) lives in code paths fully testable with fakes and a local no-creds container dry-run.

**Primary recommendation:** Build the registry schema + validator, SQLite-backed controller with fake seams, broker interface mirroring `hyprn-agent-secrets`/`hyprn-agent-github-token`, and a rootless-container runner enforcing the loop allowlist — all verified by stdlib unit tests and `tests/agents/run.sh` checks; ship LiteLLM/Cloud Run/Cloud SQL/Boole identities as reviewed Terraform + config with owner-go apply checkpoints.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Loop registry + static validation | Repo (config as code) | — | Playbook is code; dispatcher reads it, never writes it |
| Queue / dispatcher / run state | Controller VM (`hyprn-agents-wake-01` successor) | Cloud SQL (storage) | Always-on scheduler; state in managed Postgres |
| Model gateway (LiteLLM) | Cloud Run (serverless) | Cloud SQL (keys/budgets/spend) | Metered traffic needs independent scaling from controller |
| Credential broker | Host (root-owned loader) | Secret Manager (source of truth) | Secrets must never touch agent-readable disk; tmpfs handoff |
| Run runner + containers | Host (per-agent Linux user) | — | Needs agent homes, rootless Docker, egress proxy |
| Approvals (Slack bot Q&A) | Controller (Socket Mode) | Run state DB (parked runs) | Parked runs hold DB rows, not compute; one connection holder |
| Budgets / kill switch | Dispatcher pre-check + gateway backstop | Run state DB (flags/ledger) | Two layers: refuse-before-start and enforce-during-run |
| Boole identities | Terraform + provisioning | Vendor consoles (manual) | Declared in code; created by owner checklist |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3 stdlib (`sqlite3`, `unittest`, `json`, `urllib`) | 3.11 (host) [VERIFIED: `python3 --version` → 3.11.2] | Controller, broker interface, run-state DB, unit tests | Matches `agents/wake/wake.py` (stdlib + `python3-websocket` only); zero new deps |
| LiteLLM proxy (container `ghcr.io/berriai/litellm`) | Pinned digest at plan time [CITED: https://docs.litellm.ai/docs/proxy/virtual_keys] | Model gateway with virtual keys + per-key budgets | Spec-mandated (fleet §6, ADR-0006); budgets require Postgres backend [CITED: https://docs.litellm.ai/docs/proxy/users] |
| Cloud SQL Postgres | Smallest EU-region tier at apply time [ASSUMED] | LiteLLM key/budget/spend store + controller run-state DB | LiteLLM budgets/virtual keys do not function without a database [CITED: https://docs.litellm.ai/docs/proxy/users] |
| Rootless Docker (host) | 29.9.0 [VERIFIED: `docker --version`]; `rootlesskit`+`slirp4netns` present [VERIFIED: on PATH] | Per-run fresh containers under agent Linux user | Already on host; spec §4 mandates fresh rootless container per run |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | Pinned at plan time via `pip index versions pyyaml` [ASSUMED] | Parse `agents/loops/*.yaml` in validator + dispatcher | Stdlib has no YAML parser; YAML is spec-mandated file format |
| `google_cloud_run_v2_service` (+ `google_sql_database_instance`) Terraform resources | Provider version from `infra/agents/versions.tf` lock | Reviewed-not-applied gateway + DB shape | Extends existing `infra/agents/` root patterns |
| Bash + existing `tests/agents/checks/*.sh` harness | n/a | Acceptance checks joined to `run.sh` | ACC-08 continuity; every phase adds checks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite run-state (now) | Postgres from day one | No live DB without apply; SQLite schema ports 1:1 to Cloud SQL at apply — use SQLite now |
| LiteLLM | Raw provider SDKs per loop | Loses per-loop keys, budgets, attribution — rejected by spec §6 |
| Custom queue (Pub/Sub) | SQLite queue table | Pub/Sub needs provisioning + apply; SQLite queue with `FOR UPDATE SKIP LOCKED`-equivalent polling is enough for one-loop scale [ASSUMED] |
| Podman | Rootless Docker | Docker + rootlesskit already on host [VERIFIED]; don't switch |

**Installation:**
```bash
pip install "pyyaml==<version-from-pip-index>"   # validator/dispatcher only; pin in plan
# No other new packages. LiteLLM runs as a pinned container image, not a pip install.
```

**Version verification:** `python3 --version` → 3.11.2 [VERIFIED this session]; Docker 29.9.0 [VERIFIED]; `pytest` NOT installed (use `python3 -m unittest`, stdlib) [VERIFIED: import failed]; `terraform` NOT on PATH [VERIFIED] — Terraform validation happens at owner-go apply time, plans must note this gap.

## Package Legitimacy Audit

No application packages are installed by this phase beyond one well-established parser. LiteLLM is consumed as a pinned container image, not a registry package.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `pyyaml` | PyPI | ~18 yrs | ~100M/mo [ASSUMED] | github.com/yaml/pyyaml [ASSUMED] | OK (pending planner `pip index` confirm) | Approved with version pin |
| `ghcr.io/berriai/litellm` image | GHCR | multi-year project [ASSUMED] | n/a (image) | github.com/BerriAI/litellm [CITED: docs.litellm.ai] | OK (pin by digest in plan) | Approved, digest-pinned |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious (SUS):** none.
*`pyyaml` version/age/download figures are [ASSUMED] — planner must confirm with `pip index versions pyyaml` and pin before use.*

## Architecture Patterns

### System Architecture Diagram

```text
schedule ─┐
polling ──┼─► queue ─► dispatcher ─► pending run ──┬─► approval? ─► PARKED (DB row, no process)
Slack ────┘     │          │                       │       ▲               │
                │          ├─ loop registry         │       └── owner answer (Socket Mode, controller-held)
                │          ├─ run state (runs/steps/approvals/idempotency)
                │          ├─ budgets (pre-check) · kill switch (poll ≤60s)
                │          └─ run log + cost/run                │
                └─ one envelope + idempotency key; payloads untrusted
                                                           ▼
                                              run runner (host, as agent user)
                                                         │
                                              credential broker ─► tmpfs per-run dir (0500, agent-owned)
                                                         │         (gateway key, bot token, notion, gh token)
                                                         ▼
                                              fresh rootless container ─► egress proxy ─► gateway ─► provider
                                              (only loop's allowlist)      (LiteLLM, internal ingress)
```

A reader traces the primary use case: trigger envelope → idempotent enqueue → budget/kill/registry gate → broker mints per-run creds → rootless container runs behind proxy through gateway → cost logged per run.

### Recommended Project Structure
```text
agents/loops/                 # registry (greenfield this phase)
├── <name>.yaml               # loop definition (schema below)
├── validate.py               # static validator (stdlib + pyyaml)
└── testdata/test-loop.yaml   # test loop, static-validated only
controller/                   # queue + dispatcher + run state (greenfield)
├── schema.sql                # runs/steps/approvals/idempotency/budgets/killswitch tables
├── dispatcher.py             # enqueue/dispatch/park/resume/kill logic, fake seams
└── test_dispatcher.py        # python3 -m unittest, fakes only
agents/host/files/
├── hyprn-credential-broker   # per-run broker (extends hyprn-agent-secrets pattern)
└── hyprn-run-runner          # pull pending runs, rootless container exec
infra/agents/
├── gateway.tf                # Cloud Run LiteLLM + Cloud SQL (reviewed, NOT applied)
├── controller.tf             # scheduler/service wiring (reviewed, NOT applied)
└── boole.tf                  # Boole secrets + IAM (declared, NOT applied)
tests/agents/checks/
├── loops.sh                  # registry validation check
├── controller.sh             # unit-test + schema check
└── runner.sh                 # static assertion + container dry-run
```

### Pattern 1: Registry-gated dispatch
**What:** Dispatcher loads `agents/loops/*.yaml` through `validate.py`; unknown loop names are refused before any credential or compute is touched. Trigger envelopes carry an idempotency key stored as a `UNIQUE` column — duplicate deliveries enqueue once.
**When to use:** Every trigger path (schedule, poll, Slack, manual).
**Example:**
```yaml
# agents/loops/meeting-test.yaml — field set from CP-05 + EGR-03 (shape [ASSUMED], planner confirms)
name: meeting-test
owner: platform-owner
trigger: {type: poll, source: notion-meetings, interval: 5m}
steps: [fetch-page, extract, propose]
agent_steps: [extract]
tools: [notion-read, slack-post]
autonomy: {notion-write: A1, slack-post: A2}
budget: {amount_usd: 30, period: 30d}
egress_allowlist: [gateway.internal, api.notion.com, slack.com]
runtime: {binding: fireworks-open-model, agent_user: boole}
eval_set: agents/loops/meeting-test-eval.jsonl
promotion_rule: {min_pass_rate: 0.9, last_runs: 10, max_corrections_per_run: 1}
```

### Pattern 2: Parked approvals (no compute held)
**What:** An agent step requesting approval writes an `approvals` row and the runner exits; the run state becomes `awaiting_approval`. The controller (which holds ops agents' Socket Mode connections, extending the `Waker` envelope-ack pattern in `wake.py:102-126` [VERIFIED: agents/wake/wake.py:102-126]) posts via the bot; the owner's reply flips the row and re-queues. Hours-long waits cost zero compute.
**When to use:** Every A1 action (spec §9).

### Pattern 3: Two-layer budget + kill switch
**What:** Dispatcher pre-check refuses over-budget runs (reads spend ledger; fake in tests); LiteLLM per-key `max_budget` is the hard backstop — after a key crosses it, requests fail [CITED: https://docs.litellm.ai/docs/proxy/users]. Kill flags (loop/agent/fleet) live in the run-state DB; dispatcher and runner poll them at ≤60s intervals, satisfying the within-a-minute MUST.
**When to use:** All autonomous runs, from the first test loop.

### Anti-Patterns to Avoid
- **Blocking-process approvals:** holding a container/VM while waiting for Slack — violates CP-03; park in DB instead.
- **Trigger authority:** letting poll payload content select tools/credentials — payloads are untrusted (ADR-0006 rule 3); only the reviewed YAML carries authority.
- **Seat models for loops:** running autonomous loops on Claude seats — spec §1 forbids; loops use gateway keys only.
- **Shared credential files:** one token file readable by multiple agents — violates ACC-07/ACC-09; per-run tmpfs dirs, mode 0500, agent-owned (extends `hyprn-agent-github-token:34-42` [VERIFIED]).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Model routing, key auth, spend metering | Gateway proxy in Python | LiteLLM proxy + Postgres [CITED: https://docs.litellm.ai/docs/proxy/virtual_keys] | Budgets, virtual keys, cost logs, 100+ providers; budget enforcement without DB silently does nothing |
| JWT minting for GitHub Apps | Custom auth | Extend `hyprn-agent-github-token` (RS256 JWT → installation token, 1h) [VERIFIED] | Key handling, tmpfs perms, timer pattern already reviewed |
| Secret storage/rotation | Files, env vars in repo | Secret Manager + root-owned loader → tmpfs [VERIFIED: `hyprn-agent-secrets:18-41`] | Per-secret IAM, no disk persistence, missing-secret tolerance |
| Container isolation | `chroot`/namespaces by hand | Rootless Docker (present on host) [VERIFIED] | User-namespaces, network control, `--rm` freshness for free |
| Cron/scheduler | Sleep loops in dispatcher | Cloud Scheduler → queue (TF reviewed-not-applied); SQLite poll loop only as interim [ASSUMED] | Managed retries, IAM, audit |

**Key insight:** The phase's value is the thin glue (registry, dispatch rules, broker interface, runner) — every adjacent hard problem (metering, isolation, secret storage) already has a bought or built solution in-repo or in-spec.

## Common Pitfalls

### Pitfall 1: LiteLLM budgets silently unenforced without a database
**What goes wrong:** Keys with `max_budget` still authorize everything.
**Why it happens:** All budget enforcement reads spend from the database; DB-less deployments log a one-time warning and never block [CITED: https://docs.litellm.ai/docs/proxy/users].
**How to avoid:** Gateway Terraform must include Cloud SQL + `DATABASE_URL` wiring; add a `loops.sh`-style check asserting `DATABASE_URL` is set in the reviewed config.
**Warning signs:** Startup log `No connected db`; spend API returns zeros.

### Pitfall 2: Fireworks model naming mismatch
**What goes wrong:** `model_not_found` from LiteLLM for a valid Fireworks model.
**Why it happens:** LiteLLM requires the `fireworks_ai/` provider prefix and model- or router-qualified IDs; bare `fireworks_ai/firerouter` is interpreted as a model name [CITED: https://docs.fireworks.ai/ecosystem/integrations/litellm].
**How to avoid:** Pin exact `model:` strings from Fireworks docs in gateway config; provider switch (RT-01) changes only the `model:` line + env key, never client code.
**Warning signs:** 404 on first test call; works after prefix fix.

### Pitfall 3: Cloud Run publicly reachable gateway
**What goes wrong:** Gateway answers from the internet, failing ACC-09.
**Why it happens:** Default ingress is `INGRESS_TRAFFIC_ALL`.
**How to avoid:** `ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"` [CITED: Terraform registry `google_cloud_run_v2_service` + Cloud docs sample] plus no public IAM invoker binding; assert both in the review checklist check.
**Warning signs:** `curl` from outside VPC succeeds.

### Pitfall 4: Runner leaks credentials across runs
**What goes wrong:** Run B reads run A's tokens from a shared dir.
**Why it happens:** Reusing one secrets directory instead of per-run tmpfs with strict ownership.
**How to avoid:** Broker creates `/run/hyprn-agents/runs/<run-id>/` mode 0500 owned by the agent user, deletes on run end; container mounts only that dir (mirror `hyprn-agent-github-token:34-42` [VERIFIED]).

### Pitfall 5: Idle-stop kills the host mid-run
**What goes wrong:** `hyprn-idle-stop` stops the host while a container runs.
**Why it happens:** Idle detection watches sessions, not containers.
**How to avoid:** Runner registers activity (touch a hold file / inhibit); idle-stop must check `docker ps` for run containers before stopping — spec §4: running containers count as activity.

## Code Examples

### Loop registry validation entry point
```python
# agents/loops/validate.py — stdlib + pyyaml [ASSUMED shape, planner confirms]
import sys, yaml
REQUIRED = {"name","owner","trigger","steps","tools","autonomy","budget",
            "egress_allowlist","runtime","eval_set","promotion_rule"}
def validate(path):
    doc = yaml.safe_load(open(path))
    missing = REQUIRED - set(doc)
    assert not missing, f"{path}: missing {sorted(missing)}"
    assert doc["egress_allowlist"], f"{path}: EGR-03 forbids empty allowlist"
    for action, level in doc["autonomy"].items():
        assert level in {"A0","A1","A2","A3"}, f"{path}: bad level {level}"
    return True
```

### Idempotent enqueue (schema excerpt)
```sql
-- controller/schema.sql [ASSUMED shape, planner confirms]
CREATE TABLE runs(
  id TEXT PRIMARY KEY,
  loop TEXT NOT NULL,                 -- must exist in registry
  state TEXT NOT NULL DEFAULT 'queued', -- queued|running|awaiting_approval|done|failed|killed
  idempotency_key TEXT NOT NULL UNIQUE,
  budget_usd REAL NOT NULL, cost_usd REAL NOT NULL DEFAULT 0,
  kill_loop INTEGER DEFAULT 0, kill_agent INTEGER DEFAULT 0, kill_fleet INTEGER DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE approvals(run_id TEXT REFERENCES runs(id), question TEXT, answer TEXT, decided_at TEXT);
```

### LiteLLM gateway config shape
```yaml
# gateway litellm config.yaml [CITED shapes: https://docs.litellm.ai/docs/proxy/configs, https://docs.fireworks.ai/ecosystem/integrations/litellm]
model_list:
  - model_name: boole-default
    litellm_params:
      model: fireworks_ai/accounts/fireworks/models/<pinned-model-id>  # exact ID at plan time
      api_key: os.environ/FIREWORKS_AI_API_KEY
  - model_name: boole-claude
    litellm_params:
      model: anthropic/<pinned-claude-model>                            # binding-only switch (RT-01)
      api_key: os.environ/ANTHROPIC_API_KEY
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY   # must start with sk- [CITED: virtual_keys doc]
```

### Cloud Run + Cloud SQL Terraform shape (reviewed, NOT applied)
```hcl
# infra/agents/gateway.tf — ingress + Cloud SQL volume [CITED: registry google_cloud_run_v2_service]
resource "google_cloud_run_v2_service" "gateway" {
  name     = "hyprn-gateway"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  template {
    containers {
      image = "ghcr.io/berriai/litellm:<pinned-digest>"
      env { name = "DATABASE_URL"; value_source { secret_key_ref { secret = google_secret_manager_secret.gateway_db_url.secret_id : version = "latest" } } }
    }
    volumes { name = "cloudsql" cloud_sql_instance { instances = [google_sql_database_instance.gateway.connection_name] } }
  }
}
```

### Credential broker interface (token-loader pattern)
```bash
# hyprn-credential-broker <agent> <run-id> <loop.yaml> — extends hyprn-agent-secrets [VERIFIED pattern]
# Reads ONLY loop-declared secrets via VM identity, writes /run/hyprn-agents/runs/<run-id>/ (0500, agent-owned),
# mints 1h GitHub installation token where declared; deletes dir on run end. Fake: fixture dir, no network.
```

### Rootless run with allowlist dry-run (no creds)
```bash
# runner dry-run proving EGR-03 shape [ASSUMED exact flags, planner confirms on host]
docker run --rm --read-only --network=hyprn-run \
  -e HTTPS_PROXY=http://proxy.internal:3128 -e ALLOWED_HOSTS="$(allowlist_of loop.yaml)" \
  --env-file /run/hyprn-agents/runs/<run-id>/env \
  test-image curl -sf --max-time 5 https://disallowed.example/ && echo LEAK || echo BLOCKED
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tmux wrapper sessions for agents | herdr session runtime, tmux fallback (spec §4) | ADR-0006 | Runner stays independent of herdr; no dependency |
| Machine account GitHub tokens | Per-agent GitHub Apps, 1h tokens (ADR-0005) | existing | Broker mints installation tokens per run, same flow |
| Group email for Ada | Workspace user per agent (ADR-0006 amends ADR-0001) | ADR-0006 (proposed — acceptance is a Phase 3 dependency) | Plans must flag anything assuming accepted status |

**Deprecated/outdated:**
- `agents/host/agents.txt` + `agents/wake/wake.json` as agent sources: replaced by `agents/fleet.yaml` in Phase 6 — controller must read a small agent list that migrates cleanly (keep a `var.agents`-style input, cf. `infra/agents/variables.tf:51-61` [VERIFIED]).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact loop-YAML field names beyond CP-05's list (e.g. `egress_allowlist`, `runtime.binding`) | Architecture Patterns | Validator/dispatcher field mismatch; planner confirms schema against spec §5/§9 |
| A2 | PyYAML age/downloads/repo; version to pin | Standard Stack | Stale pin; planner runs `pip index versions pyyaml` |
| A3 | SQLite interim queue adequate; Cloud SQL at apply | Architecture | Throughput limits later; fine for one test loop |
| A4 | Exact `docker run` rootless/egress flags on host | Code Examples | Dry-run command needs adjusting on host; static assertion fallback stands |
| A5 | Cloud SQL tier/region/pricing; LiteLLM image digest | Standard Stack / COST-01 | Budget figure wrong; owner sets COST-01 value at go-checkpoint |
| A6 | Cloud Scheduler as trigger transport (interim poll loop) | Don't Hand-Roll | Extra TF surface; confirm against controller design in planning |
| A7 | ADR-0006 accepted before dependent builds | State of the Art | Plans must carry the acceptance-flag contingency per CONTEXT.md |

## Open Questions

1. **How do meeting notes reach Notion from Granola?**
   - What we know: Out of Phase 3 scope; needed by Phase 4 (LOOP-01); ADR-0006 lists it as an open question before dependent work.
   - What's unclear: Transport mechanism (manual export, API, third-party sync).
   - Recommendation: Test loop uses a hand-placed fixture page; no Granola automation in Phase 3.
2. **Exact Fireworks open-model ID for the test loop binding?**
   - What we know: `fireworks_ai/` prefix + qualified ID required [CITED]; keys (`fw_...`) arrive later with owner go.
   - What's unclear: Which open model (price/quality) until keys exist.
   - Recommendation: Planner pins a candidate ID from Fireworks docs; live choice confirmed at owner-go checkpoint.
3. **Controller host: extend `hyprn-agents-wake-01` or separate service?**
   - What we know: Spec §4 places dispatcher on the wake controller; wake service holds Slack connections while host is stopped.
   - What's unclear: Process layout (one binary vs. sidecar) and Socket Mode handoff between wake/controller for ops bots.
   - Recommendation: Planner decides; keep wake.py's connect/disconnect contract (`wake.py:84-100` [VERIFIED]) intact.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 stdlib (sqlite3, unittest) | Controller, validator, tests | ✓ | 3.11.2 | — |
| Docker + rootlesskit + slirp4netns | Runner EGR-03 dry-run | ✓ | Docker 29.9.0 | Static assertion on runner code + schema validation |
| `jq`, `gcloud` (HYPRN configs) | Secret-shaped checks, read-only inspection | ✓ | present | — |
| `pytest` | — | ✗ | — | Use `python3 -m unittest` (stdlib, no install) |
| `terraform` | Gateway/controller/Boole TF review | ✗ | — | Review-checklist verification now; `terraform validate/plan` at owner-go apply |
| `yamllint`/`shellcheck` | Lint checks | ✗ | — | Python validator is the check; shell via `bash -n` |
| Cloud SQL / Cloud Run / provider keys | Live gateway + test-loop run | ✗ (deferred) | — | Reviewed-not-applied TF + fakes; explicit owner-go checkpoint |

**Missing dependencies with no fallback:**
- Live keys + owner go (Fireworks/Anthropic/OpenAI, Boole Slack app, COST-01 budget) — explicitly deferred per CONTEXT.md, not blocking code delivery.

**Missing dependencies with fallback:**
- `terraform` binary → checklist review now, validate at apply; rootless dry-run if Docker restricted → static assertion fallback.

## Validation Architecture

Test framework: Bash acceptance harness + stdlib unit tests — no new test framework (pytest absent; network installs unproven).

| Property | Value |
|----------|-------|
| Framework | `tests/agents/run.sh` harness + `python3 -m unittest` (stdlib) |
| Config file | none — convention: `tests/agents/checks/*.sh` auto-discovered by `run.sh:41-46` [VERIFIED] |
| Quick run command | `python3 -m unittest discover -s controller` |
| Full suite command | `tests/agents/run.sh` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CP-05 | Loop YAML validates; unknown loop refused | unit + check | `python3 agents/loops/validate.py agents/loops/*.yaml` via `tests/agents/checks/loops.sh` | ❌ Wave 0 |
| CP-02 | Enqueue idempotent; dispatch only registered loops; run log written | unit (fake queue/gateway) | `python3 -m unittest discover -s controller` via `checks/controller.sh` | ❌ Wave 0 |
| CP-03 | Approval parks without process; Slack answer resumes | unit (fake Slack/broker, fake clock) | same suite | ❌ Wave 0 |
| CP-04 | Over-budget refused; kill flags stop within 60s poll | unit (fake ledger) | same suite | ❌ Wave 0 |
| CP-06 | Broker issues only declared creds to per-run 0500 dir; cleanup on end | unit (fake Secret Manager) + shell | same suite + `checks/controller.sh` | ❌ Wave 0 |
| CP-01 | Gateway TF internal-only, DB-wired, per-loop key+budget; config valid YAML | static review checklist | `checks/controller.sh` asserts `INGRESS_TRAFFIC_INTERNAL_ONLY` + `DATABASE_URL` present; live `curl` deferred owner-go | ❌ Wave 0 |
| RT-01 | Runner execs as agent user, fresh rootless container, allowlist enforced | container dry-run (no creds) or static assertion | `checks/runner.sh` | ❌ Wave 0 |
| EGR-03 | Disallowed destination refused + logged from first run | dry-run curl BLOCKED | `checks/runner.sh` | ❌ Wave 0 |
| OPS-01 | Boole identities declared, nothing created | static (grep TF + manifest valid JSON) | `checks/controller.sh` or `checks/loops.sh` | ❌ Wave 0 |
| ACC-09 | Least-privilege IAM blocks; no public invoker; per-run cred dirs | static review | same checks | ❌ Wave 0 |
| COST-01 | Budget placeholder present, owner-go checkpoint | static | plan checkpoint, not code | n/a |

### Sampling Rate
- **Per task commit:** `python3 -m unittest discover -s controller` + `bash -n` on new shell files
- **Per wave merge:** `tests/agents/run.sh` (full harness, appends dated record per ACC-08)
- **Phase gate:** Full suite green before `/gsd-verify-work`; live test-loop run explicitly excluded (owner-go checkpoint)

### Wave 0 Gaps
- [ ] `agents/loops/validate.py` + `agents/loops/testdata/test-loop.yaml` — covers CP-05, EGR-03 schema side
- [ ] `controller/schema.sql` + `controller/dispatcher.py` with fake seams — covers CP-02/03/04
- [ ] `controller/test_dispatcher.py` (stdlib unittest, fakes only) — covers CP-02/03/04, CP-06 interface
- [ ] `agents/host/files/hyprn-credential-broker` + `hyprn-run-runner` — covers CP-06, RT-01
- [ ] `infra/agents/gateway.tf` + `controller.tf` + `boole.tf` (reviewed, not applied) — covers CP-01, OPS-01, ACC-09
- [ ] `tests/agents/checks/loops.sh`, `checks/controller.sh`, `checks/runner.sh` wired into `run.sh` — covers all above

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | 1h GitHub installation tokens; gateway virtual keys per loop; Secret Manager as store |
| V3 Session Management | partial | Parked runs are DB rows with owner-only resume via allowlisted Slack user (ACC-02 pattern) |
| V4 Access Control | yes | Per-secret IAM (cf. `secrets.tf:34-42,65-70` [VERIFIED]); per-run tmpfs dirs; dispatcher registry gate |
| V5 Input Validation | yes | Trigger payloads untrusted — schema-validate envelopes; YAML validated before dispatch |
| V6 Cryptography | yes | No hand-roll: Secret Manager TLS APIs, RS256 via OpenSSL for GH JWT (existing pattern), LiteLLM master key `sk-` prefix |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Trigger payload injects tools/creds | Tampering / Elevation | Authority only from reviewed YAML; allowlist env-translation, never payload interpolation |
| Cross-run secret reuse | Information disclosure | Per-run 0500 dirs, delete on end; container mounts only its run dir |
| Gateway reachable from internet | Information disclosure | `INGRESS_TRAFFIC_INTERNAL_ONLY` + no public invoker; ACC-09 check |
| Budget bypass via direct provider call | Tampering | Containers reach only gateway + allowlist (EGR-03); provider keys gateway-readable only |
| Stale kill flag (run continues >60s) | Denial / Tampering | Poll flags each step + ≤60s timer; dispatcher refuses re-queue when flagged |

## Sources

### Primary (HIGH confidence)
- `docs/specs/agent-fleet.md` §4/§5/§6/§7 — read in full this session (control plane, gateway, tools, credentials)
- `docs/adr/0006-agent-first-operating-model.md` — read in full (O3 decision, design rules, build-or-buy)
- `agents/wake/wake.py:1-147` — read (Socket Mode, envelope-ack, poll loop patterns)
- `agents/host/files/hyprn-agent-github-token` + `hyprn-agent-secrets` — read (token-loader/broker pattern, tmpfs perms)
- `infra/agents/{secrets,iam,network,variables}.tf` — read (per-secret IAM, VPC shape, agent inputs)
- `tests/agents/run.sh:1-62` — read (check harness contract)
- Host tool probes this session: python3 3.11.2, Docker 29.9.0, rootlesskit/slirp4netns present, pytest/terraform absent

### Secondary (MEDIUM confidence)
- [CITED: https://docs.litellm.ai/docs/proxy/virtual_keys] — virtual keys require Postgres + `DATABASE_URL`, master key `sk-` prefix
- [CITED: https://docs.litellm.ai/docs/proxy/users] — budgets unenforced without DB; per-key `max_budget` refuses after crossing
- [CITED: https://docs.fireworks.ai/ecosystem/integrations/litellm] — `fireworks_ai/` prefix + qualified IDs; bare-router pitfall
- [CITED: https://docs.litellm.ai/docs/proxy/configs] — `model_list`/`model_name` vs `litellm_params.model` alias shape
- [CITED: Terraform registry `google_cloud_run_v2_service`] — `INGRESS_TRAFFIC_INTERNAL_ONLY`, Cloud SQL volume block
- [CITED: https://docs.cloud.google.com/run/docs/securing/ingress] — internal ingress setting + Terraform sample

### Tertiary (LOW confidence)
- PyYAML popularity/age figures; Cloud SQL tier sizing; exact `docker run` rootless flag set; Cloud Scheduler interim choice — all [ASSUMED], flagged in Assumptions Log for planner confirmation.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - core pieces verified in-repo/on-host; LiteLLM/Fireworks shapes cited from official docs, not exercised live (keys deferred)
- Architecture: MEDIUM - extends verified in-repo patterns; exact YAML field names and SQL/controller layout are planner-confirmed assumptions
- Pitfalls: HIGH - DB-required-for-budgets, Fireworks naming, and ingress defaults all cited from official docs

**Research date:** 2026-10-13
**Valid until:** 2026-11-12 (stable domain; re-check Fireworks model IDs + LiteLLM image digests at plan time)
