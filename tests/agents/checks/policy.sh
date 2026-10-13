#!/usr/bin/env bash
# Agent-policy checks (POL-01..04). Static content assertions run anywhere;
# host-executed portions run as root on the agent host.
# Exits non-zero if any check fails.
# POL-03 three-part marketplace evidence: host-runnable assertions execute
# here; the admin-console match defers to the owner checklist in
# runbooks/agents/claude.md (never a scripted console login, per D-08).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
POLICY="$REPO_ROOT/agents/policy/managed-settings.json"
ALLOWLIST="$REPO_ROOT/agents/policy/egress-allowlist.txt"
RUNBOOK="$REPO_ROOT/runbooks/agents/claude.md"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

check "policy file exists and is valid JSON" "python3 -m json.tool '$POLICY'"
check "deny covers merge family" "jq -e '[.permissions.deny[] | select(test(\"gh pr merge\"))] | length >= 1' '$POLICY'"
check "deny covers push-to-main spellings" "jq -e '[.permissions.deny[] | select(test(\"git push\"))] | length >= 5' '$POLICY'"
check "deny covers -C directory form" "jq -e '[.permissions.deny[] | select(test(\"git -C\"))] | length >= 1' '$POLICY'"
check "deny covers force-push flags" "jq -e '[.permissions.deny[] | select(test(\"force\") or test(\"-f\"))] | length >= 2' '$POLICY'"
check "deny covers admin-merge and branch-protection API paths" "jq -e '[.permissions.deny[] | select(test(\"admin\") or test(\"protection\"))] | length >= 2' '$POLICY'"
check "at least eight deny entries" "jq -e '.permissions.deny | length >= 8' '$POLICY'"
check "no allow entry overlaps a denied merge/push spelling" "! jq -r '.permissions.allow[]' '$POLICY' | grep -qE 'push|merge|admin|force|main'"
check "ask covers read-only gh api use" "jq -e '.permissions.ask | index(\"Bash(gh api *)\")' '$POLICY'"
check "managed-only locks enabled" "jq -e '.allowManagedPermissionRulesOnly == true and .permissions.disableBypassPermissionsMode == \"disable\"' '$POLICY'"
check "marketplace pinned to hyprn-agents source" "jq -e '.strictKnownMarketplaces == [{\"source\": \"github\", \"repo\": \"hyprn-labs/hyprn-agents\"}]' '$POLICY'"
check "sandbox enforced with managed-domains-only" "jq -e '.sandbox.enabled == true and .sandbox.failIfUnavailable == true and .sandbox.allowUnsandboxedCommands == false and .sandbox.network.allowManagedDomainsOnly == true' '$POLICY'"
check "sandbox network allowlist seeded" "jq -e '.sandbox.network.allowedDomains | length >= 3' '$POLICY'"
check "minimum version floor present" "jq -e '.requiredMinimumVersion | length > 0' '$POLICY'"
check "placeholder allowlist exists with seed hosts" "[ \"\$(grep -v '^#' '$ALLOWLIST' | grep -cE '^[a-z0-9.-]+\\.[a-z]+')\" -ge 3 ]"
check "allowlist header names M3 enforcement" "grep -qE 'M3|Phase 7|EGR-02' '$ALLOWLIST'"
check "POL-03 console-match step deferred to owner checklist" "grep -qE 'console|diff' '$RUNBOOK'"

exit $fail
