# Phase 4: Boole and the meeting loop - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 10 (8 new files + test + runbook from Wave 0 gaps)
**Analogs found:** 9 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `controller/poll_notion.py` | service (trigger/poller) | request-response (poll → enqueue) | `controller/dispatcher.py` | role-match |
| `controller/test_poll_notion.py` | test | batch (unit) | `controller/test_dispatcher.py` | exact |
| `agents/loops/meeting.yaml` | config (registry entry) | event-driven (poll trigger) | `agents/loops/testdata/test-loop.yaml` | exact |
| `agents/loops/meeting/prompts.md` + `skills/` | config (prompt rubric) | transform (extract) | *(none — new pattern)* | no-analog |
| `agents/loops/testdata/meeting-pages/{new,updated,malformed}.json` | test (fixture) | file-I/O | `agents/loops/testdata/test-loop.yaml` | role-match |
| `agents/host/files/hyprn-meeting-workflow` | service (workflow script) | request-response (fetch→extract→propose→park) | `agents/host/files/hyprn-run-runner` + `hyprn-credential-broker` | role-match |
| `infra/agents/boole-notion.tf` | config (terraform) | batch (declared-not-created) | `infra/agents/boole.tf` (+ `secrets.tf`) | exact |
| `tests/agents/checks/meeting.sh` | test (check script) | batch | `tests/agents/checks/loops.sh` (+ `controller.sh`) | exact |
| `tests/agents/checks/isolation.sh` | test (check script) | batch | `tests/agents/checks/accounts.sh` (+ `tests/agents/host-checks.sh`) | role-match |
| `runbooks/agents/meeting-loop-go.md` | config (owner checklist) | batch (manual) | `runbooks/agents/control-plane-go.md` | exact |

## Pattern Assignments

### `controller/poll_notion.py` (service, poll → enqueue)

**Analog:** `controller/dispatcher.py`

**Imports/header pattern** (`controller/dispatcher.py` lines 1-24) — stdlib-only, untrusted-envelope docstring, `POLL_SECONDS` constant beside module:
```python
#!/usr/bin/env python3
"""Fleet controller dispatcher (Phase 3, CP-02/CP-03/CP-04/CP-05).

Trigger envelopes are untrusted (ADR-0006 rule 3): the idempotency key is
recorded BEFORE any dispatch, and unknown loop names are refused BEFORE
any credential or compute is touched. ...
Dependencies: Python 3 standard library only (sqlite3).
"""
import sqlite3
import sys
import time


POLL_SECONDS = 15
```
Poller copies this shape: `urllib`/`json` stdlib imports only, module docstring stating the settled seam (5-min poll, one envelope per new page id, Granola leg out of scope), `POLL_INTERVAL_SECONDS = 300` constant.

**Core enqueue pattern** (`controller/dispatcher.py` lines 61-86) — poller calls, never reimplements:
```python
def enqueue(self, envelope):
    """Insert one run for an envelope. Duplicate keys enqueue once."""
    try:
        key = envelope["idempotency_key"]
        loop = envelope["loop"]
    ...
    if loop not in self.registry():
        log("refusing unknown loop:", loop)
        return None
    run_id = "run-%s" % key
    ...
    except sqlite3.IntegrityError:
        return run_id  # duplicate envelope: already queued
```
Poller builds `{"loop": "meeting", "idempotency_key": "notion-page-<page-id>", "budget_usd": 30.0}` per page, persists cursor AFTER successful enqueue, uses `--fixture` dir mode for tests.

**Cost pattern** (`controller/dispatcher.py` lines 135-140): `record_cost(run_id, amount)` accumulates `cost_usd` — poller/workflow reuse it; no new ledger.

---

### `controller/test_poll_notion.py` (test, unit)

**Analog:** `controller/test_dispatcher.py`

**Harness pattern** (`controller/test_dispatcher.py` lines 1-28) — stdlib unittest, fakes only, `sys.path` insert, `fresh_db()` + `registry_of()` + `envelope()` helpers:
```python
"""Dispatcher unit tests (Phase 3, tracer slice). Stdlib unittest, fakes
only: no network, no cloud, no keys. Run: python3 -m unittest discover -s controller."""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Dispatcher  # noqa: E402

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def fresh_db():
    connection = sqlite3.connect(":memory:")
    with open(SCHEMA, encoding="utf-8") as handle:
        connection.executescript(handle.read())
    return connection


def registry_of(*names):
    return lambda: {name: {"name": name} for name in names}


def envelope(loop="meeting-test", key="env-1", budget=30.0):
    return {"idempotency_key": key, "loop": loop, "budget_usd": budget}
```

**Dedupe test pattern** (lines 31-38) — copy for cursor/idempotency cases:
```python
class TestIdempotentEnqueue(unittest.TestCase):
    def test_same_envelope_twice_enqueues_once(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        first = disp.enqueue(envelope())
        second = disp.enqueue(envelope())
        self.assertEqual(first, second)
```
New tests: same page twice → one row; unknown loop refused (lines 47-52); parked-approval survives clock advance + stranger ignored (lines 76-100, `FakeClock` lines 65-73); cost accumulates 1.5+2.5=4.0 (lines 137-144). Poller tests inject a fake Notion query callable (no network, no token).

---

### `agents/loops/meeting.yaml` (config, poll trigger)

**Analog:** `agents/loops/testdata/test-loop.yaml` (full 33-line reference; copy field-for-field, rename `meeting-test` → `meeting`)

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

**Validator contract** (`agents/loops/validate.py` lines 16-20, 40-43): REQUIRED set + non-empty allowlist + A-levels only:
```python
REQUIRED = {"name", "owner", "trigger", "steps", "tools", "autonomy",
            "budget", "egress_allowlist", "runtime", "eval_set",
            "promotion_rule"}
...
assert doc["egress_allowlist"], "EGR-03 forbids empty allowlist"
...
assert level in AUTONOMY_LEVELS, "bad level %r for %s" % (level, action)
```
Meeting loop keeps `interval: 5m`, `budget 30 USD / 30d`, `notion-write: A1`, `agent_user: boole`, no Granola tool/secret anywhere.

---

### `agents/loops/meeting/prompts.md` + `skills/` (config, extraction rubric)

**Analog:** none in codebase (first judgment-step prompt; `agents/loops/` contains only `validate.py` + `testdata/`).

Planner uses RESEARCH.md Pattern 3 + Pitfall 5: pin a JSON contract `{decisions[], actions[{text, owner, due}], open_questions[], patch{properties}}` with a "quote the source line" rule per item; payload-is-data boundary (ADR-0006 rule 3); malformed page degrades to propose-nothing + Slack note. This file is the Phase 5 eval seed.

---

### `agents/loops/testdata/meeting-pages/*.json` (test fixtures)

**Analog:** `agents/loops/testdata/test-loop.yaml` — the fixture convention: static files under `agents/loops/testdata/` consumed by validator + checks (`tests/agents/checks/loops.sh` lines 9, 16-21 globs `agents/loops/*.yaml` + `testdata/*.yaml` and validates every file).

New: 3 fake Notion pages (`new.json`, `updated.json`, `malformed.json`) read by the poller in `--fixture` mode (dir scan instead of API); no credentials, no network. `malformed.json` proves graceful degrade.

---

### `agents/host/files/hyprn-meeting-workflow` (service, pinned workflow)

**Analog:** `agents/host/files/hyprn-run-runner` (execution shape) + `agents/host/files/hyprn-credential-broker` (credential shape)

**Runner shape** (`hyprn-run-runner` lines 1-13, 20-28, 42-49) — pinned script, root-run, kill guards, idle-stop hold, allowlist-from-YAML-only, read-only `--rm` container:
```bash
#!/usr/bin/env bash
# Run runner (Phase 3, RT-01 + EGR-03): executes one pending run ...
# hyprn-run-runner <agent> <run-id> <loop.yaml>. Run as root. ...
set -euo pipefail
...
# Early-exit guards: kill flags set, or no pending run dir.
[ -e "/run/hyprn-agents/kill_fleet" ] && exit 0                 # fleet kill flag
[ -e "/run/hyprn-agents/kill_agent_$AGENT" ] && exit 0          # agent kill flag
[ -d "$RUN_DIR" ] || exit 0                                    # no pending run

# Register a hold so hyprn-idle-stop treats run containers as activity:
touch /run/hyprn-agents/hold
trap 'hyprn-credential-broker --cleanup "$RUN_ID"; rm -f /run/hyprn-agents/hold' EXIT
...
runuser -l "$AGENT" -c "docker run --rm --read-only --network=hyprn-run \
  ...
  -v '$RUN_DIR:/run/secrets:ro' \
  ghcr.io/hyprn/runner:latest /workflow/run.sh" </dev/null
```

**Credential shape** (`hyprn-credential-broker` lines 68-85, 91-99) — declared-names-only from the reviewed loop file, temp+chown+move, `unset` key material:
```bash
# Declared secret names come ONLY from the reviewed loop file — never from
# trigger payload (ADR-0006 rule 3). Undeclared secrets are refused.
...
for name in $declared; do
  if value=$(fetch "$name") && [ -n "$value" ]; then
    umask 0377
    tmp="$dir/.$(basename "$name").tmp"
    rm -f "$tmp"
    printf '%s\n' "$value" > "$tmp"
    chown "$AGENT:$AGENT" "$tmp"
    mv "$tmp" "$dir/$(basename "$name")"
    unset value
```
Workflow copies the header/usage/`set -euo pipefail` conventions and implements fetch→extract→propose→`park`→(owner yes)→PATCH→`record_cost`, exiting after parking (never sleep-with-container). Extend the broker's tool→secret map only if new `notion-*`/`slack-post` names are needed (current map covers `github` + `slack-post`, lines 80-84).

**Park/resume reuse** (`controller/dispatcher.py` lines 107-128): `park` holds a DB row, `resume` requires `sender == owner` — workflow never invents its own approval path.

---

### `infra/agents/boole-notion.tf` (config, declared-not-created)

**Analog:** `infra/agents/boole.tf` (Boole secret containers) + `infra/agents/secrets.tf` (per-agent pattern)

**Declaration pattern** (`infra/agents/boole.tf` lines 1-34) — locals map + `for_each` secret + host-only accessor, values never in Terraform:
```hcl
# Boole runtime identities (Phase 3, OPS-01 + ACC-09): secret containers
# plus key blocks, declared NOT created. Values are added by the owner from
# the password manager (see runbooks/agents/control-plane-go.md), never
# through Terraform or Git. ...
locals {
  boole_secrets = {
    "boole-agent-slack-app-token" = "boole"
    "boole-agent-slack-bot-token" = "boole"
    "boole-agent-gateway-key"     = "boole"
  }
}

resource "google_secret_manager_secret" "boole" {
  for_each  = local.boole_secrets
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

resource "google_secret_manager_secret_iam_member" "boole" {
  for_each  = google_secret_manager_secret.boole
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.host.email}"
}
```
New file adds the Notion token container (e.g. `boole-agent-notion-token`) + Workspace-user comment in the same shape; vendor-side objects (Workspace user, integration share) stay owner-checklist items in the go-runbook, not resources. `secrets.tf` lines 6-13 show the `setproduct`-based per-agent generalization if more agents follow.

---

### `tests/agents/checks/meeting.sh` (test, check script)

**Analog:** `tests/agents/checks/loops.sh` (registry checks) + `tests/agents/checks/controller.sh` (dispatcher checks)

**Harness pattern** (`loops.sh` lines 1-12; `controller.sh` lines 1-12) — `set -uo pipefail`, `HERE`/`REPO_ROOT` resolution, `check`/`skip` helpers, `fail` accumulator:
```bash
#!/usr/bin/env bash
# Loop-registry checks (CP-05, EGR-03). Static content assertions run anywhere;
# host-executed portions run as root on the agent host.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
VALIDATOR="$REPO_ROOT/agents/loops/validate.py"
FIXTURE="$REPO_ROOT/agents/loops/testdata/test-loop.yaml"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
```

**Assertion style** (`loops.sh` lines 14, 24-26, 36-37; `controller.sh` lines 14-19) — validator-over-every-file + content greps + negative probe:
```bash
check "validator exits 0 on the test fixture" "python3 '$VALIDATOR' '$FIXTURE'"
check "fixture autonomy uses A-levels only" "python3 -c \"import yaml; assert set(yaml.safe_load(open('$FIXTURE'))['autonomy'].values()) <= {'A0','A1','A2','A3'}\""
check "negative probe: bad autonomy level is rejected" "! python3 '$VALIDATOR' '$BAD'"
check "controller unit suite is green" "python3 -m unittest discover -s '$REPO_ROOT/controller'"
check "dispatcher carries the parked-approval path" "grep -q 'def park' '$DISPATCHER' && grep -q 'def resume' '$DISPATCHER'"
```
New `meeting.sh` asserts: validator green on `meeting.yaml`; `notion-write: A1` present; no `xox|ntn_|secret_` values in declarations (OPS-02); poller fixture-mode emits one envelope per new page; `record_cost` path covered. Auto-discovered by `tests/agents/run.sh` lines 41-46 (no harness change; `run.sh` appends dated record to `runbooks/agents/`, lines 48-62).

---

### `tests/agents/checks/isolation.sh` (test, ACC-07)

**Analog:** `tests/agents/checks/accounts.sh` + `tests/agents/host-checks.sh` lines 38-46

**Per-agent loop pattern** (`host-checks.sh` lines 21-47) — iterate `agents.txt`, `runuser` probes, cross-home unreadability:
```bash
while read -r name uid harness _; do
  run() { runuser -l "$name" -c "$1" </dev/null; }
  check "$name: home is private" "[ \"\$(stat -c %a /home/$name)\" = 700 ]"
  check "$name: no sudo or docker group" "! id -nG $name | grep -qwE 'sudo|docker|adm'"
  ...
  check "$name: Slack tokens private to the agent" "[ ! -e /run/hyprn-agents/secrets/$name/slack.env ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/secrets/$name/slack.env)\" = $name:400 ]"
  check "$name: GitHub token private to the agent" "[ ! -e /run/hyprn-agents/secrets/$name/github-token ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/secrets/$name/github-token)\" = $name:400 ]"
  ...
  for other in /home/*; do
    [ "$other" = "/home/$name" ] && continue
    check "$name: cannot read $other" "! run 'ls $other'"
  done
done < <(grep -vE '^\s*(#|$)' "$AGENTS")
```

**Static-assertion style** (`accounts.sh` lines 21-24) — no-creds-on-host greps that run anywhere:
```bash
check "no user cloud credentials on host" "! ls /home/*/.[a-z]*cloud* /home/*/.config/gcloud/credentials.db 2>/dev/null | grep -q . && ! grep -rlsq '\"client_id\".*apps.googleusercontent' /home /root /etc 2>/dev/null"
check "no private-key files on host" "! grep -rlsq '\"private_key\"' /home /root /etc"
check "no credential files under agent homes" "! find /home/ada /home/codd -name '*credential*' -o -name 'application_default_credentials.json' 2>/dev/null | grep -q ."
```
New `isolation.sh` extends both to Boole's declared identities (Linux user, secret names, container user, bot tokens): static assertions (secret-name grep shows no cross-agent reads; homes 0700; `agent:400` token files) run anywhere, live `runuser` cross-read checks gated on `id boole` existing (skip-with-reason otherwise, per `skip()` convention).

---

### `runbooks/agents/meeting-loop-go.md` (owner checklist)

**Analog:** `runbooks/agents/control-plane-go.md` (55 lines — copy structure verbatim)

```markdown
# Control plane go-checklist (Phase 3, owner-go only)

Automation is forbidden to perform any step below. Each step runs only
after the platform owner's explicit go for that exact step. Record each
completion with a dated entry in the slots provided.

Depends on accepted ADR-0006. Secret values live in the password manager
(master) and Secret Manager (runtime) — never pasted into chat, never
committed. The agent checks shapes only.
```
Steps carry `- [ ]` items with `Verify:` lines + `_Dated record (step N):_ <!-- YYYY-MM-DD: ... -->` slots (lines 11-55). New file's steps: LOOP-01 settle (chosen Granola→Notion path recorded), Workspace user + Notion integration share of the *original* meetings DB (Insert Content capability), token-in-Secret-Manager shape check, 10-meeting/$30 trial approval.

## Shared Patterns

### Check-script harness
**Source:** `tests/agents/checks/loops.sh` lines 5-12 (same in `controller.sh`, `accounts.sh`)
**Apply to:** `meeting.sh`, `isolation.sh`
```bash
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
...
exit $fail
```
Auto-discovered by `tests/agents/run.sh` lines 41-46; records appended to `runbooks/agents/checks-<date>.md`.

### Approval gate (A1)
**Source:** `controller/dispatcher.py` lines 107-128 (`park`/`resume`, sender==owner)
**Apply to:** `hyprn-meeting-workflow`, `meeting.sh` tests
```python
def resume(self, run_id, answer, sender, owner):
    """Resume a parked run only on the loop owner's answer. Else ignore."""
    if sender != owner:
        log(run_id, "ignoring answer from non-owner:", sender)
        return False
```

### Untrusted-trigger boundary
**Source:** `controller/dispatcher.py` lines 4-7 (also `validate.py` lines 4-7, broker lines 68-69)
**Apply to:** `poll_notion.py`, `hyprn-meeting-workflow`, `meeting.yaml` tool scoping
```python
"""Trigger envelopes are untrusted (ADR-0006 rule 3): the idempotency key is
recorded BEFORE any dispatch, and unknown loop names are refused BEFORE
any credential or compute is touched. The reviewed YAML registry is the
only authority for tools, credentials and destinations.
```

### Secrets discipline
**Source:** `infra/agents/boole.tf` lines 1-5; `runbooks/agents/control-plane-go.md` lines 7-9
**Apply to:** `boole-notion.tf`, `meeting-loop-go.md`, `meeting.sh` (grep-for-values probe)
```
# Values are added by the owner from the password manager, never through
# Terraform or Git. ... The agent checks shapes only.
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `agents/loops/meeting/prompts.md` + `skills/` | config (prompt) | transform | First judgment-step rubric in tree; planner uses RESEARCH.md Pitfall 5 JSON contract + quote-the-source-line rule |

## Metadata

**Analog search scope:** `controller/`, `agents/loops/`, `agents/host/files/`, `tests/agents/`, `infra/agents/`, `runbooks/agents/`
**Files scanned:** 14 tracked sources (all `git ls-files`-verified)
**Pattern extraction date:** 2026-10-13
