#!/usr/bin/env bash
# EFF-01/EFF-02 checks: product toolchain pins present with no installs, and
# per-agent caches persisting across task cycles. Static greps run anywhere;
# the cache-marker round-trip runs on the agent host only and SKIPs elsewhere.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
PROVISION="$REPO_ROOT/agents/host/provision.sh"
HELPER="$REPO_ROOT/agents/host/files/bin/ada-task"
PYTHON3_PIN="$(sed -n 's/^PYTHON3_PIN="\(.*\)"/\1/p' "$PROVISION")"
DOCKER_PIN="$(sed -n 's/^DOCKER_PIN="\(.*\)"/\1/p' "$PROVISION")"
GH_PIN="$(sed -n 's/^GH_PIN="\(.*\)"/\1/p' "$PROVISION")"
GIT_PIN="$(sed -n 's/^GIT_PIN="\(.*\)"/\1/p' "$PROVISION")"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
on_host() { id ada >/dev/null 2>&1 || [ "${ADA_LIVE_TEST:-0}" = 1; }

# --- EFF-01: pinned toolchains, no installs --------------------------------------
check "python3 pin recorded in provisioning" "[ -n '$PYTHON3_PIN' ]"
check "docker pin recorded in provisioning" "[ -n '$DOCKER_PIN' ]"
check "gh pin recorded in provisioning" "[ -n '$GH_PIN' ]"
check "git pin recorded in provisioning" "[ -n '$GIT_PIN' ]"
check "python3 at the pinned version" "python3 --version 2>&1 | grep -qF 'Python $PYTHON3_PIN'"
if command -v docker >/dev/null 2>&1; then
  check "docker at the pinned version" "docker --version 2>&1 | grep -qE 'Docker version $DOCKER_PIN\\.'"
else
  skip "docker at the pinned version" "no docker here"
fi
if command -v gh >/dev/null 2>&1; then
  check "gh at the pinned version" "gh --version 2>&1 | grep -qF 'gh version $GH_PIN'"
else
  skip "gh at the pinned version" "no gh here"
fi
check "git at the pinned version" "git --version 2>&1 | grep -qF 'git version $GIT_PIN'"
check "seat OTEL env points at the host-local collector" "grep -qF 'OTEL_EXPORTER_OTLP_ENDPOINT\": \"http://localhost:4317\"' '$PROVISION'"
check "telemetry export intervals lowered against flush loss" "grep -qF 'OTEL_METRIC_EXPORT_INTERVAL\": \"10000\"' '$PROVISION' && grep -qF 'OTEL_LOGS_EXPORT_INTERVAL\": \"2000\"' '$PROVISION'"

# --- EFF-02: per-agent caches are siblings, never inside worktrees ----------------
check "cache dirs are siblings of the worktrees" "grep -qF '\"\$home/work/.cache\"' '$PROVISION'"
check "cache dirs are agent-owned" "grep -qF -- '-o \"\$name\" -g \"\$name\" -m 0700 \"\$home/work/.cache\"' '$PROVISION'"
check "no cache path inside a worktree" "! grep -E 'work/<|work/\$task|\"\$dir/' '$PROVISION' | grep -qi cache"

# --- EFF-02 live: marker survives a helper task cycle (host only) ------------------
if ! on_host; then
  skip "live: cache marker survives a task cycle" "not on agent host (no ada user; set ADA_LIVE_TEST=1 to force)"
else
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  git clone -q "$REPO_ROOT" "$tmp/base" 2>/dev/null
  (cd "$tmp/base" && git checkout -q -B main 2>/dev/null && git remote set-url origin "$tmp/base" && git fetch -q origin 2>/dev/null)
  export ADA_BASE="$tmp/base" ADA_WORKDIR="$tmp/wt" ADA_TASK_NO_EXEC=1
  mkdir -p "$tmp/wt" "$tmp/cache"
  echo "eff-marker" > "$tmp/cache/marker"
  WORKTREE_INDEX=3 "$HELPER" probe-cache >/dev/null
  WORKTREE_INDEX=3 "$HELPER" cleanup probe-cache >/dev/null
  check "live: cache marker survives the task cycle" "[ \"\$(cat '$tmp/cache/marker')\" = eff-marker ]"
  check "live: cleanup removed the worktree but left the cache dir" "[ ! -d '$tmp/wt/probe-cache' ] && [ -d '$tmp/cache' ]"
  trap - EXIT
  rm -rf "$tmp"
fi

exit $fail
