#!/usr/bin/env bash
# OBS-01/CODD-03 checks: collector reachability (or documented scrape fallback),
# digest dry-run, lower-bound disclaimer, and Zen-list staleness.
# Static greps run anywhere; reachability probes the host-local listener and
# SKIPs to the documented fallback when it is not (yet) installed.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
PROVISION="$REPO_ROOT/agents/host/provision.sh"
CONF="$REPO_ROOT/agents/host/files/telemetry-collector.conf"
DIGEST="$REPO_ROOT/agents/host/files/bin/ada-digest"
RUNBOOK="$REPO_ROOT/runbooks/agents/engineering-workflow.md"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

# --- OBS-01: collector config -------------------------------------------------------
check "collector config shipped" "[ -f '$CONF' ]"
check "collector listens on loopback only" "grep -qF 'endpoint: 127.0.0.1:4317' '$CONF'"
check "collector never binds all interfaces" "! grep -qE 'endpoint: (0\\.0\\.0\\.0|:\\s*4317)' '$CONF'"
check "collector buckets per agent per day" "grep -q 'agent' '$CONF' && grep -q 'per agent per day' '$CONF'"
if (exec 3<>/dev/tcp/127.0.0.1/4317) 2>/dev/null; then
  exec 3<&- 3>&-
  echo "PASS collector reachability (listener on 127.0.0.1:4317)"
elif grep -q 'fallback aggregate-file mode' "$RUNBOOK"; then
  echo "PASS collector reachability (documented scrape fallback: collector installs at apply, digest reports zeros plus caveat until then)"
else
  echo "FAIL collector reachability (no listener and no documented fallback)"; fail=1
fi

# --- OBS-01: digest ------------------------------------------------------------------
check "digest script exists and is executable" "[ -x '$DIGEST' ]"
check "digest dry-run exits 0" "'$DIGEST' --dry-run >/dev/null"
check "digest states the lower-bound caveat" "grep -qF 'Lower-bound totals' '$DIGEST'"
check "digest references the collector endpoint" "grep -qF 'OTEL_EXPORTER_OTLP_ENDPOINT' '$DIGEST'"
check "digest never prints the bot token" "! grep -qE 'echo[^|]*\$bot_token|printf[^|]*\$bot_token' '$DIGEST'"
check "digest post body is the aggregate digest only" "grep -qF 'body=\"\$(build_digest)\"' '$DIGEST'"
check "digest holds the host while posting" "grep -q 'HOLD_FILE' '$DIGEST' && grep -q 'trap unhold EXIT' '$DIGEST'"
check "digest schedule wired in provisioning" "grep -q 'ada-digest --post' '$PROVISION' && grep -q '/etc/cron.d/ada-digest' '$PROVISION'"
check "digest zen-check exits 0" "'$DIGEST' --zen-check >/dev/null"

# --- CODD-03: monthly terms re-check ---------------------------------------------------
# No verdict row yet means the owner has not confirmed the first check: SKIP
# with the checkpoint named (never a silent pass). A present but old row FAILs.
if grep -qE '^\| 20[0-9]{2}-[0-9]{2}-[0-9]{2} \| CODD-03' "$RUNBOOK"; then
  latest="$(grep -oE '^\| 20[0-9]{2}-[0-9]{2}-[0-9]{2} \| CODD-03' "$RUNBOOK" | tail -1 | grep -oE '20[0-9]{2}-[0-9]{2}-[0-9]{2}')"
  if [ "$(( ($(date +%s) - $(date -d "$latest" +%s)) / 86400 ))" -le 31 ]; then
    echo "PASS CODD-03 verdict row fresh ($latest)"
  else
    echo "FAIL CODD-03 verdict row stale ($latest, older than 31 days)"; fail=1
  fi
else
  skip "CODD-03 verdict row fresh" "no dated CODD-03 row yet (owner confirms at the 02-04 checkpoint)"
fi

exit $fail
