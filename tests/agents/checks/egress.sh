#!/usr/bin/env bash
# Egress-observation checks (EGR-01, observe mode).
# Run as root on the agent host; exits non-zero if any check fails.
# Proves: drop-direct for agent users AND their rootless containers, working
# proxy with per-agent attribution and allow-all posture, live DNS, and
# per-agent log flow to Cloud Logging. Static config-shape asserts run
# anywhere; live host-only probes SKIP off-host rather than false-failing.
# The live drop tests run here on the host; the Cloud Logging flow query needs
# the host's gcloud identity. Enforcement (allowlist + default-deny) stays
# Phase 7 (EGR-02); nothing here asserts a deny.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
NFT="$REPO_ROOT/agents/host/files/egress.nft"
SQUID="$REPO_ROOT/agents/host/files/squid-hyprn.conf"
AGENTS="$(mktemp)"
# Fleet registry (FLT-01) is the only declaration: render agents.txt to an
# ephemeral file; every parse loop below is untouched.
python3 "$REPO_ROOT/agents/fleet-render" --agents-out "$AGENTS" || exit 1
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
# Live probes run only on the agent host as root with the firewall table
# loaded; everywhere else they SKIP instead of false-failing.
ON_HOST=false
if [ "$(id -u)" -eq 0 ] && command -v nft >/dev/null 2>&1 && nft list table inet hyprn_agents >/dev/null 2>&1; then
  ON_HOST=true
fi
live() { if [ "$ON_HOST" = true ]; then check "$1" "$2"; else echo "SKIP $1 (not on agent host)"; fi; }

# --- static: observe-mode config shape (runs anywhere) ---
check "proxy config declares one listen port per agent" "[ \"\$(grep -cE '^http_port' '$SQUID')\" -eq 2 ]"
check "proxy config declares an access log with agent identifier" "grep -v '^#' '$SQUID' | grep -qE '^access_log' && grep -v '^#' '$SQUID' | grep -q 'logformat.*%lp'"
check "proxy config allows all on each agent port (observe mode)" "grep -v '^#' '$SQUID' | grep -qE '^http_access allow ada_port$' && grep -v '^#' '$SQUID' | grep -qE '^http_access allow codd_port$'"
check "proxy config has no deny rules (observe mode: no blocking)" "! grep -v '^#' '$SQUID' | grep -qE '^http_access deny'"
check "proxy config references no allowlist (observe mode: unenforced)" "! grep -v '^#' '$SQUID' | grep -qiE 'dstdomain|allowlist'"

# --- live: host-only probes (SKIP off-host) ---
live "firewall table loaded" "nft list table inet hyprn_agents"
live "drop-direct rules present for login UIDs" "nft list table inet hyprn_agents | grep -q 'skuid 20000-20999.*dport .*80.*443.*drop'"
live "drop-direct rules present for container subordinate ranges" "nft list table inet hyprn_agents | grep -q 'skuid 100000-231071.*dport .*80.*443.*drop'"
live "DNS allowances precede every drop rule" "nft list table inet hyprn_agents | awk '/dport 53 accept/{a=NR} /counter drop/{if(d==0)d=NR} END{exit !(a<d)}'"
live "metadata block preserved" "nft list table inet hyprn_agents | grep -q '169.254.169.254 counter reject'"
live "proxy ports accepted for agent UIDs" "nft list table inet hyprn_agents | grep -q 'dport .*3128.*3129.*accept'"
live "proxy listens on each per-agent port" "(ss -ltn | grep -q ':3128 ') && (ss -ltn | grep -q ':3129 ')"

while read -r name uid harness _; do
  run() { runuser -l "$name" -c "$1" </dev/null; }
  port=3128; [ "$name" = codd ] && port=3129
  live "$name: DNS still resolves" "run 'getent hosts github.com'"
  live "$name: direct outbound drops (proxy bypassed)" "! run 'curl --noproxy * -sf -m 10 -o /dev/null https://example.com'"
  live "$name: representative destination succeeds through the proxy" "run 'https_proxy=http://127.0.0.1:$port http_proxy=http://127.0.0.1:$port curl -sf -m 15 -o /dev/null https://github.com'"
  live "$name: arbitrary destination succeeds through the proxy (observe: allow-all)" "run 'https_proxy=http://127.0.0.1:$port http_proxy=http://127.0.0.1:$port curl -sf -m 15 -o /dev/null https://example.com'"
  live "$name: proxied request logged with agent port label" "grep 'example.com' /var/log/squid/access.log | grep -qE ' $port( |$)'"
  # Container tests assume host.containers.internal resolves to the host from
  # rootless containers at provisioning time; the host run proves or corrects it.
  live "$name: container direct outbound drops" "! run 'docker run --rm --env NO_PROXY=* --env no_proxy=* curlimages/curl -sf -m 10 -o /dev/null https://example.com'"
  live "$name: container destination succeeds through the proxy" "run 'docker run --rm --env https_proxy=http://host.containers.internal:$port --env http_proxy=http://host.containers.internal:$port curlimages/curl -sf -m 15 -o /dev/null https://github.com'"
done < <(grep -vE '^\s*(#|$)' "$AGENTS")

live "recent per-agent destination entries in Cloud Logging" "gcloud logging read 'resource.type=\"gce_instance\" AND jsonPayload.agent_label=~\"ada|codd\"' --freshness=1h --limit=1 --project=hyprn-agents --format='value(timestamp)' | grep -qE '[0-9]{4}-[0-9]{2}-[0-9]{2}'"

rm -f "$AGENTS"
exit $fail
