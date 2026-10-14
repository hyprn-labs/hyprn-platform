#!/usr/bin/env bash
# Provisions the wake VM hyprn-agents-wake-01 (ADR-0002). Idempotent; run as root.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
[ "$(id -u)" -eq 0 ] || { echo "provision.sh must run as root" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive

apt-get update -q
apt-get install -y -q python3-websocket python3-yaml unattended-upgrades
systemctl enable --now unattended-upgrades >/dev/null

id hyprn-wake >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin hyprn-wake
install -d -m 0755 /opt/hyprn-agents/wake /etc/hyprn-agents
install -m 0644 "$HERE/wake.py" /opt/hyprn-agents/wake/wake.py
# Fleet registry (FLT-01) is the only agent declaration: validate fail-closed
# before installing anything, then render wake.json to the path wake.py reads
# (the renderer lists slack:true agents only, so a Slack-less agent can never
# gain token reads).
python3 "$HERE/../fleet-validate" "$HERE/../fleet.yaml" || { echo "fleet registry invalid; aborting wake provisioning" >&2; exit 1; }
python3 "$HERE/../fleet-render" --fleet "$HERE/../fleet.yaml" --wake-out /etc/hyprn-agents/wake.json
install -m 0644 "$HERE/hyprn-agents-wake.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable hyprn-agents-wake.service >/dev/null
systemctl restart hyprn-agents-wake.service
sleep 5
systemctl is-active hyprn-agents-wake.service
journalctl -u hyprn-agents-wake.service -n 5 --no-pager -o cat
