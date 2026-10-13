#!/usr/bin/env bash
# Gateway review checks (CP-01, OPS-01, ACC-09, COST-01). Static content
# assertions run anywhere; terraform validate/plan runs at the owner-go
# apply step (terraform binary absent here — noted, not failed).
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
GATEWAY="$REPO_ROOT/infra/agents/gateway.tf"
CONTROLLER="$REPO_ROOT/infra/agents/controller.tf"
BOOLE="$REPO_ROOT/infra/agents/boole.tf"
CONFIG="$REPO_ROOT/agents/gateway/litellm-config.yaml"
RUNBOOK="$REPO_ROOT/runbooks/agents/control-plane-go.md"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

check "gateway config parses with a model list" "python3 -c \"import yaml; d=yaml.safe_load(open('$CONFIG')); assert 'model_list' in d and 'general_settings' in d\""
check "gateway config carries the Fireworks default binding" "grep -q 'fireworks_ai/' '$CONFIG'"
check "gateway config carries the Claude binding beside it" "grep -q 'anthropic/' '$CONFIG'"
check "gateway config master key is a reference, not a value" "grep -q 'os.environ/LITELLM_MASTER_KEY' '$CONFIG'"
check "gateway uses internal-only ingress" "grep -q 'INGRESS_TRAFFIC_INTERNAL_ONLY' '$GATEWAY'"
check "gateway wires the database URL by reference" "grep -v '^#' '$GATEWAY' | grep -q 'secret_key_ref'"
check "gateway secret wiring carries no credential value" "! grep -v '^#' '$GATEWAY' | grep -qiE 'BEGIN.*PRIVATE|sk-[A-Za-z0-9]{10,}'"
check "gateway has no public invoker grant" "! grep -v '^#' '$GATEWAY' | grep -q 'allUsers\\|allAuthenticatedUsers'"
check "gateway declares per-loop key plus budget blocks" "grep -q 'loop_keys' '$GATEWAY'"
check "gateway declares the spend-state database" "grep -q 'google_sql_database_instance' '$GATEWAY'"
check "controller declares a dedicated service account" "[ \"\$(grep -v '^#' '$CONTROLLER' | grep -c 'service_account')\" -ge 1 ]"
check "boole grants accessors only to named accounts" "! grep -q 'allUsers\|domain:' '$BOOLE'"
check "boole non-comment lines carry no credential value" "! grep -v '^#' '$BOOLE' | grep -qiE 'BEGIN.*PRIVATE|sk-[A-Za-z0-9]{10,}|xox[bap]-'"
check "boole carries the COST-01 budget placeholder" "grep -q 'COST-01' '$BOOLE'"
check "go-runbook lists the provider-keys step" "grep -qiE 'fireworks.*anthropic.*openai|provider key' '$RUNBOOK'"
check "go-runbook lists the budget step" "grep -qiE 'budget' '$RUNBOOK'"
check "go-runbook lists the Slack app install step" "grep -qiE 'slack app' '$RUNBOOK'"
check "go-runbook lists the exact-plan apply step" "grep -qiE 'terraform.*apply|apply.*terraform' '$RUNBOOK'"
check "go-runbook lists the live test-loop run step" "grep -qiE 'live.*run|test-loop' '$RUNBOOK'"
check "go-runbook entries carry verification lines" "grep -q 'Verify' '$RUNBOOK'"
skip "terraform validate plus plan" "terraform binary absent — runs at the owner-go apply step"

exit $fail
