#!/usr/bin/env bash
# One command for the host's safety checks (ACC-08): host-checks.sh, then every
# checks/*.sh. Run as root on the agent host (agents/host/apply.sh runs it after
# provisioning). Prints each result, keeps a dated record in
# /var/lib/hyprn-agents/checks/ and exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RECORDS="${RECORDS:-/var/lib/hyprn-agents/checks}"
install -d -m 0750 "$RECORDS"
record="$RECORDS/$(date -u +%F).md"
out="$(mktemp)"
status=0
for script in "$HERE/host-checks.sh" "$HERE"/checks/*.sh; do
  [ -e "$script" ] || continue
  echo "== $(basename "$script")" | tee -a "$out"
  bash "$script" 2>&1 | tee -a "$out" || status=1
done
pass=$(grep -c '^PASS' "$out"); fail=$(grep -c '^FAIL' "$out")
{
  printf '\n## %s\n\n%s pass, %s fail\n\n' "$(date -u +%FT%TZ)" "$pass" "$fail"
  grep -E '^(==|FAIL)' "$out"
} >> "$record"
rm -f "$out"
echo "== $pass pass, $fail fail (record: $record)"
exit $status
