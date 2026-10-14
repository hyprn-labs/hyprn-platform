#!/usr/bin/env bash
# Egress observation (EGR-01). Run as root on the host by tests/agents/run.sh.
# Always: proxy, log shipping and the direct-connection log are in place. While
# the proxy is switched on: each agent's traffic goes through it and is logged
# under its name, and Ada's Slack connection works through it.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

check "egress: proxy running with a valid configuration" "systemctl is-active --quiet squid && ! squid -k parse 2>&1 | grep -qE 'FATAL|ERROR'"
check "egress: Ops Agent running" "systemctl is-active --quiet google-cloud-ops-agent"
check "egress: direct connections of agent users logged" "nft list chain inet hyprn_agents output | grep -q 'hyprn-egress-direct'"
check "egress: nothing refused but the metadata server" "[ \"\$(nft list chain inet hyprn_agents output | grep -cE 'reject|drop')\" = 2 ]"

on=$([ -e /etc/hyprn-agents/egress-proxy ] && echo yes || echo no)
echo "INFO egress proxy switched on: $on"
while read -r name _ harness _; do
  run() { runuser -l "$name" -c "$1" </dev/null; }
  port="$(cat "/etc/hyprn-agents/agents/$name.proxy-port" 2>/dev/null)"
  check "$name: proxy port assigned and listening" "[ -n '$port' ] && ss -Hltn 'sport = :$port' | grep -q 127.0.0.1"
  [ "$on" = yes ] || continue
  check "$name: shell uses the proxy" "run 'echo \$HTTPS_PROXY' | grep -qx 'http://127.0.0.1:$port'"
  marker="hyprn-check-$(date +%s)-$name"
  check "$name: HTTPS through the proxy, logged under its name" "run 'curl -sf -m 15 -o /dev/null https://api.github.com/zen?$marker'; sleep 2; grep -q 'agent=$name .*api.github.com' /var/log/squid/access.log"
  check "$name: Docker uses the proxy" "run 'docker info --format {{.HTTPSProxy}}' | grep -q '127.0.0.1:$port'"
  if [ "$harness" = claude ]; then
    check "$name: Slack connected since the last session start" "since=\$(systemctl show -p ActiveEnterTimestamp --value hyprn-agent@$name); tail -50 /home/$name/.local/state/hyprn-slack/server.log | grep 'socket mode connected' | tail -1 | cut -c1-19 | xargs -I{} date -d {} +%s | awk -v s=\$(date -d \"\$since\" +%s) '{exit !(\$1 >= s)}'"
  fi
done < <(grep -vE '^\s*(#|$)' "$HERE/../../../agents/host/agents.txt")
exit $fail
