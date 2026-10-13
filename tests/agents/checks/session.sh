#!/usr/bin/env bash
# Live session checks (ACC-01/02/03, D-08): Slack permission relay,
# sender-allowlist silence, and in-session refusals per repository.
# Slack-driven steps are performed live by the owner at execution time and
# recorded as marker files per runbooks/agents/live/README.md — the script
# records each live outcome as a named check so the dated record captures
# it, and never simulates the sender. Host-executed portions run as root on
# the agent host. Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
LIVE="$REPO_ROOT/runbooks/agents/live"
ALLOWLIST_FILE="/run/hyprn-agents/slack-allowed-users.json"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
# A live outcome passes when its marker file exists with a date first line
# and an owner-principal second line.
live() { [ -f "$LIVE/$1.ok" ] && head -1 "$LIVE/$1.ok" | grep -qE '^20[0-9]{2}-[0-9]{2}-[0-9]{2}' && sed -n '2p' "$LIVE/$1.ok" | grep -qE '^owner: .'; }

check "relay precondition: allowlist root-owned, owner only" "[ \"\$(stat -c %U:%a '$ALLOWLIST_FILE')\" = root:644 ]"
check "relay: owner yes proceeds" "live relay-owner-yes"
check "relay: owner no stops" "live relay-owner-no"
check "relay: non-owner reply rejected" "live relay-non-owner-rejected"
check "allowlist: non-listed senders get no reaction" "live allowlist-silence"

for repo in hyprn-platform hyprn-mvp; do
  short="$repo"; short="${short#hyprn-}"
  check "refusals ($repo): merge refused with variants" "live refuse-$short-merge"
  check "refusals ($repo): push-to-main refused with variants" "live refuse-$short-push-main"
  check "refusals ($repo): force-push refused with variants" "live refuse-$short-force-push"
  check "refusals ($repo): bypass mode refused" "live refuse-$short-bypass"
done

exit $fail
