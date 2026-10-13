#!/usr/bin/env bash
# Controller checks (CP-02, CP-03, CP-04). Static content assertions run anywhere;
# host-executed portions run as root on the agent host.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
DISPATCHER="$REPO_ROOT/controller/dispatcher.py"
SCHEMA="$REPO_ROOT/controller/schema.sql"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

check "controller unit suite is green" "python3 -m unittest discover -s '$REPO_ROOT/controller'"
check "schema loads into an in-memory database" "python3 -c \"import sqlite3; c=sqlite3.connect(':memory:'); c.executescript(open('$SCHEMA').read())\""
check "kill-flag poll interval stays within the one-minute bound" "[ \"\$(grep -E '^POLL_SECONDS *= *[0-9]+' '$DISPATCHER' | grep -oE '[0-9]+')\" -le 60 ]"
check "dispatcher carries the parked-approval path" "grep -q 'def park' '$DISPATCHER' && grep -q 'def resume' '$DISPATCHER'"
check "dispatcher carries the budget pre-check" "grep -q '_spend_for' '$DISPATCHER'"
check "dispatcher carries three-scope kill flags" "grep -q 'kill_loop' '$DISPATCHER' && grep -q 'kill_agent' '$DISPATCHER' && grep -q 'kill_fleet' '$DISPATCHER'"

exit $fail
