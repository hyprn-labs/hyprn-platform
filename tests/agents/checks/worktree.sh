#!/usr/bin/env bash
# GH-02 worktree checks: ada-task index-derived isolation, the GH-01 PR body
# contract it emits, and full cleanup leaving zero residue.
# Static greps run anywhere; the live two-worktree proof runs on the agent
# host only (needs the ada user) and SKIPs elsewhere. Live full cleanup proof
# on-host runs after the 02-03 owner-go apply; static coverage is complete off-host.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
HELPER="$REPO_ROOT/agents/host/files/bin/ada-task"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

# --- static: index derivation -------------------------------------------------
check "helper exists and is executable" "[ -x '$HELPER' ]"
check "helper uses strict mode" "grep -q 'set -euo pipefail' '$HELPER'"
check "slug regex kept verbatim from opencode-task" "grep -qF '^[a-z0-9][a-z0-9-]{0,40}\$' '$HELPER'"
check "hyprn-platform name reservation kept" "grep -qF '[ \"\$task\" != hyprn-platform ]' '$HELPER'"
check "index defaults to 0" "grep -qF 'WORKTREE_INDEX=\"\${WORKTREE_INDEX:-0}\"' '$HELPER'"
check "port stride is 100 per index" "grep -qF 'PORT_BASE + WORKTREE_INDEX * 100' '$HELPER'"
check "compose project derived from index and slug" "grep -qF 'COMPOSE_PROJECT_NAME=\"hyprn-wt-\${WORKTREE_INDEX}-' '$HELPER'"
check "test DB derived from index" "grep -qF 'TEST_DB=\"hyprn_test_wt\${WORKTREE_INDEX}\"' '$HELPER'"
check "product env read with defaults (no hyprn-mvp hard requirement)" "grep -qE '\\$\\{PRODUCT_[A-Z_]+:-' '$HELPER'"
check "branch shape is agent/<name>/<slug>" "grep -qF 'branch=\"agent/\$(id -un)/\$task\"' '$HELPER'"
check "fetch-prune plus reopen-if-exists kept" "grep -q 'fetch -q --prune origin' '$HELPER'"
check "cleanup subcommand removes worktree" "grep -q 'worktree remove --force' '$HELPER'"
check "cleanup subcommand deletes the local branch" "grep -q 'branch -D' '$HELPER'"
check "cleanup selects volumes by derived project name only" "grep -qF '\${COMPOSE_PROJECT_NAME}_' '$HELPER'"
check "runtime state is a sibling file, never inside the worktree" "grep -qF 'ENV_FILE=\"\${dir}.env\"' '$HELPER'"
check "PR template carries the What-changed heading" "grep -qF '## What changed' '$HELPER'"
check "PR template carries the How-verified heading" "grep -qF '## How verified' '$HELPER'"
check "no merge step anywhere in the helper" "! grep -q 'pr merge' '$HELPER'"
check "slug interpolations are quoted" "grep -qF '\"\$task\"' '$HELPER'"

# --- fail-fast TEST guard ------------------------------------------------------
# The live proof below creates real worktrees and branches; it must never run
# by accident in CI or on a checkout that is not the agent host. Refuse unless
# the host marker (ada user) or an explicit opt-in is present.
on_host() { id ada >/dev/null 2>&1 || [ "${ADA_LIVE_TEST:-0}" = 1 ]; }

# --- live: two concurrent worktrees, isolated, fully cleaned -------------------
if ! on_host; then
  skip "live: two worktrees get distinct ports/projects/DBs" "not on agent host (no ada user; set ADA_LIVE_TEST=1 to force)"
  skip "live: cleanup leaves zero residue" "not on agent host (no ada user; set ADA_LIVE_TEST=1 to force)"
else
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  # Fully hermetic base: local clone whose origin points at itself, so the
  # helper's fetch-prune plus origin/main flow works with no network.
  git clone -q "$REPO_ROOT" "$tmp/base" 2>/dev/null
  (cd "$tmp/base" && git checkout -q -B main 2>/dev/null && git remote set-url origin "$tmp/base" && git fetch -q origin 2>/dev/null)
  export ADA_BASE="$tmp/base" ADA_WORKDIR="$tmp/wt" ADA_TASK_NO_EXEC=1
  mkdir -p "$tmp/wt"

  WORKTREE_INDEX=0 "$HELPER" probe-alpha >/dev/null
  # shellcheck disable=SC1090
  . "$tmp/wt/probe-alpha.env"
  port0="$APP_PORT"; proj0="$COMPOSE_PROJECT_NAME"; db0="$TEST_DB"
  WORKTREE_INDEX=1 "$HELPER" probe-beta >/dev/null
  # shellcheck disable=SC1090
  . "$tmp/wt/probe-beta.env"
  port1="$APP_PORT"; proj1="$COMPOSE_PROJECT_NAME"; db1="$TEST_DB"

  check "live: consecutive indexes yield ports 100 apart" "[ '$port1' = \"$((port0 + 100))\" ]"
  check "live: compose projects differ" "[ '$proj0' != '$proj1' ]"
  check "live: test DBs differ" "[ '$db0' != '$db1' ]"
  check "live: env files are siblings of the worktrees" "[ -f '$tmp/wt/probe-alpha.env' ] && [ -f '$tmp/wt/probe-beta.env' ]"

  WORKTREE_INDEX=0 "$HELPER" cleanup probe-alpha >/dev/null
  WORKTREE_INDEX=1 "$HELPER" cleanup probe-beta >/dev/null
  check "live: cleanup removes both worktrees" "! git -C '$tmp/base' worktree list --porcelain | grep -q '$tmp/wt/probe-'"
  check "live: cleanup deletes both branches" "! git -C '$tmp/base' show-ref --quiet --verify refs/heads/agent/'$(id -un)'/probe-alpha && ! git -C '$tmp/base' show-ref --quiet --verify refs/heads/agent/'$(id -un)'/probe-beta"
  check "live: cleanup removes both env files" "[ ! -e '$tmp/wt/probe-alpha.env' ] && [ ! -e '$tmp/wt/probe-beta.env' ]"
  if command -v docker >/dev/null 2>&1; then
    check "live: no volumes left for either project" "! docker volume ls --format '{{.Name}}' 2>/dev/null | grep -qE '^hyprn-wt-[01]-probe-(alpha|beta)_'"
  else
    skip "live: no volumes left for either project" "no docker here"
  fi
  trap - EXIT
  rm -rf "$tmp"
fi

exit $fail
