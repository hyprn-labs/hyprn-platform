#!/usr/bin/env bash
# Ada-Boole-Codd isolation checks (Phase 4, ACC-07). Static content
# assertions run anywhere; host-executed portions run as root on the
# agent host and skip with reason when the agent user does not exist.
# Covers homes, secrets, containers, tokens, and bots for ada, boole,
# and codd. Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
BROKER="$REPO_ROOT/agents/host/files/hyprn-credential-broker"
WORKFLOW="$REPO_ROOT/agents/host/files/hyprn-meeting-workflow"
RUNNER="$REPO_ROOT/agents/host/files/hyprn-run-runner"
MEETING_YAML="$REPO_ROOT/agents/loops/meeting.yaml"
NOTION_TF="$REPO_ROOT/infra/agents/boole-notion.tf"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }

# ---- Static assertions: broker and workflow issue per-agent secrets only.
check "broker issues only loop-declared secrets" "grep -q 'Undeclared secrets are refused' '$BROKER'"
check "broker parameterizes secret names per agent" "grep -q '\$AGENT-agent-' '$BROKER'"
check "workflow takes secrets only from the reviewed loop file" "grep -q 'reviewed loop file' '$WORKFLOW'"
check "no hardcoded cross-agent secret names in broker or workflow" "! grep -qE '(ada|codd)-agent-(slack|github|notion)' '$BROKER' '$WORKFLOW'"
check "meeting loop declares no other agent's tokens" "! grep -qE '(ada|codd)-agent-' '$MEETING_YAML'"
check "notion declarations carry no other agent's tokens" "! grep -qE '(ada|codd)-agent-' '$NOTION_TF'"
check "runner executes as the parameterized agent user" "grep -q 'runuser -l \"\$AGENT\"' '$RUNNER'"
check "runner takes destinations from the reviewed loop allowlist only" "grep -q 'reviewed loop' '$RUNNER'"
check "no private-key material in loop or workflow files" "! grep -rlsq '\"private_key\"' '$REPO_ROOT/agents/loops' '$WORKFLOW'"
check "notion token container declared without values" "grep -q 'google_secret_manager_secret' '$NOTION_TF' && ! grep -qE 'secret_data|secret_string|secret_value' '$NOTION_TF'"
check "notion accessor is host-only secretAccessor" "grep -q 'roles/secretmanager.secretAccessor' '$NOTION_TF' && grep -q 'serviceAccount:\${google_service_account.host.email}' '$NOTION_TF'"

# ---- Static assertions: host secret-file conventions.
check "no user cloud credentials under agent homes" "! ls /home/*/.[a-z]*cloud* /home/*/.config/gcloud/credentials.db 2>/dev/null | grep -q . && ! grep -rlsq '\"client_id\".*apps.googleusercontent' /home /root /etc 2>/dev/null"

# ---- Live legs: per-agent homes, secrets, cross-reads. Skip cleanly
# when the agent user (e.g. boole before provisioning) does not exist.
for name in ada boole codd; do
  if ! id "$name" >/dev/null 2>&1; then
    skip "$name: home is private" "no $name user on this machine"
    skip "$name: no sudo or docker group" "no $name user on this machine"
    skip "$name: secret files private to the agent" "no $name user on this machine"
    skip "$name: cannot read other agent homes" "no $name user on this machine"
    continue
  fi
  check "$name: home is private" "[ \"\$(stat -c %a /home/$name)\" = 700 ]"
  check "$name: no sudo or docker group" "! id -nG $name | grep -qwE 'sudo|docker|adm'"
  if [ -d "/run/hyprn-agents/secrets/$name" ]; then
    check "$name: secret files private to the agent" "! find /run/hyprn-agents/secrets/$name -type f \\( ! -perm 400 -o ! -user $name \\) | grep -q ."
  else
    skip "$name: secret files private to the agent" "no secret dir on this machine"
  fi
  for other in ada boole codd; do
    [ "$other" = "$name" ] && continue
    if [ -d "/home/$other" ]; then
      check "$name: cannot read /home/$other" "! runuser -l '$name' -c 'ls /home/$other' </dev/null"
    else
      skip "$name: cannot read /home/$other" "no $other home on this machine"
    fi
  done
done

check "isolation.sh is executable for run.sh auto-discovery" "[ -x '$HERE/isolation.sh' ]"

exit $fail
