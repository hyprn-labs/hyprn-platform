#!/usr/bin/env bash
# Isolation checks on the agent host (ADR-0001 confirmation). Run as root on
# the host; exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AGENTS="$HERE/../../agents/host/agents.txt"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
OPENCODE_VERSION="$(sed -n 's/^OPENCODE_VERSION="\(.*\)"/\1/p' "$HERE/../../agents/host/provision.sh")"
md="http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/email"

check "root reaches metadata (control)" "curl -sf -m 5 -H Metadata-Flavor:Google $md"
check "no rootful Docker daemon" "! systemctl is-active --quiet docker.service"
check "metadata block loaded" "nft list table inet hyprn_agents"
check "idle-stop timer active" "systemctl is-active --quiet hyprn-idle-stop.timer"
check "Slack allowlist root-owned, not agent-writable" "[ ! -e /run/hyprn-agents/slack-allowed-users.json ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/slack-allowed-users.json)\" = root:644 ]"
check "OpenCode at the pinned version" "/usr/local/lib/opencode/opencode --version | grep -qF $OPENCODE_VERSION"
check "OpenCode policy root-owned, opencode provider only" "[ \"\$(stat -c %U:%a /etc/opencode/opencode.json)\" = root:644 ] && jq -e '.enabled_providers == [\"opencode\"]' /etc/opencode/opencode.json"
check "no service-account key files on host" "[ -z \"\$(grep -rlsE --include='*.json' '\"type\": *\"service_account\"' /home /root /etc | xargs -r -d '\\n' grep -ls '\"private_key\"')\" ]"

while read -r name uid harness _; do
  run() { runuser -l "$name" -c "$1" </dev/null; }
  check "$name: home is private" "[ \"\$(stat -c %a /home/$name)\" = 700 ]"
  check "$name: no sudo or docker group" "! id -nG $name | grep -qwE 'sudo|docker|adm'"
  check "$name: DNS resolves" "run 'getent hosts github.com'"
  check "$name: outbound HTTPS" "run 'curl -sf -m 10 -o /dev/null https://api.github.com'"
  check "$name: metadata unreachable" "! run 'curl -sf -m 5 -H Metadata-Flavor:Google $md'"
  check "$name: rootless Docker" "run 'docker info --format {{.SecurityOptions}}' | grep -q rootless"
  if [ "$harness" = claude ]; then
    check "$name: Claude Code installed" "run 'claude --version'"
    check "$name: Slack plugin installed" "run 'claude plugin list' | grep -q slack@hyprn-agents"
    check "$name: OpenCode refused" "run 'opencode --version 2>&1; true' | grep -q 'not $name'"
  else
    check "$name: OpenCode runs" "run 'opencode --version' | grep -qF $OPENCODE_VERSION"
    check "$name: no Slack tokens" "[ ! -e /run/hyprn-agents/secrets/$name/slack.env ]"
    check "$name: GitHub App limited to hyprn-platform" "run 'gh api installation/repositories --jq .repositories[].full_name' | grep -qx hyprn-labs/hyprn-platform && [ \"\$(run 'gh api installation/repositories --jq .total_count')\" = 1 ]"
  fi
  check "$name: Slack tokens private to the agent" "[ ! -e /run/hyprn-agents/secrets/$name/slack.env ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/secrets/$name/slack.env)\" = $name:400 ]"
  check "$name: GitHub token private to the agent" "[ ! -e /run/hyprn-agents/secrets/$name/github-token ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/secrets/$name/github-token)\" = $name:400 ]"
  check "$name: git commits as its GitHub App bot" "run 'git config --global user.email' | grep -q '\\[bot\\]@users.noreply.github.com'"
  check "$name: GitHub App token fresh (under 35 minutes)" "find /run/hyprn-agents/secrets/$name/github-token -mmin -35 | grep -q ."
  check "$name: gh works with the App token" "run 'gh api installation/repositories --jq .total_count' | grep -qE '^[1-9]'"
  for other in /home/*; do
    [ "$other" = "/home/$name" ] && continue
    check "$name: cannot read $other" "! run 'ls $other'"
  done
done < <(grep -vE '^\s*(#|$)' "$AGENTS")

exit $fail
