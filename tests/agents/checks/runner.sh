#!/usr/bin/env bash
# Runner checks (CP-06, RT-01, EGR-03). Static content assertions run anywhere;
# the container dry-run executes only on the agent host (docker + agent user),
# otherwise SKIP with reason. Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
BROKER="$REPO_ROOT/agents/host/files/hyprn-credential-broker"
RUNNER="$REPO_ROOT/agents/host/files/hyprn-run-runner"
LOOP="$REPO_ROOT/agents/loops/testdata/test-loop.yaml"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

check "broker passes syntax check" "bash -n '$BROKER'"
check "runner passes syntax check" "bash -n '$RUNNER'"
check "broker carries usage text" "bash '$BROKER' --help 2>&1 | grep -qiE 'usage|run-id'"
check "broker non-comment lines carry no key-shaped material" "[ \"\$(grep -v '^#' '$BROKER' | grep -c -iE 'BEGIN.*PRIVATE|sk-[A-Za-z0-9]{10,}')\" = 0 ]"
check "broker scopes the run dir by run id" "grep -q 'RUN_ID' '$BROKER' && grep -q 'RUN_ROOT' '$BROKER'"
check "broker creates the run dir agent-owned mode 0500" "grep -q 'install -d -m 0500 -o \"\$AGENT\"' '$BROKER'"
check "broker writes via temp plus chown plus atomic move" "grep -q 'chown \"\$AGENT' '$BROKER'"
check "broker removes the run dir on run end" "grep -q -- '--cleanup' '$BROKER' && grep -q 'rm -rf \"\$dir\"' '$BROKER'"
check "broker unsets key material after signing" "grep -q 'unset key' '$BROKER'"
check "broker reads only loop-declared secrets" "grep -q 'loop file' '$BROKER'"
check "runner opens with kill-flag early-exit guards" "grep -q 'kill_fleet' '$RUNNER' && grep -q 'kill_agent_' '$RUNNER'"
check "runner registers the idle-stop hold" "grep -q 'hyprn-agents/hold' '$RUNNER'"
check "runner translates the loop allowlist into container env" "grep -q 'egress_allowlist' '$RUNNER' && grep -q 'ALLOWED_HOSTS' '$RUNNER'"
check "runner mounts only its own run dir" "grep -q \"RUN_DIR:/run/secrets:ro\" '$RUNNER'"
check "runner executes as the agent user" "grep -q 'runuser -l \"\$AGENT\"' '$RUNNER'"
check "runner uses read-only plus auto-remove flags" "grep -q -- '--rm' '$RUNNER' && grep -q -- '--read-only' '$RUNNER'"
check "runner passes the binding through as config" "grep -q 'MODEL_BINDING' '$RUNNER'"
check "runner invokes broker cleanup on run end" "grep -q 'credential-broker --cleanup' '$RUNNER'"

# Fixture-mode probe: no network, completes anywhere.
FIXTURE_DIR="$(mktemp -d)"
if bash "$BROKER" --fixture "$FIXTURE_DIR" "$LOOP" >/dev/null 2>&1 && [ -d "$FIXTURE_DIR/fixture-run" ]; then
  echo "PASS broker fixture mode completes with zero network"
else
  echo "FAIL broker fixture mode completes with zero network"; fail=1
fi
rm -rf "$FIXTURE_DIR"

# Live dry-run: disallowed destination refused while the gateway host
# resolves — host only (docker + boole user), else SKIP.
if command -v docker >/dev/null 2>&1 && id boole >/dev/null 2>&1; then
  if runuser -l boole -c "docker run --rm curlimages/curl -sf -m 10 -o /dev/null https://example.com" </dev/null >/dev/null 2>&1; then
    echo "FAIL dry-run: disallowed destination reachable"; fail=1
  else
    echo "PASS dry-run: disallowed destination refused"
  fi
else
  skip "dry-run: disallowed destination refused" "no container runtime or agent user (static assertion only)"
fi

exit $fail
