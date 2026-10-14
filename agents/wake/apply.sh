#!/usr/bin/env bash
# Ships the wake service to hyprn-agents-wake-01 over IAP and provisions it.
# Run from the repository root by a gcp-admins member, after the owner's go.
set -euo pipefail
: "${CLOUDSDK_CONFIG:?set CLOUDSDK_CONFIG to the gcloud configuration dedicated to hyprn.ai}"
cd "$(git rev-parse --show-toplevel)"
tar -czf - agents/wake agents/fleet.yaml agents/fleet-render agents/fleet-validate |
  gcloud compute ssh hyprn-agents-wake-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap --quiet --command \
    'set -e; rm -rf ~/hyprn-wake; mkdir ~/hyprn-wake; tar -C ~/hyprn-wake -xzf -; sudo bash ~/hyprn-wake/agents/wake/provision.sh'
