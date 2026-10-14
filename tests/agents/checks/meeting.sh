#!/usr/bin/env bash
# Meeting-loop checks (Phase 4, LOOP-01/LOOP-02/LOOP-03 + OPS-02 static).
# Static content assertions plus fake-backed probes run anywhere: no
# network, no tokens, no host-only state. Exits non-zero on any failure.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
MEETING_YAML="$REPO_ROOT/agents/loops/meeting.yaml"
VALIDATOR="$REPO_ROOT/agents/loops/validate.py"
PROMPTS="$REPO_ROOT/agents/loops/meeting/prompts.md"
SHAPES="$REPO_ROOT/agents/loops/meeting/skills/notion-slack-shapes.md"
WORKFLOW="$REPO_ROOT/agents/host/files/hyprn-meeting-workflow"
FIXTURES="$REPO_ROOT/agents/loops/testdata/meeting-pages"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

check "validator green on meeting.yaml" "python3 '$VALIDATOR' '$MEETING_YAML'"
check "meeting loop pins notion-write to A1" "grep -q 'notion-write: A1' '$MEETING_YAML'"
check "meeting loop polls notion-meetings every 5m" "grep -q 'source: notion-meetings' '$MEETING_YAML' && grep -q 'interval: 5m' '$MEETING_YAML'"

check "rubric pins the JSON contract fields" "grep -q '\"decisions\"' '$PROMPTS' && grep -q '\"actions\"' '$PROMPTS' && grep -q '\"open_questions\"' '$PROMPTS' && grep -q '\"patch\"' '$PROMPTS'"
check "rubric carries the quote-the-source rule" "grep -qi 'quote.*source\|source.*quot' '$PROMPTS'"
check "rubric carries the instruction-injection guard" "grep -qi 'injection guard' '$PROMPTS'"
check "rubric degrades malformed input to propose-nothing" "grep -q 'propose-nothing' '$PROMPTS'"
check "shapes note pins Notion-Version 2026-03-11" "grep -q 'Notion-Version: 2026-03-11' '$SHAPES'"
check "shapes note scopes approval text with run id plus page id" "grep -q 'run id' '$SHAPES' && grep -q 'page id' '$SHAPES'"

check "workflow parks before any PATCH application" "[ \"\$(grep -n 'park_and_exit\|Dispatcher.*park' '$WORKFLOW' | head -1 | cut -d: -f1)\" -lt \"\$(grep -n 'apply_patch()' '$WORKFLOW' | head -1 | cut -d: -f1)\" ]"
check "workflow records per-run cost" "grep -q 'record_cost' '$WORKFLOW'"
check "workflow holds no sleep while parked" "! grep -qE '^\s*sleep' '$WORKFLOW'"
check "workflow unsets key material after use" "grep -q 'unset .*token' '$WORKFLOW'"
check "workflow takes secrets only from the reviewed loop file" "grep -q 'eclared secret names come ONLY.*reviewed loop file' '$WORKFLOW'"

check "poller fixture mode emits one run per new page and dedupes" "REPO_ROOT='$REPO_ROOT' FIXTURES='$FIXTURES' python3 - <<'EOF'
import os, sqlite3, sys
sys.path.insert(0, os.path.join(os.environ['REPO_ROOT'], 'controller'))
from dispatcher import Dispatcher
import poll_notion, json
schema = os.path.join(os.environ['REPO_ROOT'], 'controller', 'schema.sql')
def fresh():
    c = sqlite3.connect(':memory:')
    c.executescript(open(schema).read())
    return c
def page(n):
    return json.load(open(os.path.join(os.environ['FIXTURES'], n)))
disp = Dispatcher(fresh(), registry=lambda: {'meeting': {}})
first, cursor = poll_notion.poll_once([page('new.json')], disp)
assert first == ['run-notion-page-page-abc123'], first
second, _ = poll_notion.poll_once([page('new.json'), page('updated.json')], disp, cursor=cursor)
assert second == [], second
runs = disp.db.execute('SELECT COUNT(*) AS n FROM runs').fetchone()['n']
assert runs == 1, runs
EOF"

check "cost ledger accumulates per meeting run" "REPO_ROOT='$REPO_ROOT' python3 - <<'EOF'
import os, sqlite3, sys
sys.path.insert(0, os.path.join(os.environ['REPO_ROOT'], 'controller'))
from dispatcher import Dispatcher
schema = os.path.join(os.environ['REPO_ROOT'], 'controller', 'schema.sql')
c = sqlite3.connect(':memory:')
c.executescript(open(schema).read())
disp = Dispatcher(fresh_db := c, registry=lambda: {'meeting': {}})
run = disp.enqueue({'idempotency_key': 'notion-page-budget-probe', 'loop': 'meeting', 'budget_usd': 30.0})
disp.record_cost(run, 1.5)
disp.record_cost(run, 2.5)
cost = disp.db.execute('SELECT cost_usd FROM runs WHERE id = ?', (run,)).fetchone()['cost_usd']
assert abs(cost - 4.0) < 1e-9, cost
EOF"

check "no secret values in meeting declarations" "! grep -rE 'xox[baprs]-|ntn_[A-Za-z0-9]|secret_[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9]{8,}' '$MEETING_YAML' '$PROMPTS' '$SHAPES' '$WORKFLOW'"
# Pattern built without the literal so this file's own line never matches.
UPSTREAM_TOOL="$(printf 'gran%cola' o)"
check "no meeting-tool integration selected" "! grep -ri \"\$UPSTREAM_TOOL\" '$MEETING_YAML' '$PROMPTS' '$SHAPES' '$WORKFLOW' '$FIXTURES'"
check "meeting.sh is executable for run.sh auto-discovery" "[ -x '$HERE/meeting.sh' ]"

exit $fail
