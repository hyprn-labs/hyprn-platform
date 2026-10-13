# Phase 3: Control plane core - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 12 new files (Wave 0 gaps)
**Analogs found:** 10 / 12 (2 greenfield-with-partial-analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `agents/loops/validate.py` | utility (static validator) | file-I/O + transform | `agents/wake/wake.py` (stdlib-only Python, §imports/error style) | role-match |
| `agents/loops/testdata/test-loop.yaml` | config (test fixture) | file-I/O | `tests/agents/checks/*.sh` JSON-shape assertions (no YAML precedent) | partial |
| `controller/schema.sql` | migration/schema | CRUD (DDL) | none in repo (first SQL file); planner uses RESEARCH.md §Code Examples | no-analog |
| `controller/dispatcher.py` | service (queue/dispatch/run-state) | CRUD + request-response | `agents/wake/wake.py` (poll loop, envelope-ack, stdlib urllib/json) | role-match |
| `controller/test_dispatcher.py` | test (stdlib unittest) | batch | none (no `unittest` in repo; closest: `tests/agents/checks/*.sh` `check()` harness) | no-analog |
| `agents/host/files/hyprn-credential-broker` | service (root-owned loader) | file-I/O + request-response | `agents/host/files/hyprn-agent-secrets` | exact |
| `agents/host/files/hyprn-run-runner` | service (run executor) | event-driven + file-I/O | `agents/host/files/hyprn-agent-github-token` (tmpfs handoff) + `agents/host/files/hyprn-idle-stop` (host guard idioms) | role-match |
| `infra/agents/gateway.tf` | config (Terraform) | request-response | `infra/agents/network.tf` + `infra/agents/wake.tf` | role-match |
| `infra/agents/controller.tf` | config (Terraform) | event-driven | `infra/agents/wake.tf` | exact |
| `infra/agents/boole.tf` | config (Terraform) | CRUD | `infra/agents/secrets.tf` | exact |
| `tests/agents/checks/loops.sh` | test (shell check) | batch | `tests/agents/checks/policy.sh` | exact |
| `tests/agents/checks/controller.sh` + `runner.sh` | test (shell checks) | batch | `tests/agents/checks/egress.sh` (+ `github.sh` live/static split) | exact |

All analog paths verified git-tracked via `git ls-files` (2026-10-13). `agents/loops/` and `controller/` confirmed greenfield (do not exist).

## Pattern Assignments

### `agents/loops/validate.py` (utility, file-I/O + transform)

**Analog:** `agents/wake/wake.py` — the only Python service in the repo; sets the stdlib-only convention.

**Imports pattern** (`agents/wake/wake.py` lines 12-20):
```python
import base64
import json
import sys
import threading
import time
import urllib.error
import urllib.request

import websocket  # Debian package python3-websocket
```
Copy: stdlib imports first, one-per-line, third-party (here: `yaml` for PyYAML, Debian/pinned) in a separate group with a comment naming the source. Module docstring at top stating ADR/phase + dependency list (wake.py lines 1-11).

**Core pattern — fail-fast validation with `log()` to stderr** (wake.py lines 32-33, 102-114):
```python
def log(*parts):
    print("hyprn-wake:", *parts, file=sys.stderr, flush=True)
```
Validator equivalent: `print("hyprn-loops:", *parts, file=sys.stderr)`; per-file errors prefixed with path; `sys.exit(1)` on any failure so `loops.sh` inherits the exit code. Single `validate(path)` function returning bool + `main()` iterating `sys.argv[1:]` (mirrors `main()` poll-loop shape at wake.py lines 129-143, minus the infinite loop).

**Error handling pattern** (wake.py lines 103-106, 135-137):
```python
try:
    envelope = json.loads(raw)
except ValueError:
    return
```
Copy: catch narrow exceptions (`ValueError` for YAML/JSON parse, `KeyError` for missing fields, `AssertionError` for schema violations) per file and continue to the next file — never let one bad loop abort validation of the rest. Same narrow-tuple style as wake.py line 135: `except (urllib.error.URLError, KeyError, ValueError)`.

**No-analog gaps (use RESEARCH.md):** YAML parsing itself (`yaml.safe_load`, REQUIRED-field set, `egress_allowlist` non-empty assertion, autonomy-level enum) has no in-repo precedent — copy RESEARCH.md "Loop registry validation entry point" verbatim and confirm field names against spec §5/§9 (Assumption A1).

---

### `agents/loops/testdata/test-loop.yaml` (config fixture, file-I/O)

**Analog (partial):** static JSON fixtures validated by checks — `agents/github/main-ruleset.json` asserted via `tests/agents/checks/github.sh` lines 18-32 (`python3 -m json.tool`, `jq -e` shape probes).

**Pattern to copy:** fixture file lives next to its validator (`agents/loops/testdata/`, mirroring `agents/github/main-ruleset.json` next to its check); every field the validator requires must be present so `validate.py testdata/test-loop.yaml` is green on day one. Shape comes from RESEARCH.md Pattern 1 (registry-gated dispatch example: `name/owner/trigger/steps/agent_steps/tools/autonomy/budget/egress_allowlist/runtime/eval_set/promotion_rule`) — no in-repo YAML loop exists to copy keys from.

---

### `controller/schema.sql` (migration/DDL, CRUD)

**Analog:** none — first `.sql` file in the repo (confirmed: no `*.sql` precedent; `infra/agents/*.tf` holds no DDL).

**Planner uses RESEARCH.md** "Idempotent enqueue (schema excerpt)": `runs(id, loop, state, idempotency_key UNIQUE, budget_usd, cost_usd, kill_* flags, created_at)` + `approvals(run_id REFERENCES runs(id), question, answer, decided_at)`. Keep SQLite-now/Cloud-SQL-at-apply portability: only types/functions valid in both (`TEXT/REAL/INTEGER`, `datetime('now')`), no Postgres-only DDL.

---

### `controller/dispatcher.py` (service, CRUD + request-response)

**Analog:** `agents/wake/wake.py` (full file, 147 lines).

**Imports + config pattern** (wake.py lines 22-29):
```python
CONFIG = json.load(open("/etc/hyprn-agents/wake.json", encoding="utf-8"))
MD = "http://169.254.169.254/computeMetadata/v1"
...
POLL_SECONDS = 15
```
Copy: module constants for paths + poll interval (`POLL_SECONDS = 15` → dispatcher kill-flag poll `<= 60` per CP-04); config load with explicit `encoding="utf-8"`.

**Core pattern — poll loop with guarded iteration** (wake.py lines 129-143):
```python
def main():
    allowed = set(json.loads(secret("agents-slack-allowed-users")))
    wakers = [Waker(agent, allowed) for agent in CONFIG["agents"]]
    while True:
        try:
            status = gcp(INSTANCE).get("status", "")
        except (urllib.error.URLError, KeyError, ValueError) as error:
            log("status check failed:", error)
            status = ""
        for waker in wakers:
            if status in STOPPED:
                waker.connect()
            elif status:
                waker.disconnect()
        time.sleep(POLL_SECONDS)
```
Copy for the dispatcher poll cycle: load registry → dequeue one row → budget/kill/registry gates → dispatch-or-park; wrap the per-iteration I/O in the same narrow `try/except` + `log()` + continue shape. Fake seams (fake queue, fake gateway, fake broker per CONTEXT.md) enter as constructor-injected callables on a `Dispatcher` class mirroring the `Waker` class shape (wake.py lines 75-82: `__init__` stores agent/allowed/secrets/handles).

**Envelope-ack + allowlist-gate pattern** (wake.py lines 102-114):
```python
def on_envelope(self, ws, raw):
    try:
        envelope = json.loads(raw)
    except ValueError:
        return
    if envelope.get("envelope_id"):
        ws.send(json.dumps({"envelope_id": envelope["envelope_id"]}))
    ...
    if not (is_dm or event.get("type") == "app_mention") or event.get("user") not in self.allowed:
        return
```
Copy: ack-then-gate ordering — record idempotency key (UNIQUE insert; duplicate = already-queued, return) BEFORE any dispatch; refuse unknown loop names against the registry BEFORE touching credentials/compute (RESEARCH.md Pattern 1; ADR-0006 rule 3 — payloads untrusted).

**HTTP helper pattern** (wake.py lines 36-53): `http()` via `urllib.request` + `gcp_token()` caching with 60s early-refresh. Copy for any gateway/Slack calls in the dispatcher; no new HTTP deps.

---

### `controller/test_dispatcher.py` (test, batch)

**Analog:** none for `unittest` — repo has zero `unittest`/`sqlite3` usage (grep 2026-10-13: only `python3 -m json.tool` in checks). Closest harness precedent is the shell `check()` idiom (see Shared Patterns §Checks).

**Pattern to establish (planner copies RESEARCH.md Validation Architecture):**
- Stdlib only: `import unittest, sqlite3` — `pytest` is NOT installed (RESEARCH.md Environment Availability); run via `python3 -m unittest discover -s controller`.
- Fakes only, no network: fake queue (in-memory list), fake gateway (spend-ledger dict), fake broker (fixture dir), fake clock for parked-approval timing (CP-03) and kill-flag polling (CP-04).
- One `TestCase` per requirement: `TestIdempotentEnqueue` (CP-02), `TestRegistryGate` (CP-05), `TestParkedApproval` (CP-03), `TestBudgetKill` (CP-04), `TestBrokerInterface` (CP-06).
- Per-task-commit command: `python3 -m unittest discover -s controller` (RESEARCH.md Sampling Rate).

---

### `agents/host/files/hyprn-credential-broker` (service, file-I/O + request-response)

**Analog:** `agents/host/files/hyprn-agent-secrets` (42 lines — read fully, copy structure line-for-line).

**Header + safety pattern** (hyprn-agent-secrets lines 1-9):
```bash
#!/usr/bin/env bash
# Loads one agent's runtime secrets from Secret Manager with the VM identity and
# writes them to tmpfs, readable only by that agent (ADR-0001 sections 4 and 6).
# Run as root by hyprn-agent-secrets@<agent>.service. Missing secrets are not
# fatal: the agent session then starts without its Slack channel.
set -euo pipefail
AGENT="$1"
PROJECT="${PROJECT:-hyprn-agents}"
MD="http://169.254.169.254/computeMetadata/v1"
```
Copy: purpose comment citing the ADR, `set -euo pipefail`, `AGENT="$1"`, `PROJECT` default, metadata-base `MD`. Broker usage becomes `hyprn-credential-broker <agent> <run-id> <loop.yaml>`.

**Fetch + missing-tolerance pattern** (hyprn-agent-secrets lines 11-26):
```bash
token=$(curl -sf -H 'Metadata-Flavor: Google' "$MD/instance/service-accounts/default/token" | jq -r .access_token)
fetch() {
  curl -sf -H "Authorization: Bearer $token" \
    "https://secretmanager.googleapis.com/v1/projects/$PROJECT/secrets/$1/versions/latest:access" \
    | jq -r .payload.data | base64 -d | tr -d '\r\n'
}
```
Copy the `fetch()` helper verbatim; broker reads ONLY loop-declared secret names (parsed from `<loop.yaml>`) — never a fixed list. Missing undeclared secrets are refused; missing declared-but-absent secrets warn to stderr and continue (same tolerance idiom as lines 18-26).

**Per-run tmpfs handoff pattern** (hyprn-agent-secrets lines 28-41 + hyprn-agent-github-token lines 34-42):
```bash
dir="/run/hyprn-agents/secrets/$AGENT"
install -d -m 0711 /run/hyprn-agents/secrets
install -d -m 0500 -o "$AGENT" -g "$AGENT" "$dir"
...
umask 0377
tmp="$dir/.slack.env.tmp"
rm -f "$tmp"
printf 'SLACK_APP_TOKEN=%s\nSLACK_BOT_TOKEN=%s\n' "$app" "$bot" > "$tmp"
chown "$AGENT:$AGENT" "$tmp"
mv "$tmp" "$dir/slack.env"
```
Copy exactly, with `$dir` scoped per run: `/run/hyprn-agents/runs/<run-id>/` mode 0500 owned by the agent user; write-temp + `chown` + atomic `mv`; broker deletes the dir on run end (CP-06, Pitfall 4). GitHub installation-token minting (1h) reuses the `hyprn-agent-github-token` lines 20-32 flow (RS256 JWT via `openssl`, `unset key` immediately after signing) where the loop declares a GitHub credential.

---

### `agents/host/files/hyprn-run-runner` (service, event-driven + file-I/O)

**Analog:** `agents/host/files/hyprn-agent-github-token` (tmpfs handoff tail) + `agents/host/files/hyprn-idle-stop` (host guard idioms).

**Guard-clause idiom** (hyprn-idle-stop lines 8-10):
```bash
up=$(cut -d. -f1 /proc/uptime)
[ "$up" -ge $((IDLE_MINUTES * 60)) ] || exit 0          # grace period after boot
[ -e /run/hyprn-agents/hold ] && exit 0                 # manual hold
```
Copy: early-exit guards at the top of the runner — kill-flag files set (`kill_loop/kill_agent/kill_fleet`), no pending runs, `docker ps` hold-file registration so idle-stop sees run containers as activity (Pitfall 5; spec §4: running containers block idle-stop).

**Container exec shape** (no exact in-repo precedent; closest live-container probe is `tests/agents/checks/egress.sh` lines 36-37):
```bash
check "$name: container direct outbound drops" "! run 'docker run --rm --env NO_PROXY=* --env no_proxy=* curlimages/curl -sf -m 10 -o /dev/null https://example.com'"
check "$name: container same destination succeeds through the proxy" "run 'docker run --rm --env https_proxy=http://host.containers.internal:$port --env http_proxy=http://host.containers.internal:$port curlimages/curl -sf -m 15 -o /dev/null https://example.com'"
```
Copy: `docker run --rm`, `--env` proxy wiring via `host.containers.internal`, per-agent execution via `runuser -l "$name" -c ...` (egress.sh lines 29, 79). Runner additions from RESEARCH.md: `--read-only`, `--env-file /run/hyprn-agents/runs/<run-id>/env` (only that run's dir mounted), `ALLOWED_HOSTS` translated from the loop's `egress_allowlist` — never from trigger payload (Threat: trigger-payload injection). EGR-03 dry-run proves disallowed curl → BLOCKED.

---

### `infra/agents/gateway.tf` (Terraform config, request-response)

**Analog:** `infra/agents/network.tf` (53 lines) + `infra/agents/wake.tf` (91 lines).

**Resource shape** (network.tf lines 1-13, wake.tf lines 46-90):
```hcl
resource "google_compute_network" "agents" {
  name                    = "hyprn-agents-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}
```
```hcl
  labels = {
    component  = "agents"
    role       = "wake"
    managed_by = "terraform"
  }
```
Copy: aligned `=` style, every resource carries `labels { component = "agents", managed_by = "terraform" }` (+ `role`/`agent` where applicable, cf. secrets.tf lines 27-31). Gateway adds `google_cloud_run_v2_service` with `ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"` (Pitfall 3 — default is public), `DATABASE_URL` from Secret Manager `value_source.secret_key_ref`, and Cloud SQL volume block; exact block from RESEARCH.md "Cloud Run + Cloud SQL Terraform shape" (cited from registry `google_cloud_run_v2_service`). Provider version comes from `infra/agents/versions.tf` (`hashicorp/google ~> 8.6`); backend stays `gcs` bucket `hyprn-agents-tfstate`.

---

### `infra/agents/controller.tf` (Terraform config, event-driven)

**Analog:** `infra/agents/wake.tf` — exact match (always-on scheduler VM + minimal IAM).

**IAM-least-privilege pattern** (wake.tf lines 5-38):
```hcl
resource "google_service_account" "wake" {
  account_id   = "hyprn-agents-wake"
  display_name = "hyprn agents wake"
  description  = "Identity of the wake VM; may only get, start and stop the agent host."
}

resource "google_project_iam_member" "wake" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.wake.email}"
}

resource "google_project_iam_custom_role" "host_power" {
  ...
  permissions = [
    "compute.instances.get",
    "compute.instances.start",
    "compute.instances.stop",
  ]
}
```
Copy: dedicated service account per component, stock roles via `for_each = toset([...])`, bespoke powers as a custom role with enumerated permissions granted on the narrowest resource. Controller identity gets run-state-DB client + queue-read rights only (ACC-09). VM block copies wake.tf lines 46-90 (pinned `var.host_image`, `shielded_instance_config`, `enable-oslogin`/`block-project-ssh-keys` metadata, `cloud-platform` scope). File header comment cites the ADR/phase like wake.tf line 1-3. Reviewed-NOT-applied; no `terraform apply` in phase execution.

---

### `infra/agents/boole.tf` (Terraform config, CRUD)

**Analog:** `infra/agents/secrets.tf` (99 lines — exact match for declared-not-created identities).

**Per-agent secret + per-reader IAM pattern** (secrets.tf lines 8-42):
```hcl
locals {
  agent_slack_secrets = {
    for pair in setproduct(var.slack_agents, ["slack-app-token", "slack-bot-token"]) :
    "${pair[0]}-agent-${pair[1]}" => pair[0]
  }
}

resource "google_secret_manager_secret" "agent_slack" {
  for_each  = local.agent_slack_secrets
  secret_id = each.key

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    agent      = each.value
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_iam_member" "agent_slack" {
  for_each = {
    for pair in setproduct(keys(local.agent_slack_secrets), ["host", "wake"]) :
    "${pair[0]}-${pair[1]}" => { secret = pair[0], reader = pair[1] }
  }
  secret_id = google_secret_manager_secret.agent_slack[each.value.secret].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.reader == "host" ? google_service_account.host.email : google_service_account.wake.email}"
}
```
Copy: `setproduct` locals for `<agent>-<purpose>` secret IDs, `user_managed` replication pinned to `var.region`, per-secret `secretAccessor` grants to named service accounts only (never project-wide — iam.tf lines 1-2). Boole entries: `boole-agent-slack-app-token/bot-token`, gateway virtual-key placeholder, `boole-agent-github-app-key` following the lines 46-70 block (host-only reader). Values are owner-supplied from the password manager, never in TF (secrets.tf lines 1-4). Agent list input follows `infra/agents/variables.tf` lines 51-61 (`var.agents`/`var.slack_agents` with `["ada", "codd"]` defaults); Linux user `boole` declared in host provisioning alongside. Vendor-side objects are owner checklists in the runbook, not TF resources.

---

### `tests/agents/checks/loops.sh` + `controller.sh` + `runner.sh` (shell checks, batch)

**Analog:** `tests/agents/checks/policy.sh` (static checks, 35 lines) for `loops.sh`/`controller.sh`; `tests/agents/checks/egress.sh` (live host checks, 42 lines) for `runner.sh`; `tests/agents/checks/github.sh` (static+live split with SKIP, 84 lines) for the combined pattern.

**Check-script boilerplate** (policy.sh lines 1-15, identical in egress.sh/github.sh):
```bash
#!/usr/bin/env bash
# <Domain> checks (<REQ-IDs>). Static content assertions run anywhere;
# host-executed portions run as root on the agent host.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
...
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
...
exit $fail
```
Copy verbatim: `set -uo pipefail` (no `-e` — a failing domain never masks later ones), `HERE`/`REPO_ROOT` resolution, `fail` accumulator, `check "<name>" "<eval-string>"`, `exit $fail`. Auto-discovery needs no registration: `tests/agents/run.sh` lines 41-46 picks up every executable `checks/*.sh`; just `chmod +x`.

**Static-assertion style** (policy.sh lines 17-32):
```bash
check "policy file exists and is valid JSON" "python3 -m json.tool '$POLICY'"
check "deny covers merge family" "jq -e '[.permissions.deny[] | select(test(\"gh pr merge\"))] | length >= 1' '$POLICY'"
```
Copy for `loops.sh` (validator green on `agents/loops/*.yaml` + testdata; `egress_allowlist` non-empty grep) and `controller.sh` (`python3 -m unittest discover -s controller`; `schema.sql` loads under `sqlite3`; TF greps: `INGRESS_TRAFFIC_INTERNAL_ONLY` + `DATABASE_URL` present — Pitfalls 1/3; `terraform` absent so `bash -n`/grep review only).

**Live/static split with SKIP** (github.sh lines 58-68):
```bash
skip() { echo "SKIP $1 ($2)"; }
...
if [ -z "${GH01_PROBE_PR:-}" ]; then
  skip "live: probe draft PR is bot-authored and a draft" "no probe PR yet (gated on Phase 1 green run)"
```
Copy for `runner.sh`: container dry-run (egress.sh lines 36-37 shape) when `docker` + rootless present; `SKIP (static assertion only — <reason>)` otherwise (RESEARCH.md fallback). Off-host user-loop pattern (github.sh lines 74-82: `id "$name"` guard → skip) applies to any check needing the `boole` user.

## Shared Patterns

### Shell-check harness contract
**Source:** `tests/agents/run.sh` lines 20-46 + `tests/agents/checks/policy.sh` lines 8-15
**Apply to:** `loops.sh`, `controller.sh`, `runner.sh`
```bash
set -uo pipefail   # never -e inside a check
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
# ...
exit $fail
```
`run.sh` runs `host-checks.sh` first, then every executable `checks/*.sh` in a guarded `run_one` (status recorded, never masks later domains), and appends a dated `runbooks/agents/checks-<DATE>.md` record (ACC-08).

### Secret handling (never in repo)
**Source:** `infra/agents/secrets.tf` lines 1-4 + `agents/host/files/hyprn-agent-secrets` lines 28-41
**Apply to:** broker, runner, all three `.tf` files, all checks
```hcl
# Secret containers per agent; values are added by the owner from the password
# manager (see runbooks/agents/slack.md), never through Terraform or Git.
```
```bash
install -d -m 0500 -o "$AGENT" -g "$AGENT" "$dir"
umask 0377
# ... write temp, chown "$AGENT:$AGENT", atomic mv ...
```
Checks assert shapes/presence only (`jq`, `grep`); never print values — shape-only inspection per AGENTS.md.

### Python stdlib-only style
**Source:** `agents/wake/wake.py` lines 1-33
**Apply to:** `validate.py`, `dispatcher.py`, `test_dispatcher.py`
Module docstring with ADR reference + `Dependencies:` line; stdlib-first imports; `log()` to stderr with component prefix; narrow `except (..., KeyError, ValueError)` tuples; `POLL_SECONDS`-style named constants. New third-party surface is exactly one package: PyYAML (pinned at plan time), plus the LiteLLM container image (digest-pinned, not a pip dep).

### Terraform file shape
**Source:** `infra/agents/wake.tf` + `infra/agents/secrets.tf` + `infra/agents/variables.tf` lines 51-61 + `infra/agents/versions.tf`
**Apply to:** `gateway.tf`, `controller.tf`, `boole.tf`
Header comment (purpose + ADR ref); `for_each = toset([...])` for role lists; `setproduct` locals for per-agent secrets; `user_managed` replication in `var.region`; `labels { component = "agents", managed_by = "terraform" }` on everything; agent inputs via `var.agents`/`var.slack_agents`; provider/backend from `versions.tf` unchanged (`google ~> 8.6`, `gcs` backend `hyprn-agents-tfstate`). All three files reviewed-NOT-applied; owner-go checkpoint before any `terraform validate/plan/apply` (`terraform` not on PATH — RESEARCH.md Environment Availability).

### Least privilege (ACC-09)
**Source:** `infra/agents/iam.tf` lines 1-18 + `infra/agents/secrets.tf` lines 34-42, 65-70
**Apply to:** controller/broker/runner identities + `boole.tf`
Per-secret `secretAccessor` to named service accounts; custom roles with enumerated permissions on the narrowest resource (wake.tf `agentHostPower` model); per-run tmpfs dirs `0500` agent-owned; no public invoker on the gateway.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `controller/schema.sql` | migration | CRUD (DDL) | First SQL file in repo; use RESEARCH.md idempotent-enqueue excerpt |
| `controller/test_dispatcher.py` | test | batch | Zero `unittest`/`sqlite3` usage in repo; establish stdlib-`unittest` + fakes pattern per RESEARCH.md Validation Architecture |

## Metadata

**Analog search scope:** `agents/wake/`, `agents/host/files/`, `infra/agents/`, `tests/agents/checks/`, `tests/agents/run.sh` (+ grep for `unittest|sqlite3` across `*.py/*.sh`)
**Files scanned:** 14 tracked files read or globbed; 6 read in full (wake.py, hyprn-agent-secrets, hyprn-agent-github-token, hyprn-idle-stop, secrets.tf, wake.tf), 6 read for shape (network.tf, iam.tf, variables.tf, versions.tf, run.sh, policy/github/egress.sh)
**Pattern extraction date:** 2026-10-13
