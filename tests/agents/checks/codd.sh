#!/usr/bin/env bash
# Codd scope checks (CODD-01, D-03/D-04): the Codd App installation resolves
# to exactly hyprn-platform and hyprn-mvp with per-repo assertions; tokens
# rotate within the one-hour bound; the codd home is private and unreachable
# from the other agent; the managed OpenCode config is root-owned with the
# expected provider restriction and deny families; Codd has no Slack app or
# Workspace presence. Host-executed portions run as root on the agent host.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
MANAGED="$REPO_ROOT/agents/host/files/opencode.json"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

if ! id codd >/dev/null 2>&1; then
  echo "SKIP codd live checks (no local user codd; not on agent host)"
else
  run() { runuser -l codd -c "$1" </dev/null; }
  check "codd: App installation covers hyprn-platform" "run 'gh api installation/repositories --jq .repositories[].full_name' | grep -qx hyprn-labs/hyprn-platform"
  check "codd: App installation covers hyprn-mvp" "run 'gh api installation/repositories --jq .repositories[].full_name' | grep -qx hyprn-labs/hyprn-mvp"
  check "codd: App installation total count is 2" "[ \"\$(run 'gh api installation/repositories --jq .total_count')\" = 2 ]"
  check "codd: installation token fresh (under 60 minutes)" "find /run/hyprn-agents/secrets/codd/github-token -mmin -60 | grep -q ."
  check "codd: home is private" "[ \"\$(stat -c %a /home/codd)\" = 700 ]"
  if id ada >/dev/null 2>&1; then
    check "codd: home unreachable from ada" "! runuser -l ada -c 'ls /home/codd' </dev/null"
  fi
  check "codd: no Slack tokens" "[ ! -e /run/hyprn-agents/secrets/codd/slack.env ]"
fi

check "codd: managed OpenCode config root-owned on host" "[ \"\$(stat -c %U:%a /etc/opencode/opencode.json)\" = root:644 ]"
check "codd: managed config restricts to opencode provider" "jq -e '.enabled_providers == [\"opencode\"]' /etc/opencode/opencode.json"
check "codd: managed config denies push-to-main variants" "jq -e '(.permission.bash | to_entries | map(select(.value == \"deny\" and (.key | test(\"git push\")))) | length) >= 5' /etc/opencode/opencode.json"
check "codd: managed config denies merge and asks for gh api" "jq -e '.permission.bash[\"gh pr merge*\"] == \"deny\" and .permission.bash[\"gh api *\"] == \"ask\"' /etc/opencode/opencode.json"
check "codd: reviewed copy matches host copy" "diff '$MANAGED' /etc/opencode/opencode.json"
check "codd: no Slack app (not a steered agent)" "! sed -n '/variable \"slack_agents\"/,/^}/p' '$REPO_ROOT/infra/agents/variables.tf' | grep -q codd"
check "codd: no Slack secret on host" "[ ! -e /run/hyprn-agents/secrets/codd/slack.env ]"

exit $fail
