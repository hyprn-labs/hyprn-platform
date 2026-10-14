#!/usr/bin/env bash
# No cloud or production credentials on the agent host (ACC-04, ACC-05). Run as
# root on the host by tests/agents/run.sh.
set -uo pipefail
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

check "no gcloud user credentials on host" "[ -z \"\$(find /home /root -path '*/.config/gcloud/*' \\( -name 'credentials.db' -o -name 'application_default_credentials.json' -o -name 'access_tokens.db' \\) 2>/dev/null)\" ]"
check "no cloud credential variables in agent environments" "! grep -lsE 'GOOGLE_APPLICATION_CREDENTIALS|AWS_SECRET_ACCESS_KEY|AZURE_CLIENT_SECRET' /run/hyprn-agents/secrets/*/* /etc/hyprn-agents/agents/*"
check "agent secrets hold only Slack and GitHub tokens" "[ -z \"\$(find /run/hyprn-agents/secrets -type f ! -name slack.env ! -name github-token 2>/dev/null)\" ]"
exit $fail
