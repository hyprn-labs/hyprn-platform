#!/usr/bin/env bash
# GitHub-protection checks (GHE-01 definition review, GHE-03 interim posture).
# Run as root on the agent host; static file assertions also run anywhere.
# Exits non-zero if any check fails. Per D-01 (Phase 1 CONTEXT) the ruleset
# file is review-only: no task here calls any ruleset write API.
# Per D-03/D-04 each agent App installation must resolve to exactly the two
# repositories hyprn-platform and hyprn-mvp.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
RULESET="$REPO_ROOT/agents/github/main-ruleset.json"
CODEOWNERS="$REPO_ROOT/CODEOWNERS"
AGENTS="$REPO_ROOT/agents/host/agents.txt"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

check "ruleset file is valid JSON" "python3 -m json.tool '$RULESET'"
check "ruleset bypass actor list is empty (no App bypass)" "[ \"\$(jq -r '.bypass_actors | length' '$RULESET')\" = 0 ]"
check "ruleset name present" "jq -e '.name | length > 0' '$RULESET'"
check "ruleset enforcement is active" "jq -e '.enforcement == \"active\"' '$RULESET'"
check "ruleset targets the main ref" "jq -e '.conditions.ref_name.include | index(\"refs/heads/main\")' '$RULESET'"
check "ruleset has at least four rules" "jq -e '.rules | length >= 4' '$RULESET'"
check "ruleset blocks non-fast-forward pushes" "jq -e '.rules | map(.type) | index(\"non_fast_forward\")' '$RULESET'"
check "ruleset blocks branch deletion" "jq -e '.rules | map(.type) | index(\"deletion\")' '$RULESET'"
check "ruleset requires linear history" "jq -e '.rules | map(.type) | index(\"required_linear_history\")' '$RULESET'"
check "ruleset requires pull-request control" "jq -e '.rules | map(.type) | index(\"pull_request\")' '$RULESET'"
check "pull-request requires at least one approval" "jq -e '(.rules[] | select(.type == \"pull_request\") | .parameters.required_approving_review_count) >= 1' '$RULESET'"
check "pull-request dismisses stale reviews on push" "jq -e '.rules[] | select(.type == \"pull_request\") | .parameters.dismiss_stale_reviews_on_push' '$RULESET'"
check "pull-request requires code-owner review" "jq -e '.rules[] | select(.type == \"pull_request\") | .parameters.require_code_owner_review' '$RULESET'"
check "pull-request requires last-push approval" "jq -e '.rules[] | select(.type == \"pull_request\") | .parameters.require_last_push_approval' '$RULESET'"
check "CODEOWNERS exists with a catch-all human-team entry" "grep -qE '^\\* @hyprn-labs/' '$CODEOWNERS'"
check "no ruleset write/apply call in this plan's files" "! grep -rqE 'gh api .*repos/.*rule""sets.*(--method|-X) *(POST|PUT|PATCH)|rule""sets --input' '$REPO_ROOT/agents/github' '$HERE/github.sh'"

# Live per-agent installation assertions (agent host only): each agent row from
# agents.txt must resolve its App installation to exactly the two repositories.
# Off-host (no such local user) the checks SKIP so the script stays runnable
# for static review anywhere; on the host they are strict.
while read -r name uid harness _; do
  if ! id "$name" >/dev/null 2>&1; then
    skip "$name: App installation covers both repositories" "no local user $name (not on agent host)"
    continue
  fi
  run() { runuser -l "$name" -c "$1" </dev/null; }
  check "$name: App installation covers both repositories" "run 'gh api installation/repositories --jq .repositories[].full_name' | sort | diff - <(printf 'hyprn-labs/hyprn-mvp\nhyprn-labs/hyprn-platform\n')"
  check "$name: App installation total count is 2" "[ \"\$(run 'gh api installation/repositories --jq .total_count')\" = 2 ]"
done < <(grep -vE '^\s*(#|$)' "$AGENTS")

exit $fail
