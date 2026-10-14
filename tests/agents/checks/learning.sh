#!/usr/bin/env bash
# Learning-loop checks (Phase 5, LRN-01/LRN-02 + OPS-03 static).
# Static content assertions plus fake-backed probes run anywhere: no
# network, no tokens, no host-only state. Exits non-zero on any failure.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
SCHEMA="$REPO_ROOT/controller/schema.sql"
DISPATCHER="$REPO_ROOT/controller/dispatcher.py"
EVAL_JSONL="$REPO_ROOT/agents/loops/meeting-eval.jsonl"
RUNNER="$REPO_ROOT/agents/eval/run.py"
FIXTURES="$REPO_ROOT/agents/loops/testdata/eval-fixtures"
LOOP_YAML="$REPO_ROOT/agents/loops/meeting.yaml"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

check "schema carries the feedback table" "grep -q 'CREATE TABLE IF NOT EXISTS feedback' '$SCHEMA'"
check "dispatcher carries the feedback writer" "grep -q 'def record_feedback' '$DISPATCHER'"
check "feedback kinds stay a closed set" "grep -q 'FEEDBACK_KINDS' '$DISPATCHER'"
check "approval answers stay owner-gated" "grep -q 'sender != owner' '$DISPATCHER'"

check "controller unit suite is green" "python3 -m unittest discover -s '$REPO_ROOT/controller'"

check "seed eval file parses as one JSON object per line" "python3 -c \"import json; [json.loads(l) for l in open('$EVAL_JSONL') if l.strip()]\""
check "every eval line carries an origin marker" "REPO_ROOT='$REPO_ROOT' python3 - <<'EOF'
import json, os
rows = [json.loads(l) for l in open(os.path.join(os.environ['REPO_ROOT'], 'agents', 'loops', 'meeting-eval.jsonl')) if l.strip()]
assert rows, 'eval set is empty'
assert all(r.get('origin') in ('seed', 'real') for r in rows), 'origin must be seed or real'
assert all(r.get('origin') == 'seed' for r in rows), '05-01 slice must be all seeds'
EOF"
check "eval regression subset is non-empty" "python3 -c \"import json; rows=[json.loads(l) for l in open('$EVAL_JSONL') if l.strip()]; assert any(r.get('regression') for r in rows)\""
check "eval pages mirror the fixture title/body shape" "python3 -c \"import json; rows=[json.loads(l) for l in open('$EVAL_JSONL') if l.strip()]; assert all(set(r.get('page', {})) >= {'id', 'last_edited_time'} for r in rows)\""

check "eval set holds at least 20 seed-labeled cases" "REPO_ROOT='$REPO_ROOT' python3 - <<'EOF'
import json, os
rows = [json.loads(l) for l in open(os.path.join(os.environ['REPO_ROOT'], 'agents', 'loops', 'meeting-eval.jsonl')) if l.strip()]
assert len(rows) >= 20, len(rows)
assert all(r.get('origin') == 'seed' for r in rows), 'full set must be all seeds until the trial feeds real runs'
assert any(r.get('regression') for r in rows), 'regression subset must be non-empty'
EOF"
check "eval covers injection and malformed shapes" "python3 -c \"import json; rows=[json.loads(l) for l in open('$EVAL_JSONL') if l.strip()]; assert sum(1 for r in rows if r.get('expect', {}).get('propose_nothing')) >= 2; assert sum(1 for r in rows if 'njection' in (r.get('page', {}).get('title') or '')) >= 2\""
check "injection pages grade propose-only with empty patch" "REPO_ROOT='$REPO_ROOT' RUNNER='$RUNNER' EVAL='$EVAL_JSONL' python3 - <<'EOF'
import json, os, sys
sys.path.insert(0, os.path.join(os.environ['REPO_ROOT'], 'agents', 'eval'))
import run
rows = [json.loads(l) for l in open(os.environ['EVAL']) if l.strip()]
injected = [r for r in rows if 'njection' in (r.get('page', {}).get('title') or '')]
assert len(injected) >= 2, len(injected)
for case in injected:
    extraction = run.extract_local(case['page'])
    ok, reasons = run.grade(case, extraction)
    assert ok, (case['id'], reasons)
    assert extraction['patch'] == {}, case['id']
EOF"

check "runner grades the seed slice offline with no network" "python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' | grep -q '^overall: PASS'"
check "runner grades the full set against canned fixtures offline" "python3 '$RUNNER' --fixture '$FIXTURES' --eval '$EVAL_JSONL' | grep -q '^overall: PASS'"
check "runner smoke-checks canned input pages in sorted order" "python3 '$RUNNER' --fixture '$FIXTURES' --eval '$EVAL_JSONL' | grep -q '^fixture pages: [1-9][0-9]*/[1-9][0-9]* shape-ok'"
check "runner report separates seed and real tallies" "python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' | grep -q '^seed: ' && python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' | grep -q '^real: '"
check "runner rejects a tampered canned output" "BADDIR=\"\$(mktemp -d)\"; cp '$FIXTURES'/seed-001.json \"\$BADDIR/seed-001.json\"; printf '{\"decisions\":[],\"actions\":[],\"open_questions\":[],\"patch\":{}}' > \"\$BADDIR/seed-001.json\"; ! python3 '$RUNNER' --fixture \"\$BADDIR\" --eval '$EVAL_JSONL' | grep -q '^overall: PASS'; rm -rf \"\$BADDIR\""
check "runner takes secrets only from the reviewed loop file" "grep -q 'eclared secret names come ONLY.*reviewed loop file' '$RUNNER'"
check "runner declares its live and post flags" "python3 '$RUNNER' --help | grep -q -- '--run' && python3 '$RUNNER' --help | grep -q -- '--post'"
check "runner post mode emits the seed-labeled body section" "python3 '$RUNNER' --fixture '$FIXTURES' --eval '$EVAL_JSONL' --post | grep -q '^## Eval result' && python3 '$RUNNER' --fixture '$FIXTURES' --eval '$EVAL_JSONL' --post | grep -q '^seed: '"

if [ -n "${BOOLE_HOST:-}" ] && command -v docker >/dev/null 2>&1; then
  check "live: runner gateway path grades the seed set" "python3 '$RUNNER' --run live-probe --eval '$EVAL_JSONL'"
  check "live: runner posts the report on the probe PR" "python3 '$RUNNER' --post-pr '${EVAL_POST_PR:-0}' --fixture '$FIXTURES' --eval '$EVAL_JSONL'"
else
  skip "live: runner gateway path grades the seed set" "not on agent host (set BOOLE_HOST with docker for live)"
  skip "live: runner posts the report on the probe PR" "no broker token off-host"
fi
skip "live: feedback capture from the channel server" "live wiring waits for the Boole bot (owner vendor step)"

check "no secret values in learning declarations" "! grep -rE 'xox[baprs]-|ntn_[A-Za-z0-9]|secret_[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9]{8,}' '$EVAL_JSONL' '$RUNNER' '$SCHEMA' '$DISPATCHER' '$FIXTURES' '$LOOP_YAML'"

check "no secret values in runner output" "! python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' 2>/dev/null | grep -E 'xox[baprs]-|ntn_[A-Za-z0-9]|sk-[A-Za-z0-9]{8,}'"
check "learning.sh is executable for run.sh auto-discovery" "[ -x '$HERE/learning.sh' ]"

exit $fail
