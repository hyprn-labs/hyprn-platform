#!/usr/bin/env bash
# Isolation checks on the agent host (ADR-0001 confirmation). Run as root on
# the host; exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AGENTS="$HERE/../../agents/host/agents.txt"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
md="http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/email"

check "root reaches metadata (control)" "curl -sf -m 5 -H Metadata-Flavor:Google $md"
check "no rootful Docker daemon" "! systemctl is-active --quiet docker.service"
check "metadata block loaded" "nft list table inet hyprn_agents"
check "idle-stop timer active" "systemctl is-active --quiet hyprn-idle-stop.timer"
check "Slack allowlist root-owned, not agent-writable" "[ ! -e /run/hyprn-agents/slack-allowed-users.json ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/slack-allowed-users.json)\" = root:644 ]"
check "no service-account key files on host" "! grep -rlsq '\"private_key\"' /home /root /etc"

while read -r name uid _; do
  run() { runuser -l "$name" -c "$1" </dev/null; }
  check "$name: home is private" "[ \"\$(stat -c %a /home/$name)\" = 700 ]"
  check "$name: no sudo or docker group" "! id -nG $name | grep -qwE 'sudo|docker|adm'"
  check "$name: DNS resolves" "run 'getent hosts github.com'"
  check "$name: outbound HTTPS" "run 'curl -sf -m 10 -o /dev/null https://api.github.com'"
  check "$name: metadata unreachable" "! run 'curl -sf -m 5 -H Metadata-Flavor:Google $md'"
  check "$name: rootless Docker" "run 'docker info --format {{.SecurityOptions}}' | grep -q rootless"
  check "$name: Claude Code installed" "run 'claude --version'"
  check "$name: Slack tokens private to the agent" "[ ! -e /run/hyprn-agents/secrets/$name/slack.env ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/secrets/$name/slack.env)\" = $name:400 ]"
  check "$name: Slack plugin installed" "run 'claude plugin list' | grep -q slack@hyprn-agents"
  for other in /home/*; do
    [ "$other" = "/home/$name" ] && continue
    check "$name: cannot read $other" "! run 'ls $other'"
  done
done < <(grep -vE '^\s*(#|$)' "$AGENTS")

exit $fail
