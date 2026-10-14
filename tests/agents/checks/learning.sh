#!/usr/bin/env bash
# Learning-loop checks (Phase 5, LRN-01/LRN-02/LRN-03/LRN-04 + OPS-03 static).
# Static content assertions plus fake-backed probes run anywhere: no
# network, no tokens, no host-only state. Exits non-zero on any failure.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
SCHEMA="$REPO_ROOT/controller/schema.sql"
DISPATCHER="$REPO_ROOT/controller/dispatcher.py"
EVAL_JSONL="$REPO_ROOT/agents/loops/meeting-eval.jsonl"
RUNNER="$REPO_ROOT/agents/eval/run.py"
PROMOTION="$REPO_ROOT/agents/eval/promotion.py"
FIXTURES="$REPO_ROOT/agents/loops/testdata/eval-fixtures"
LOOP_YAML="$REPO_ROOT/agents/loops/meeting.yaml"
PROMPTS="$REPO_ROOT/agents/loops/meeting/prompts.md"
LEARNING_MD="$REPO_ROOT/runbooks/agents/learning.md"
GITHUB_MD="$REPO_ROOT/runbooks/agents/github.md"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

# Improvement gate (LRN-03): a PASS verdict plus a prompts/skills-only
# diff queues the draft for owner review; anything else stays in draft.
# The owner merge step lives outside this gate by design.
improvement_gate() { # $1 verdict file, $2 diffstat file
  grep -q '^overall: PASS' "$1" || return 1
  ! grep -q 'agents/loops/meeting\.yaml' "$2" || return 1
  ! grep -qE '^\+.*(autonomy|promotion_rule)' "$2" || return 1
  return 0
}

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

check "fixture improvement carries the rubric-clarity wording" "grep -q 'Extraction multiplicity' '$PROMPTS'"
check "passing fixture improvement queues for owner review" "VGATE=\"\$(mktemp)\"; DGATE=\"\$(mktemp)\"; python3 '$RUNNER' --fixture '$FIXTURES' --eval '$EVAL_JSONL' >\"\$VGATE\" 2>/dev/null; printf 'branch=agent/boole/seed-wording-clarity\nauthor=boole-agent-hyprn[bot]\n## What changed\n## How verified\n## Eval result\n' >>\"\$VGATE\"; printf 'agents/loops/meeting/prompts.md | 4 +++-\n' >\"\$DGATE\"; grep -q '^## Eval result' \"\$VGATE\" && grep -q 'agent/boole/' \"\$VGATE\" && grep -q 'boole-agent-hyprn\[bot\]' \"\$VGATE\" && grep -q '## What changed' \"\$VGATE\" && grep -q '## How verified' \"\$VGATE\" && improvement_gate \"\$VGATE\" \"\$DGATE\"; rc=\$?; rm -f \"\$VGATE\" \"\$DGATE\"; [ \$rc -eq 0 ]"
check "failing fixture improvement stays in draft" "BADDIR=\"\$(mktemp -d)\"; VGATE=\"\$(mktemp)\"; DGATE=\"\$(mktemp)\"; cp '$FIXTURES'/seed-001.json \"\$BADDIR/seed-001.json\"; printf '{\"decisions\":[],\"actions\":[],\"open_questions\":[],\"patch\":{}}' > \"\$BADDIR/seed-001.json\"; python3 '$RUNNER' --fixture \"\$BADDIR\" --eval '$EVAL_JSONL' >\"\$VGATE\" 2>/dev/null || true; printf 'agents/loops/meeting/prompts.md | 4 +++-\n' >\"\$DGATE\"; ! improvement_gate \"\$VGATE\" \"\$DGATE\"; rc=\$?; rm -rf \"\$BADDIR\" \"\$VGATE\" \"\$DGATE\"; [ \$rc -eq 0 ]"
check "autonomy-touching diffs rejected by the gate" "VGATE=\"\$(mktemp)\"; DGATE=\"\$(mktemp)\"; python3 '$RUNNER' --fixture '$FIXTURES' --eval '$EVAL_JSONL' >\"\$VGATE\" 2>/dev/null; printf 'agents/loops/meeting.yaml | 2 +-\n+  notion-write: A2\n' >\"\$DGATE\"; ! improvement_gate \"\$VGATE\" \"\$DGATE\"; rc=\$?; rm -f \"\$VGATE\" \"\$DGATE\"; [ \$rc -eq 0 ]"

check "promotion reads thresholds from the registry file" "grep -q 'promotion_rule' '$PROMOTION' && ! grep -q 'yaml.dump\|safe_dump' '$PROMOTION'"
check "promotion exits non-zero on seeds-only state" "! python3 '$PROMOTION' '$LOOP_YAML' --eval '$EVAL_JSONL' >/dev/null 2>&1"
check "promotion reports insufficient data on seeds-only state" "POUT=\"\$(python3 '$PROMOTION' '$LOOP_YAML' --eval '$EVAL_JSONL' 2>&1 || true)\"; echo \"\$POUT\" | grep -q 'INSUFFICIENT DATA (seeds excluded)' && echo \"\$POUT\" | grep -q '^real: 0 runs'"
check "promotion threshold source is the registry, never hard-coded" "TDIR=\"\$(mktemp -d)\"; TEVAL=\"\$TDIR/eval.jsonl\"; TLOOP=\"\$TDIR/loop.yaml\"; python3 -c \"import json; rows=[json.loads(l) for l in open('$EVAL_JSONL') if l.strip()]; rows[6]['origin']='real'; rows[12]['origin']='real'; open('\$TEVAL','w').write('\n'.join(json.dumps(r) for r in rows)+'\n')\"; sed 's/last_runs: 10/last_runs: 2/' '$LOOP_YAML' >\"\$TLOOP\"; python3 '$PROMOTION' \"\$TLOOP\" --eval \"\$TEVAL\" | grep -q 'TEMPLATE PASS'; rc=\$?; POUT2=\"\$(python3 '$PROMOTION' '$LOOP_YAML' --eval \"\$TEVAL\" 2>&1 || true)\"; echo \"\$POUT2\" | grep -q 'INSUFFICIENT DATA'; rc2=\$?; rm -rf \"\$TDIR\"; [ \$rc -eq 0 ] && [ \$rc2 -eq 0 ]"
check "promotion changes no autonomy level" "grep -q 'notion-write: A1' '$LOOP_YAML'"

check "Boole App declared with platform-only scope" "grep -q 'boole-agent-hyprn' '$LEARNING_MD' && grep -qi 'hyprn-platform.*only' '$LEARNING_MD'"
check "Boole declaration names contents plus PR write with metadata read" "grep -q 'Contents' '$LEARNING_MD' && grep -q 'Pull requests' '$LEARNING_MD' && grep -qi 'metadata read' '$LEARNING_MD'"
check "webhook stays inactive in the declaration" "grep -qi 'webhook.*inactive' '$LEARNING_MD'"
check "Boole declaration carries the broker token path" "grep -q 'boole-agent-github-app-key' '$LEARNING_MD' && grep -q 'one-hour' '$LEARNING_MD'"
check "Boole declaration records the owner checklist" "grep -q 'owner checklist' '$LEARNING_MD' && grep -q 'gcloud secrets versions add boole-agent-github-app-key' '$LEARNING_MD'"
check "Boole declaration creates nothing and embeds no key material" "! grep -q 'BEGIN PRIVATE KEY' '$LEARNING_MD' && grep -q 'no App creation' '$LEARNING_MD'"
check "GitHub runbook records the Boole declaration row" "grep -q 'Boole App declared' '$GITHUB_MD' && grep -q 'boole-agent-hyprn' '$GITHUB_MD'"

if [ -n "${BOOLE_HOST:-}" ] && command -v docker >/dev/null 2>&1; then
  check "live: runner gateway path grades the seed set" "python3 '$RUNNER' --run live-probe --eval '$EVAL_JSONL'"
  check "live: runner posts the report on the probe PR" "python3 '$RUNNER' --post-pr '${EVAL_POST_PR:-0}' --fixture '$FIXTURES' --eval '$EVAL_JSONL'"
else
  skip "live: runner gateway path grades the seed set" "not on agent host (set BOOLE_HOST with docker for live)"
  skip "live: runner posts the report on the probe PR" "no broker token off-host"
fi
skip "live: feedback capture from the channel server" "live wiring waits for the Boole bot (owner vendor step)"

check "no secret values in learning declarations" "! grep -rE 'xox[baprs]-|ntn_[A-Za-z0-9]|secret_[A-Za-z0-9_-]{6,}|sk-[A-Za-z0-9]{8,}' '$EVAL_JSONL' '$RUNNER' '$PROMOTION' '$SCHEMA' '$DISPATCHER' '$FIXTURES' '$LOOP_YAML' '$PROMPTS' '$LEARNING_MD' '$GITHUB_MD'"

check "no secret values in runner output" "! python3 '$RUNNER' --fixture '' --eval '$EVAL_JSONL' 2>/dev/null | grep -E 'xox[baprs]-|ntn_[A-Za-z0-9]|sk-[A-Za-z0-9]{8,}'"
check "learning.sh is executable for run.sh auto-discovery" "[ -x '$HERE/learning.sh' ]"

exit $fail
