#!/usr/bin/env bash
# One-command acceptance harness (ACC-08): runs host-checks.sh unchanged first,
# then every executable tests/agents/checks/*.sh, and appends a dated record
# under runbooks/agents/. Exits non-zero if any domain fails.
# A failing domain never masks later domains: each script runs in a guarded
# invocation whose status is recorded before continuing.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
RECORDS="$REPO_ROOT/runbooks/agents"
DATE="$(date +%F)"
STAMP="$(date -u +%FT%TZ)"
HASH="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
RECORD="$RECORDS/checks-$DATE.md"

declare -a NAMES=()
declare -a RESULTS=()
overall=PASS

run_one() {
  local label="$1" script="$2"
  local out status
  set +e
  out="$("$script" 2>&1)"
  status=$?
  set -e
  printf '%s\n' "$out"
  if [ "$status" -eq 0 ]; then
    echo "SCRIPT-PASS $label"
    NAMES+=("$label"); RESULTS+=("PASS")
  else
    echo "SCRIPT-FAIL $label (exit $status)"
    NAMES+=("$label"); RESULTS+=("FAIL")
    overall=FAIL
  fi
}

echo "=== host-checks ==="
run_one "host-checks" "$HERE/host-checks.sh"

for script in "$HERE"/checks/*.sh; do
  [ -e "$script" ] || continue
  [ -x "$script" ] || chmod +x "$script"
  echo "=== checks/$(basename "$script") ==="
  run_one "checks/$(basename "$script" .sh)" "$script"
done

{
  echo ""
  echo "## Run $STAMP (checkout $HASH)"
  echo ""
  echo "| Script | Result |"
  echo "|---|---|"
  for i in "${!NAMES[@]}"; do
    echo "| ${NAMES[$i]} | ${RESULTS[$i]} |"
  done
  echo ""
  echo "Overall: $overall"
} >> "$RECORD"
echo "Record appended to $RECORD"

[ "$overall" = PASS ]
