#!/usr/bin/env bash
# Fleet-registry checks (Phase 6, FLT-01 + CODD-02 schema side). Static content
# assertions run anywhere; no host SSH, no vendor calls.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
VALIDATOR="$REPO_ROOT/agents/fleet-validate"
RENDERER="$REPO_ROOT/agents/fleet-render"
REGISTRY="$REPO_ROOT/agents/fleet.yaml"
AGENTS_TXT="$REPO_ROOT/agents/host/agents.txt"
WAKE_JSON="$REPO_ROOT/agents/wake/wake.json"
TFVARS_JSON="$REPO_ROOT/infra/agents/fleet.auto.tfvars.json"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

check "validator exits 0 on the fleet registry" "python3 '$VALIDATOR' '$REGISTRY'"
check "validator accepts the committed wake list" "python3 '$VALIDATOR' '$REGISTRY' --wake '$WAKE_JSON'"
check "renderer regen is clean on all three generated files" "python3 '$RENDERER' --check"

if python3 -c "import yaml" >/dev/null 2>&1; then
  check "registry declares ada and codd" "python3 -c \"import yaml; assert {a['name'] for a in yaml.safe_load(open('$REGISTRY'))['agents']} >= {'ada','codd'}\""
  check "codd row carries the Codd pattern (opencode, no slack, no workspace)" "python3 -c \"import yaml; c=[a for a in yaml.safe_load(open('$REGISTRY'))['agents'] if a['name']=='codd'][0]; assert (c['kind'],c['harness'],c['slack'],c['workspace'])==('engineering','opencode',False,'none')\""
  check "tfvars renders agents [ada codd] sorted" "python3 -c \"import json; assert json.load(open('$TFVARS_JSON'))['agents']==['ada','codd']\""
  check "tfvars renders slack_agents [ada]" "python3 -c \"import json; assert json.load(open('$TFVARS_JSON'))['slack_agents']==['ada']\""
  check "ada present in wake.json agents" "python3 -c \"import json; assert 'ada' in json.load(open('$WAKE_JSON'))['agents']\""
  check "codd absent from wake.json agents" "python3 -c \"import json; assert 'codd' not in json.load(open('$WAKE_JSON'))['agents']\""
else
  skip "registry content probes" "no yaml parser on PATH"
fi

# The provision.sh reader skips comments/blanks and reads eight columns with
# display taking the rest of the line; rendered rows must keep that shape.
check "agents.txt rows keep the load-bearing eight-column shape" "grep -vE '^\\s*(#|\$)' '$AGENTS_TXT' | awk 'NF>=8' | grep -q ada"

# Scripts take secret paths/handles only, never values: no value-taking token
# flags, no set -x near handles. agents/fleet joins this list in 06-02.
VALUE_FLAGS='--(token|secret|key)([ =]|$)'
FOUND=""
for script in "$RENDERER" "$VALIDATOR"; do
  [ -f "$script" ] || continue
  if grep -rEn -- "$VALUE_FLAGS" "$script" >/dev/null 2>&1; then FOUND="$FOUND $(basename "$script")"; fi
done
[ -f "$REPO_ROOT/agents/fleet" ] && grep -rEn -- "$VALUE_FLAGS" "$REPO_ROOT/agents/fleet" >/dev/null 2>&1 && FOUND="$FOUND fleet"
check "no secret-value flags in fleet scripts" "[ -z '$FOUND' ]"

# Negative probes in the loops.sh mktemp-fixture shape.
BAD="$(mktemp)"
sed 's/harness: claude/harness: bogus/' "$REGISTRY" > "$BAD"
check "negative probe: bad harness is rejected" "! python3 '$VALIDATOR' '$BAD'"
rm -f "$BAD"

DUP="$(mktemp)"
sed 's/uid: 20002/uid: 20001/' "$REGISTRY" > "$DUP"
check "negative probe: duplicate UID is rejected" "! python3 '$VALIDATOR' '$DUP'"
rm -f "$DUP"

LEGACY="$(mktemp)"
sed 's/name: codd/name: agent-codd/' "$REGISTRY" > "$LEGACY"
check "negative probe: agent-<name> legacy name is rejected" "! python3 '$VALIDATOR' '$LEGACY'"
rm -f "$LEGACY"

WAKEBAD="$(mktemp)"
python3 -c "import json; d=json.load(open('$WAKE_JSON')); d['agents']=sorted(d['agents']+['codd']); json.dump(d,open('$WAKEBAD','w'),indent=2)"
check "negative probe: Slack-less agent in wake list is rejected" "! python3 '$VALIDATOR' '$REGISTRY' --wake '$WAKEBAD'"
rm -f "$WAKEBAD"

# CLI assertions (06-02): fleet add/remove dry-runs per kind plus handles-only
# shape. Static and local: no SSH, no vendor calls.
FLEET="$REPO_ROOT/agents/fleet"
check "fleet add driver exists and is executable" "[ -x '$FLEET' ]"
check "onboarding runbook exists and covers both kinds plus remove" "[ -f '$REPO_ROOT/runbooks/agents/onboarding.md' ] && grep -q 'fleet add' '$REPO_ROOT/runbooks/agents/onboarding.md' && grep -q 'fleet remove' '$REPO_ROOT/runbooks/agents/onboarding.md'"
# Snapshot the tree so the dry-run-clean assertion below only sees what the
# dry-runs themselves change (the check must stay green on a dirty worktree).
TREE_BEFORE="$(mktemp)"
git -C "$REPO_ROOT" status --porcelain agents/ infra/agents/ | grep -v '^??' | sort >"$TREE_BEFORE"
ENG_OUT="$(mktemp)"; OPS_OUT="$(mktemp)"; RM_OUT="$(mktemp)"
ENG_START="$(date +%s)"
"$FLEET" add test-eng --kind engineering --harness opencode --dry-run >"$ENG_OUT" 2>&1
ENG_STATUS=$?
ENG_END="$(date +%s)"
OPS_START="$(date +%s)"
"$FLEET" add test-ops --kind operations --dry-run >"$OPS_OUT" 2>&1
OPS_STATUS=$?
OPS_END="$(date +%s)"
"$FLEET" remove test-eng --dry-run >"$RM_OUT" 2>&1
RM_STATUS=$?
check "add --dry-run engineering (opencode) exits 0" "[ '$ENG_STATUS' -eq 0 ]"
check "add --dry-run operations exits 0" "[ '$OPS_STATUS' -eq 0 ]"
check "remove --dry-run exits 0" "[ '$RM_STATUS' -eq 0 ]"
check "engineering dry-run prints a numbered owner checklist" "grep -q '^[0-9]\. \[go\]' '$ENG_OUT'"
check "operations dry-run prints a numbered owner checklist" "grep -q '^[0-9]\. \[go\]' '$OPS_OUT'"
check "engineering dry-run states the stop before the seat invite" "grep -q 'stops before the Claude seat invitation' '$ENG_OUT'"
check "engineering opencode dry-run covers App plus user plus OpenCode plus herdr" "grep -q 'GitHub App' '$ENG_OUT' && grep -q 'Linux user' '$ENG_OUT' && grep -q 'OpenCode' '$ENG_OUT' && grep -q 'herdr' '$ENG_OUT'"
check "remove dry-run prints the manual-remainder table" "grep -q 'manual-remainder table' '$RM_OUT'"
# grep -v exits 1 on empty input, which pipefail turns into a pipeline
# failure on a clean tree: snapshot to a file with || true instead.
TREE_AFTER="$(mktemp)"
git -C "$REPO_ROOT" status --porcelain agents/ infra/agents/ | grep -v '^??' | sort >"$TREE_AFTER" || true
check "dry-runs leave the tree unmodified" "diff -q '$TREE_BEFORE' '$TREE_AFTER'"
check "no secret-value flags in fleet add/remove driver" "! grep -rEn -- '$VALUE_FLAGS' '$FLEET'"
ENG_ACTIONS="$(grep -c '^[0-9]\. \[go\]' "$ENG_OUT")"
OPS_ACTIONS="$(grep -c '^[0-9]\. \[go\]' "$OPS_OUT")"
echo "EVIDENCE add --kind engineering --harness opencode --dry-run: $((ENG_END-ENG_START))s, $ENG_ACTIONS owner actions (budget 15 min / ~8 actions)"
echo "EVIDENCE add --kind operations --dry-run: $((OPS_END-OPS_START))s, $OPS_ACTIONS owner actions (budget 15 min / ~8 actions)"
check "engineering dry-run evidence carries action count" "grep -q 'Total owner actions' '$ENG_OUT'"
check "operations dry-run evidence carries action count" "grep -q 'Total owner actions' '$OPS_OUT'"
rm -f "$ENG_OUT" "$OPS_OUT" "$RM_OUT" "$TREE_BEFORE" "$TREE_AFTER"

exit $fail
