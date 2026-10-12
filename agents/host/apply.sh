#!/usr/bin/env bash
# Ships the provisioning to the agent host over IAP and runs it as root.
# Run from the repository root by a gcp-admins member, after the owner's go.
set -euo pipefail
: "${CLOUDSDK_CONFIG:?set CLOUDSDK_CONFIG to the gcloud configuration dedicated to hyprn.ai}"
HOST="${HOST:-hyprn-agents-host-01}"
ZONE="${ZONE:-europe-west1-b}"
PROJECT="${PROJECT:-hyprn-agents}"
cd "$(git rev-parse --show-toplevel)"
tar -czf - agents/host agents/roles agents/marketplace tests/agents |
  gcloud compute ssh "$HOST" --zone="$ZONE" --project="$PROJECT" --tunnel-through-iap --quiet --command \
    'set -e; rm -rf ~/hyprn-provision; mkdir ~/hyprn-provision; tar -C ~/hyprn-provision -xzf -;
     sudo bash ~/hyprn-provision/agents/host/provision.sh;
     sudo bash ~/hyprn-provision/tests/agents/host-checks.sh'
