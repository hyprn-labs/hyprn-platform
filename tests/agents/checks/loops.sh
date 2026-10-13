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

check "validator exits 0 on the test fixture" "python3 '$VALIDATOR' '$FIXTURE'"
shopt -s nullglob
REGISTRY_FILES=("$REPO_ROOT"/agents/loops/*.yaml "$REPO_ROOT"/agents/loops/testdata/*.yaml)
if [ "${#REGISTRY_FILES[@]}" -gt 0 ]; then
  check "validator exits 0 over every registry file" "python3 '$VALIDATOR' ${REGISTRY_FILES[*]}"
else
  skip "validator over every registry file" "no registry files yet"
fi

if python3 -c "import yaml" >/dev/null 2>&1; then
  check "fixture carries every REQUIRED field" "python3 -c \"import yaml; d=yaml.safe_load(open('$FIXTURE')); assert {'name','owner','trigger','steps','tools','autonomy','budget','egress_allowlist','runtime','eval_set','promotion_rule'} <= set(d)\""
  check "fixture allowlist is non-empty" "python3 -c \"import yaml; assert yaml.safe_load(open('$FIXTURE'))['egress_allowlist']\""
  check "fixture autonomy uses A-levels only" "python3 -c \"import yaml; assert set(yaml.safe_load(open('$FIXTURE'))['autonomy'].values()) <= {'A0','A1','A2','A3'}\""
else
  skip "fixture REQUIRED-field probe" "no yaml parser on PATH"
  skip "fixture allowlist probe" "no yaml parser on PATH"
  skip "fixture autonomy probe" "no yaml parser on PATH"
fi
check "fixture allowlist block is non-empty" "[ \"\$(sed -n '/egress_allowlist:/,/^[a-z]/p' '$FIXTURE' | grep -c '^\s*-')\" -ge 1 ]"

# Negative probe: an unknown autonomy level must fail validation.
BAD="$(mktemp)"
printf 'name: bad\nowner: o\ntrigger: {type: poll}\nsteps: [a]\ntools: [t]\nautonomy: {x: A9}\nbudget: {amount_usd: 1}\negress_allowlist: [gateway.internal]\nruntime: {binding: b}\neval_set: e\npromotion_rule: {min_pass_rate: 0.9}\n' > "$BAD"
check "negative probe: bad autonomy level is rejected" "! python3 '$VALIDATOR' '$BAD'"
rm -f "$BAD"

exit $fail
