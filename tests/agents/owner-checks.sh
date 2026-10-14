#!/usr/bin/env bash
# Safety checks that need the platform owner's identities: Google Cloud IAM and
# detection, GitHub organization settings, and the reviewed policy files. Run
# from the repository root on the owner's workstation with the HYPRN
# configurations (CLOUDSDK_CONFIG, GH_CONFIG_DIR). Read-only. Exits non-zero
# if any check fails; SKIP marks checks waiting on a deferred purchase.
set -uo pipefail
: "${CLOUDSDK_CONFIG:?set CLOUDSDK_CONFIG to the gcloud configuration dedicated to hyprn.ai}"
: "${GH_CONFIG_DIR:?set GH_CONFIG_DIR to the gh configuration dedicated to hyprn-labs}"
cd "$(git rev-parse --show-toplevel)"
ORG=1071176223527 FOLDER=86446816109 PROJECT=hyprn-agents GH_ORG=hyprn-labs
ADMINS="group:gcp-admins@hyprn.ai"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

echo "== reviewed files"
check "ruleset: valid, active on main, no deletion or force push, code-owner approval" "jq -e '.enforcement == \"active\" and (.conditions.ref_name.include == [\"refs/heads/main\"]) and ([.rules[].type] | contains([\"deletion\",\"non_fast_forward\",\"pull_request\"])) and (.rules[] | select(.type == \"pull_request\") | .parameters.require_code_owner_review and .parameters.required_approving_review_count >= 1)' agents/github/main-ruleset.json"
check "ruleset: only organization admins bypass, through pull requests" "jq -e '.bypass_actors == [{\"actor_id\":1,\"actor_type\":\"OrganizationAdmin\",\"bypass_mode\":\"pull_request\"}]' agents/github/main-ruleset.json"
check "CODEOWNERS names the owners team" "grep -qx '\\* @hyprn-labs/owners' CODEOWNERS"
check "policy: channels and the Slack plugin allowed, bypass mode disabled" "jq -e '.channelsEnabled == true and (.allowedChannelPlugins | index({\"marketplace\":\"hyprn-agents\",\"plugin\":\"slack\"})) and .permissions.disableBypassPermissionsMode == \"disable\"' agents/policy/managed-settings.json"
check "policy: merges, pushes to main and force pushes denied" "jq -e '[.permissions.deny[]] | (map(select(test(\"merge\"))) | length > 0) and (map(select(test(\"main\"))) | length > 0) and (map(select(test(\"force\"))) | length > 0)' agents/policy/managed-settings.json"

echo "== Google Cloud"
check "organization: roles held only by the admins group" "[ \"\$(gcloud organizations get-iam-policy $ORG --format=json | jq -r '[.bindings[].members[]] | unique | join(\",\")')\" = '$ADMINS' ]"
check "agents folder: no role held by a person" "[ -z \"\$(gcloud resource-manager folders get-iam-policy $FOLDER --format=json | jq -r '.bindings[]?.members[] | select(startswith(\"user:\"))')\" ]"
check "agents project: no role held by a person" "[ -z \"\$(gcloud projects get-iam-policy $PROJECT --format=json | jq -r '.bindings[].members[] | select(startswith(\"user:\"))')\" ]"
check "Secret Manager data reads are audited" "gcloud projects get-iam-policy $PROJECT --format=json | jq -e '.auditConfigs[]? | select(.service == \"secretmanager.googleapis.com\") | .auditLogConfigs[] | select(.logType == \"DATA_READ\")'"
policies() {
  curl -sf -H "Authorization: Bearer $(gcloud auth print-access-token)" -H "x-goog-user-project: hyprn-bootstrap" \
    "https://monitoring.googleapis.com/v3/projects/$PROJECT/alertPolicies"
}
for policy in "hyprn agents: unexpected secret access" "hyprn agents: IAM policy change"; do
  check "alert enabled with the admins channel: $policy" "policies | jq -e --arg n \"$policy\" '.alertPolicies[]? | select(.displayName == \$n and .enabled == true and (.notificationChannels | length) > 0)'"
done
WAKE="serviceAccount:hyprn-agents-wake@$PROJECT.iam.gserviceaccount.com"
check "wake identity: only log and metric writing at project level" "[ \"\$(gcloud projects get-iam-policy $PROJECT --format=json | jq -r --arg m $WAKE '[.bindings[] | select(.members | index(\$m)) | .role] | sort | join(\",\")')\" = 'roles/logging.logWriter,roles/monitoring.metricWriter' ]"
check "wake identity: only get, start and stop, on the host only" "[ \"\$(gcloud iam roles describe agentHostPower --project=$PROJECT --format=json | jq -r '.includedPermissions | sort | join(\",\")')\" = 'compute.instances.get,compute.instances.start,compute.instances.stop' ] && gcloud compute instances get-iam-policy hyprn-agents-host-01 --zone=europe-west1-b --project=$PROJECT --format=json | jq -e --arg m $WAKE '.bindings == [{\"role\":\"projects/$PROJECT/roles/agentHostPower\",\"members\":[\$m]}]'"
if [ "$(gcloud compute instances describe hyprn-agents-host-01 --zone=europe-west1-b --project=$PROJECT --format='value(status)')" = RUNNING ]; then
  check "wake service holds no Slack connection while the host runs" "gcloud compute ssh hyprn-agents-wake-01 --zone=europe-west1-b --project=$PROJECT --tunnel-through-iap --quiet --command 'sudo journalctl -u hyprn-agents-wake --no-pager | grep -E \"(connected|disconnected)\" | tail -1' 2>/dev/null | grep -q 'disconnected; host is running'"
else
  skip "wake service holds no Slack connection while the host runs" "host stopped"
fi

echo "== GitHub"
check "organization requires two-factor authentication" "gh api orgs/$GH_ORG --jq .two_factor_requirement_enabled | grep -qx true"
check "owners team exists" "gh api orgs/$GH_ORG/teams/owners"
if [ "$(gh api orgs/$GH_ORG --jq .plan.name)" = free ]; then
  skip "ruleset on main in every repository" "GitHub Free: rulesets on private repositories need the Team plan"
else
  for repo in $(gh repo list $GH_ORG --json name --jq '.[].name'); do
    check "$repo: main-protection ruleset active" "gh api repos/$GH_ORG/$repo/rulesets --jq '.[] | select(.name == \"main-protection\" and .enforcement == \"active\")' | grep -q ."
  done
fi
exit $fail
