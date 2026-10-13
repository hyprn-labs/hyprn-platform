#!/usr/bin/env bash
# Account-safeguard checks (ACC-04/05/06).
# Discovery finding (recorded here per plan): the wake service runs on
# hyprn-agents-wake-01 (separate VM, ADR-0002) as identity
# hyprn-agents-wake, whose custom role agentHostPower grants exactly
# compute.instances.get/start/stop on the host instance only
# (infra/agents/wake.tf). The host keeps its disk across idle stops because
# idle-stop issues systemctl poweroff (a stop), never a delete.
# Host-executed portions run as root on the agent host; owner-credential
# steps appear as documented commands with expected outputs, never as
# scripted logins. Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
WAKE_TF="$REPO_ROOT/infra/agents/wake.tf"
HOST_TF="$REPO_ROOT/infra/agents/host.tf"
IDLE_STOP="$REPO_ROOT/agents/host/files/hyprn-idle-stop"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

check "no user cloud credentials on host" "! ls /home/*/.[a-z]*cloud* /home/*/.config/gcloud/credentials.db 2>/dev/null | grep -q . && ! grep -rlsq '\"client_id\".*apps.googleusercontent' /home /root /etc 2>/dev/null"
check "no private-key files on host" "! grep -rlsq '\"private_key\"' /home /root /etc"
check "no credential files under agent homes" "! find /home/ada /home/codd -name '*credential*' -o -name 'application_default_credentials.json' 2>/dev/null | grep -q ."
check "no staging or prod roles or secrets on host" "! grep -rlsiE 'staging|prod' /run/hyprn-agents/secrets 2>/dev/null | grep -q . && ! compgen -G '/home/*/*staging*' >/dev/null && ! compgen -G '/home/*/*prod*' >/dev/null"
check "wake custom role grants only get, start, stop" "[ \"\$(grep -cE '^ *\"compute.instances.(get|start|stop)\"' '$WAKE_TF')\" = 3 ] && ! grep -qE 'compute\\.(instances\\.(delete|set[a-zA-Z]+)|[a-z]+\\.[a-zA-Z]+\\.admin)' '$WAKE_TF'"
check "wake power grant is instance-scoped" "grep -q 'resource \"google_compute_instance_iam_member\" \"wake_host_power\"' '$WAKE_TF'"
check "idle-stop powers off (disk kept), never deletes" "grep -q 'systemctl poweroff' '$IDLE_STOP' && ! grep -qE 'instances delete|delete-instance' '$IDLE_STOP'"
check "host boot disk declared in Terraform" "grep -q 'boot_disk' '$HOST_TF'"
check "wake identity binding grants only host power (owner credentials)" "gcloud compute instances get-iam-policy hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents --format=json 2>/dev/null | jq -e '[.bindings[] | select(.members[] | contains(\"hyprn-agents-wake\")) | .role] | sort == [\"projects/hyprn-agents/roles/agentHostPower\"]'"
check "wake holds no Slack connection while host runs (owner credentials)" "gcloud compute ssh hyprn-agents-wake-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap --quiet --command 'systemctl show hyprn-agents-wake.service -p ActiveState,SubState' 2>/dev/null | grep -qE 'ActiveState=inactive|SubState=dead'"
check "org-wide IAM matches declared roles only (owner credentials)" "ORG=1071176223527; gcloud organizations get-iam-policy \"\$ORG\" --format='json(bindings)' 2>/dev/null | jq -e '[.[] | .members[]] | unique | map(select(test(\"^group:gcp-admins@hyprn.ai$\") or test(\"serviceAccount:.*gserviceaccount.com$\"))) | length == ([.[] | .members[]] | unique | length)'"

exit $fail
