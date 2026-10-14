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

check "runner grades the seed slice offline with no network" "python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' | grep -q '^overall: PASS'"
check "runner report separates seed and real tallies" "python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' | grep -q '^seed: ' && python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' | grep -q '^real: '"

if [ -n "${BOOLE_HOST:-}" ] && command -v docker >/dev/null 2>&1; then
  check "live: runner gateway path grades the seed set" "python3 '$RUNNER' --run live-probe --eval '$EVAL_JSONL'"
else
  skip "live: runner gateway path grades the seed set" "not on agent host (set BOOLE_HOST with docker for live)"
fi
skip "live: feedback capture from the channel server" "live wiring waits for the Boole bot (owner vendor step)"

check "no secret values in learning declarations" "! grep -rE 'xox[baprs]-|ntn_[A-Za-z0-9]|secret_[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9]{8,}' '$EVAL_JSONL' '$RUNNER' '$SCHEMA' '$DISPATCHER'"
check "no secret values in runner output" "! python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' 2>/dev/null | grep -E 'xox[baprs]-|ntn_[A-Za-z0-9]|sk-[A-Za-z0-9]{8,}'"
check "learning.sh is executable for run.sh auto-discovery" "[ -x '$HERE/learning.sh' ]"

exit $fail
