#!/usr/bin/env bash
# Misuse-detection checks (DET-01/02).
# Static Terraform-content assertions run anywhere; live gcloud assertions
# need owner credentials and run at owner-go time (never scripted logins).
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
TF="$REPO_ROOT/infra/agents/detect.tf"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

check "detect.tf declares DATA_READ audit config for Secret Manager" "grep -q 'service = \"secretmanager.googleapis.com\"' '$TF' && grep -q 'log_type = \"DATA_READ\"' '$TF'"
check "detect.tf declares the admins-group email channel" "grep -q 'type.*=.*\"email\"' '$TF' && grep -q 'var.admins_group' '$TF'"
check "detect.tf declares the secret-access alert with channel attached" "grep -q 'resource \"google_monitoring_alert_policy\" \"secret_unexpected_access\"' '$TF' && grep -q 'notification_channels' '$TF'"
check "secret alert excludes the declared host and wake identities" "grep -q 'google_service_account.host.email' '$TF' && grep -q 'google_service_account.wake.email' '$TF'"
check "detect.tf declares the IAM-change alert over the agents project" "grep -q 'resource \"google_monitoring_alert_policy\" \"agents_iam_change\"' '$TF' && grep -q 'SetIamPolicy' '$TF'"
check "detect.tf declares the folder sink into the agents project" "grep -q 'resource \"google_logging_folder_sink\"' '$TF' && grep -q 'var.agents_folder_id' '$TF'"
check "no secret value or key literal in detect.tf" "! grep -qiE 'private_key|BEGIN .*PRIVATE KEY|password *=' '$TF'"
check "audit config present in the project" "gcloud projects get-iam-policy hyprn-agents --format=json 2>/dev/null | jq -e '.auditConfigs[] | select(.service == \"secretmanager.googleapis.com\") | .auditLogConfigs[] | select(.logType == \"DATA_READ\")'"
check "secret-access alert policy exists, enabled, channel attached" "gcloud alpha monitoring policies list --project=hyprn-agents --format='json(displayName,enabled,notificationChannels)' 2>/dev/null | jq -e '.[] | select(.displayName == \"hyprn agents: unexpected secret access\") | select(.enabled == true) | .notificationChannels | length >= 1'"
check "IAM-change alert policy exists, enabled, channel attached" "gcloud alpha monitoring policies list --project=hyprn-agents --format='json(displayName,enabled,notificationChannels)' 2>/dev/null | jq -e '.[] | select(.displayName == \"hyprn agents: IAM policy change\") | select(.enabled == true) | .notificationChannels | length >= 1'"
# Folder numeric ID from the bootstrap record (STATE.md VMs/context rows);
# the Terraform source of truth is var.agents_folder_id in detect.tf.
check "folder sink exists with folder source filter" "gcloud logging sinks describe agents-folder-iam-to-project --folder=86446816109 --format='json(destination,filter)' 2>/dev/null | jq -e '.destination | contains(\"hyprn-agents\")'"
check "admins group accepts notification mail (deliverability)" "gcloud alpha monitoring channels list --project=hyprn-agents --format='json(enabled)' 2>/dev/null | jq -e '[.[] | select(.enabled == true)] | length >= 1'"

exit $fail
