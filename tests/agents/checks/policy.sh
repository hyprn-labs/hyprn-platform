#!/usr/bin/env bash
# Claude Code organization policy (POL-01, POL-03): the policy Ada's Claude Code
# receives from the admin console matches the reviewed copy, and the Slack
# channel plugin comes from the root-owned local marketplace. Run as root on
# the host by tests/agents/run.sh.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REVIEWED="$HERE/../../../agents/policy/managed-settings.json"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

while read -r name _ harness _; do
  [ "$harness" = claude ] || continue
  live="/home/$name/.claude/remote-settings.json"
  check "$name: console policy matches agents/policy/managed-settings.json" "diff <(jq -S . '$live') <(jq -S 'del(.\"\$comment\")' '$REVIEWED')"
  check "$name: Slack plugin from the local marketplace" "runuser -l $name -c 'claude plugin marketplace list' </dev/null | grep -q /opt/hyprn-agents/marketplace"
  check "$name: marketplace root-owned, not agent-writable" "[ \"\$(stat -c %U /opt/hyprn-agents/marketplace)\" = root ] && ! runuser -l $name -c 'test -w /opt/hyprn-agents/marketplace' </dev/null"
done < <(grep -vE '^\s*(#|$)' "$HERE/../../../agents/host/agents.txt")
exit $fail
