#!/usr/bin/env bash
# herdr runtime checks (COK-02): pinned checksum-verified install, per-agent
# user units active, agent-to-agent prompting off, hooks allowlisted, tmux
# fallback present-but-disabled, and a regression tail proving Slack/wake/checks
# still work after the tmux-to-herdr switch.
# Static greps run anywhere; unit/host assertions run on the agent host only
# (needs the ada user and root for runuser) and SKIP elsewhere.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
PROVISION="$REPO_ROOT/agents/host/provision.sh"
SESSION="$REPO_ROOT/agents/host/files/herdr-session"
UNIT="$REPO_ROOT/agents/host/files/herdr@.service"
FALLBACK_UNIT="$REPO_ROOT/agents/host/files/hyprn-agent@.service"
POLICY="$REPO_ROOT/agents/policy/managed-settings.json"
AGENTS="$(mktemp)"
# Fleet registry (FLT-01) is the only declaration: render agents.txt to an
# ephemeral file; every parse loop below is untouched.
python3 "$REPO_ROOT/agents/fleet-render" --agents-out "$AGENTS" || exit 1
HERDR_VERSION="$(sed -n 's/^HERDR_VERSION="\(.*\)"/\1/p' "$PROVISION")"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
on_host() { id ada >/dev/null 2>&1 && [ "$(id -u)" -eq 0 ]; }

# --- static: pin, unit shape, prompting off, hooks --------------------------------
check "herdr pin derived from provision.sh" "[ -n '$HERDR_VERSION' ]"
check "provision.sh carries a per-arch SHA256 for herdr" "grep -qE '^HERDR_SHA256=\"[0-9a-f]{64}\"' '$PROVISION' && grep -qE '^HERDR_SHA256_AARCH64=\"[0-9a-f]{64}\"' '$PROVISION'"
check "provision.sh verifies the checksum before install" "grep -q 'sha256sum -c' '$PROVISION'"
check "install_herdr() mirrors the opencode pin-guard shape" "grep -q 'install_herdr()' '$PROVISION' && grep -qF 'grep -qF \"\$HERDR_VERSION\"' '$PROVISION'"
check "herdr-session uses strict mode and a restart loop" "grep -q 'set -uo pipefail' '$SESSION' && grep -q 'sleep 10' '$SESSION'"
check "unit runs one server per agent UID" "grep -qF 'User=%i' '$UNIT'"
check "unit restarts the server on failure" "grep -qF 'Restart=on-failure' '$UNIT'"
check "agent-to-agent prompting locked off in the launcher" "grep -q 'unset HERDR_ENV' '$SESSION'"
check "agent-to-agent prompting denied in policy" "grep -qF 'Bash(herdr agent prompt*)' '$POLICY'"
check "herdr lifecycle hooks allowlisted in policy" "grep -qF 'Bash(herdr pane report-agent*)' '$POLICY'"
check "merge-refusal denies still intact" "[ \"\$(grep -c 'gh pr merge' '$POLICY')\" = 2 ]"
check "policy is valid JSON" "python3 -m json.tool '$POLICY'"
check "tmux fallback unit still shipped" "[ -f '$FALLBACK_UNIT' ]"
check "runbook holds the cockpit checklist" "grep -qF 'herdr machine add' '$REPO_ROOT/runbooks/agents/engineering-workflow.md' && grep -qF 'Remote Control' '$REPO_ROOT/runbooks/agents/engineering-workflow.md'"

# --- live: units active, pin installed, fallback disabled (host only) ---------------
if ! on_host; then
  skip "live: per-agent herdr units active" "not root on the agent host"
  skip "live: installed herdr at the pinned version" "not root on the agent host"
  skip "live: tmux fallback present but disabled" "not root on the agent host"
  skip "live: agent homes still private under herdr" "not root on the agent host"
else
  while read -r name uid harness _; do
    run() { runuser -l "$name" -c "$1" </dev/null; }
    if [ "$harness" = claude ]; then
      check "$name: herdr unit active" "runuser -l '$name' -c 'XDG_RUNTIME_DIR=/run/user/$uid systemctl --user is-active --quiet herdr@${name}.service' </dev/null"
      check "$name: tmux fallback disabled" "! systemctl is-enabled --quiet 'hyprn-agent@${name}.service'"
    fi
    check "$name: home still private" "[ \"\$(stat -c %a /home/$name)\" = 700 ]"
  done < <(grep -vE '^\s*(#|$)' "$AGENTS")
  check "herdr installed at the pinned version" "/usr/local/lib/herdr/herdr --version | grep -qF '$HERDR_VERSION'"
fi

# --- regression tail: Slack/wake/checks keep working --------------------------------
# Runs every sibling check script except this one (calling run.sh itself would
# recurse: run.sh executes this file). Host-only: elsewhere the siblings fail
# on pre-existing environmental grounds (no runuser off-host), which would
# misreport as a herdr regression. Skipped when already nested.
if [ -n "${HERDR_NESTED:-}" ]; then
  skip "regression: sibling checks" "nested run"
elif ! on_host; then
  skip "regression: sibling checks" "not root on the agent host (runs post-apply)"
else
  export HERDR_NESTED=1
  for script in "$HERE"/*.sh; do
    [ "$script" = "$HERE/herdr.sh" ] && continue
    [ -x "$script" ] || continue
    if "$script" >/dev/null 2>&1; then
      echo "PASS regression: $(basename "$script") green"
    else
      echo "FAIL regression: $(basename "$script") red"; fail=1
    fi
  done
fi

rm -f "$AGENTS"
exit $fail
