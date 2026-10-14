# Phase 5: Learning - Pattern Map

**Mapped:** 2026-10-14
**Files analyzed:** 7 (6 new + 2 modified)
**Analogs found:** 7 / 7

All analog paths below verified git-tracked via `git ls-files` (2026-10-14).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `agents/loops/meeting-eval.jsonl` (NEW) | config | batch | `agents/loops/testdata/meeting-pages/new.json` + `agents/loops/meeting.yaml` (`eval_set` pointer) | exact |
| `controller/test_feedback.py` (NEW) | test | CRUD | `controller/test_dispatcher.py` | exact |
| `controller/schema.sql` (MOD: add `feedback` table) | model | CRUD | itself (`runs`/`approvals` tables, lines 4-21) | exact |
| `controller/dispatcher.py` (MOD: add `record_feedback`) | service | request-response | itself (`enqueue`/`park`/`resume`, lines 61-128) | exact |
| eval runner, e.g. `agents/eval/run.py` (NEW) | utility | batch | `agents/host/files/hyprn-meeting-workflow` + `controller/poll_notion.py` (`scan_fixture_dir`) | role-match |
| promotion-check, e.g. `agents/eval/promotion.py` (NEW) | utility | batch | `agents/loops/validate.py` | role-match |
| `tests/agents/checks/learning.sh` (NEW) | test | batch | `tests/agents/checks/meeting.sh` | exact |
| `agents/loops/testdata/eval-fixtures/` (NEW dir) | test | file-I/O | `agents/loops/testdata/meeting-pages/` | exact |
| Boole App declaration (docs + `boole.tf` row) (MOD) | config | request-response | `infra/agents/boole.tf` + `runbooks/agents/github.md` | exact |

## Pattern Assignments

### `agents/loops/meeting-eval.jsonl` (config, batch)

**Analog:** `agents/loops/testdata/meeting-pages/new.json` (case content shape) + `agents/loops/meeting.yaml` lines 29-33 (registry pointer + thresholds)

**Registry pointer pattern** (`agents/loops/meeting.yaml`, lines 29-33):
```yaml
eval_set: agents/loops/meeting-eval.jsonl
promotion_rule:
  min_pass_rate: 0.9
  last_runs: 10
  max_corrections_per_run: 1
```
No registry change needed — `eval_set` already points at the new file. Runner and promotion-check read thresholds from here, never hard-code.

**Case content pattern** (`agents/loops/testdata/meeting-pages/new.json`, line 1):
```json
{"body": "Discussed Q3 launch scope. DECISION: Ship the beta to five pilot customers by Nov 1. ACTION: Platform owner to confirm the pilot list by Oct 20. Open question: pricing tier for pilots.", "id": "page-abc123", "last_edited_time": "2026-10-13T09:00:00Z", "title": "Weekly sync 2026-10-13"}
```
Each JSONL line reuses this page shape inside a `page` object, plus the rubric contract (`decisions`/`actions`/`open_questions`/`patch`, quote-the-source, propose-nothing degrade per `agents/loops/meeting/prompts.md`):
```json
{"id": "seed-001", "origin": "seed", "regression": true, "page": {"title": "...", "body": "DECISION: ... ACTION: ..."}, "expect": {"min_decisions": 1, "min_actions": 1, "must_quote_source": true, "propose_nothing": false}}
```
`origin` is REQUIRED, closed set `seed`|`real`; `regression:true` marks the always-run subset. Seeds labeled `seed` everywhere — never present seed output as real.

---

### `controller/test_feedback.py` (test, CRUD)

**Analog:** `controller/test_dispatcher.py`

**Imports + fixture pattern** (lines 1-28):
```python
#!/usr/bin/env python3
"""... Stdlib unittest, fakes only: no network, no cloud, no keys. Run: python3 -m unittest discover -s controller."""
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
```
Copy verbatim: `fresh_db()` + `registry_of("meeting")` give in-memory-sqlite fakes. New tests cover: closed-kind enforcement (reject unknown `kind`), dedupe-key idempotency (same `dedupe_key` inserts once), unknown-run refusal, approval-feedback pairing. Discovered automatically by the existing `controller.sh` assertion (`python3 -m unittest discover -s controller`) — no harness change needed.

**Class-per-behavior pattern** (lines 31-38): one `unittest.TestCase` subclass per behavior group (`TestIdempotentEnqueue`, `TestRegistryGate`, `TestParkedApproval`, ...). Add e.g. `TestRecordFeedback` in the same shape.

---

### `controller/schema.sql` + `controller/dispatcher.py` (MOD: feedback store + writer)

**Analog:** the files themselves — extend, don't invent.

**Schema pattern** (`controller/schema.sql`, lines 4-21):
```sql
CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY,
  ...
  idempotency_key TEXT NOT NULL UNIQUE,
  ...
);
CREATE TABLE IF NOT EXISTS approvals(
  run_id TEXT NOT NULL REFERENCES runs(id),
  question TEXT NOT NULL,
  answer TEXT,
  decided_at TEXT
);
```
Append beside them (SQLite-now/Cloud-SQL-later: only TEXT/REAL/INTEGER + `datetime('now')`):
```sql
CREATE TABLE IF NOT EXISTS feedback(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES runs(id),
  kind TEXT NOT NULL,            -- 'reaction' | 'reply' | 'approval' (closed set, enforced in writer)
  payload TEXT NOT NULL,         -- JSON: emoji / reply text+sender / answer+sender
  sender TEXT NOT NULL DEFAULT '',
  dedupe_key TEXT NOT NULL UNIQUE, -- caller-supplied idempotency (Socket-Mode retries)
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Writer pattern** (`controller/dispatcher.py`): copy the `enqueue` discipline (lines 61-86) — validate BEFORE touching state, idempotency via `INSERT` + `IntegrityError`:
```python
def enqueue(self, envelope):
    try:
        key = envelope["idempotency_key"]
        loop = envelope["loop"]
    except (KeyError, TypeError) as error:
        log("bad envelope:", error)
        return None
    if loop not in self.registry():
        log("refusing unknown loop:", loop)
        return None
    ...
    except sqlite3.IntegrityError:
        return run_id  # duplicate envelope: already queued
```
So `record_feedback(run_id, kind, payload, sender="", dedupe_key="")`: reject unknown `kind` (closed tuple `("reaction", "reply", "approval")`) and unknown `run_id` before insert; `INSERT OR IGNORE` / `IntegrityError` on `dedupe_key` for Socket-Mode retry dedupe. Approval-decision feedback is one extra INSERT in the `resume` path (lines 116-128), which already gates `sender == owner` — stranger answers return `False` and record nothing.

**Module conventions** (lines 1-21, 156-160): `#!/usr/bin/env python3` + docstring naming the phase/req IDs, `Dependencies: Python 3 standard library only (sqlite3)`, constructor-injected seams (`registry`, `gateway`, `now`), `log()` to stderr with `hyprn-dispatcher:` prefix, `open_db()` helper loading `SCHEMA_PATH`.

---

### Eval runner, e.g. `agents/eval/run.py` (utility, batch)

**Analog:** `agents/host/files/hyprn-meeting-workflow` (fixture seam + declared-secrets guard) + `controller/poll_notion.py` `scan_fixture_dir` (lines 125-134)

**Fixture-seam pattern** (`hyprn-meeting-workflow`, lines 66-92):
```bash
fetch_page() {
  if [ -n "$FIXTURE_DIR" ]; then
    src="$FIXTURE_DIR/${PAGE_ID}.json"
    [ -r "$src" ] || src="$FIXTURE_DIR/new.json"
    cp "$src" "$RUN_DIR/page.json"
  else
    notion_token="$(cat "$RUN_DIR/boole-agent-notion-token" 2>/dev/null || true)"
    ...
    unset notion_token
  fi
}
```
Runner MUST follow this shape: `--fixture <dir>` runs all cases against canned model outputs / the local extract function with no gateway, no tokens; live path (`--run <id>` via gateway) is a strict superset. Precedent also in broker (`hyprn-credential-broker` lines 52-59: fixture mode creates placeholder dirs, `exit 0`, no network) and poller (`poll_notion.py` lines 125-134: `scan_fixture_dir` reads `*.json` from a directory, used by `--fixture` mode and tests).

**Declared-secrets guard** (`hyprn-meeting-workflow`, lines 46-60; broker lines 68-85):
```bash
# Declared secret names come ONLY from the reviewed loop file — never from
# trigger payload (ADR-0006 rule 3). Undeclared secrets are refused.
declared_secrets() {
  python3 -c "
import yaml
doc = yaml.safe_load(open('$LOOP'))
...
"
}
```
Reuse verbatim: secret names come ONLY from the reviewed loop YAML. Runner posts the seed-labeled report on the PR via `gh` with the broker-minted token — reuse the broker RS256 flow (`hyprn-credential-broker` lines 105-132), never hand-roll signing. Deterministic verdicts (valid JSON, required keys, every item has non-empty `source`, malformed→propose-nothing) are the gate; any gateway-graded quality score is advisory-only.

**PR body contract** (see Shared Patterns → Draft-PR contract): report carries `## Eval result` + the word `seed` in tallies; print seed and real tallies on separate lines, never blend.

---

### Promotion-check, e.g. `agents/eval/promotion.py` (utility, batch)

**Analog:** `agents/loops/validate.py`

**Structure pattern** (`agents/loops/validate.py`, lines 1-62):
```python
#!/usr/bin/env python3
"""... Dependencies: Python 3 standard library and PyYAML (Debian python3-yaml)."""
import sys
import yaml

def log(*parts):
    print("hyprn-loops:", *parts, file=sys.stderr, flush=True)

def validate(path):
    """... Returns True when valid, False otherwise."""
    try:
        with open(path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
    except (ValueError, OSError) as error:
        log(path, "unparseable:", error)
        return False
    ...
    return True

def main():
    if len(sys.argv) < 2:
        log("usage: ...")
        return 2
    ...
if __name__ == "__main__":
    sys.exit(main())
```
Copy: stdlib + PyYAML only, `log()` to stderr with component prefix, `validate(path)`-style function returning bool, `main()` with usage + exit codes. The check reads `min_pass_rate`/`last_runs`/`max_corrections_per_run` from `agents/loops/meeting.yaml` (never hard-codes thresholds), counts only `origin:"real"` runs; fewer than 10 real runs → print `INSUFFICIENT DATA (seeds excluded)`, exit non-zero — never a false PASS. Ships as a template: must NOT flip `autonomy` in `meeting.yaml` (validator rejects bad levels, `validate.py` lines 40-43; `learning.sh` asserts the improvement diff touches only `prompts.md`/`skills/*`).

---

### `tests/agents/checks/learning.sh` (test, batch)

**Analog:** `tests/agents/checks/meeting.sh` (exact: static + fake-backed probes, runnable anywhere)

**Harness pattern** (`meeting.sh`, lines 1-16; auto-discovery in `tests/agents/run.sh` lines 41-46):
```bash
#!/usr/bin/env bash
# Meeting-loop checks (Phase 4, ...). Static content assertions plus fake-backed probes run anywhere: no
# network, no tokens, no host-only state. Exits non-zero on any failure.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
...
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
...
exit $fail
```
Copy the header + `check`/`skip` helpers verbatim; file must be executable (auto-discovered by `run.sh`; assert with `[ -x ... ]` as `meeting.sh` line 75 does). Borrow per-concern idioms:
- **Static JSON/YAML assertions** from `meeting.sh` lines 18-27 (grep for contract fields, `python3 validate.py`) and `loops.sh` lines 14-38 (validator green over registry files + negative probe with `mktemp` BAD file asserting rejection).
- **Fake-backed python probes** from `meeting.sh` lines 35-54 (heredoc `python3 - <<'EOF'` with `REPO_ROOT`/`FIXTURES` env, in-memory sqlite, hard asserts) — use for: JSONL parses, ≥20 cases, all `origin`-labeled, regression subset non-empty, promotion-check `INSUFFICIENT DATA` on seeds-only, eval-runner `--fixture` green offline.
- **Live-gating SKIP** from `runner.sh` lines 45-53 and `github.sh` lines 58-68: live gateway/`gh`/host paths guarded by tool presence (`command -v docker`, `id boole`), else `skip "..." "reason"`. `learning.sh` must pass off-host.
- **Secret-guard extension** from `meeting.sh` line 71: extend the `xox[baprs]-|ntn_|sk-` grep to the eval file, fixtures, and runner output.
- **Unit-suite line** from `controller.sh` line 14: `python3 -m unittest discover -s controller` already picks up `test_feedback.py` — no new line needed, but `learning.sh` may assert the feedback tests exist.

---

### `agents/loops/testdata/eval-fixtures/` (test, file-I/O)

**Analog:** `agents/loops/testdata/meeting-pages/` (`new.json`, `updated.json`, `malformed.json` — all git-tracked)

Copy the flat-JSON-page convention (title + DECISION/ACTION/open-question body, `id`, `last_edited_time`) for canned input pages, plus canned model outputs (good contract, malformed→propose-nothing, injection-attempt page) so the runner's `--fixture` mode proves deterministic verdicts offline. Consumed via the `scan_fixture_dir` pattern (`poll_notion.py` lines 125-134: sorted `*.json` directory scan).

---

### Boole App declaration (config, request-response)

**Analog:** `infra/agents/boole.tf` (secret-container declaration) + `runbooks/agents/github.md` (App create/install procedure + record table)

**Declaration pattern** (`boole.tf`, lines 1-8, 17-34):
```python
# ... secret containers plus key blocks, declared NOT created. Values are added by the owner from
# the password manager ..., never through Terraform or Git. Vendor-side objects ... are
# owner checklists in the go-runbook, not resources here.
resource "google_secret_manager_secret" "boole" {
  for_each  = local.boole_secrets
  ...
  labels = { component = "agents", agent = each.value, managed_by = "terraform" }
}
```
Boole's App ships as: manifest/scope declaration (`hyprn-platform` only, contents + pull-requests write, metadata read) + broker path + owner checklist. The `boole-agent-github-app-key` container already exists (`boole.tf` lines 45-61). Per `github.md` lines 1-5: App named `boole-agent-hyprn`, webhook inactive, install `hyprn-platform` only (NOT all repos — unlike Ada). No App-create API calls, no key material in-phase (a plan task doing either fails the phase's own checks). Append a Boole row to `github.md` (declaration, not creation) following the existing `## Record` dated-table pattern.

---

## Shared Patterns

### Check-script harness
**Source:** `tests/agents/checks/meeting.sh` lines 1-16; discovery `tests/agents/run.sh` lines 41-46; record append `run.sh` lines 48-62
**Apply to:** `tests/agents/checks/learning.sh`
```bash
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
...
exit $fail
```
Every executable `checks/*.sh` is auto-discovered; results append a dated record under `runbooks/agents/`.

### Fake-seam / `--fixture` offline mode
**Source:** `agents/host/files/hyprn-credential-broker` lines 52-59; `agents/host/files/hyprn-meeting-workflow` lines 66-92; `controller/poll_notion.py` lines 125-134
**Apply to:** eval runner, `learning.sh`, `eval-fixtures/`
```bash
if [ "$FIXTURE_MODE" = 1 ]; then
  # Fixture mode: no network. ... so checks run anywhere.
  dir="$FIXTURE_DIR/$RUN_ID"
  install -d -m 0700 "$dir"
  ...
  exit 0
fi
```
`--fixture` default in checks; live path guarded with `SKIP <reason>` (`runner.sh` lines 45-53).

### Draft-PR contract (GH-01)
**Source:** `tests/agents/checks/github.sh` lines 39-45; ruleset lines 18-33
**Apply to:** improvement-PR flow + eval report posting
```bash
check "GH-01: ada-task carries the What-changed heading" "grep -qF '## What changed' '$HELPER'"
check "GH-01: ada-task creates agent/<name>/<slug> branches" "grep -qF 'branch=\"agent/\$(id -un)/\$task\"' '$HELPER'"
check "GH-01: no self-merge path in helper or intake" "! grep -rq 'gh pr merge' ..."
```
Improvement PRs use `agent/boole/<slug>` branches, bot author, `## What changed` + `## How verified` + seed-labeled `## Eval result`; owner merges only (ruleset: PR + human code-owner approval, stale dismissal, empty bypass list). Eval gate rejects any `meeting.yaml`/`autonomy` change in improvement diffs.

### Declared-secrets-only authority (ADR-0006 rule 3)
**Source:** `agents/host/files/hyprn-meeting-workflow` lines 46-60; asserted by `meeting.sh` line 33
**Apply to:** eval runner, promotion-check, improvement path
```bash
check "workflow takes secrets only from the reviewed loop file" "grep -q 'eclared secret names come ONLY.*reviewed loop file' '$WORKFLOW'"
```

### Unit-test fake pattern
**Source:** `controller/test_dispatcher.py` lines 16-28; run via `tests/agents/checks/controller.sh` line 14
**Apply to:** `controller/test_feedback.py`
```bash
check "controller unit suite is green" "python3 -m unittest discover -s '$REPO_ROOT/controller'"
```

### Approval scoping (run id + page id)
**Source:** `agents/loops/meeting/skills/notion-slack-shapes.md` lines 29-42; `controller/dispatcher.py` lines 116-128
**Apply to:** LRN-01 approval-decision feedback
```
[meeting run-<idempotency-key> page <page-id>] <title>
...
Approve? Reply yes to apply the patch, no to drop it.
```
Approval text carries run id + page id so a yes cannot replay onto another run; only the loop owner's answer resumes. Feedback rows store the run id parsed from this scoped text; Slack shape is read-side only (no new bot scopes/events).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| *(none)* | — | — | Every Phase 5 file extends a check-covered existing pattern; RESEARCH.md §"Don't Hand-Roll" covers what must NOT be built (custom JWT minting, new queue, new Slack listener, new Notion client, aggregation service). |

## Metadata

**Analog search scope:** `controller/`, `agents/loops/`, `agents/host/files/`, `agents/marketplace/plugins/slack/`, `tests/agents/checks/`, `infra/agents/`, `runbooks/agents/`
**Files scanned:** ~20 (all Reads listed in RESEARCH.md Sources §Primary + verification reads this session)
**Pattern extraction date:** 2026-10-14
**Git-track gate:** every analog path verified with `git ls-files` — no mirror/untracked paths emitted.
