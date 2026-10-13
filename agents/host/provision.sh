#!/usr/bin/env bash
# Provisions the agent host (ADR-0001 section 4, ADR-0002). Idempotent.
# Run as root on hyprn-agents-host-01; see README.md for how it is shipped.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROLES="$HERE/../roles"
CLAUDE_CODE_VERSION="2.1.287"
DOCKER_KEY_FPR="9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
GH_KEY_FPRS="2C6106201985B60E6C7AC87323F3D4EA75716059 7F38BBB59D064DBCB3D84D725612B36462313325"

[ "$(id -u)" -eq 0 ] || { echo "provision.sh must run as root" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
log() { printf '== %s\n' "$*"; }

install_base() {
  log "base packages"
  apt-get update -q
  apt-get install -y -q ca-certificates curl gnupg git tmux jq nftables uidmap \
    dbus-user-session slirp4netns fuse-overlayfs bubblewrap socat build-essential \
    python3-venv python3-websocket unattended-upgrades

  install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  fi
  gpg --show-keys --with-colons /etc/apt/keyrings/docker.asc | grep -q "^fpr:::::::::${DOCKER_KEY_FPR}:" \
    || { echo "unexpected Docker signing key" >&2; exit 1; }
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
    > /etc/apt/sources.list.d/docker.list

  if [ ! -f /etc/apt/keyrings/githubcli-archive-keyring.gpg ]; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli-archive-keyring.gpg
  fi
  gh_fpr="$(gpg --show-keys --with-colons /etc/apt/keyrings/githubcli-archive-keyring.gpg | awk -F: '/^fpr/{print $10; exit}')"
  case " $GH_KEY_FPRS " in *" $gh_fpr "*) ;; *) echo "unexpected GitHub CLI signing key: $gh_fpr" >&2; exit 1;; esac
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list

  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-ce-rootless-extras \
    docker-compose-plugin docker-buildx-plugin gh

  # Agents use rootless Docker only; a rootful daemon would be root-equivalent.
  systemctl disable --now docker.service docker.socket containerd.service >/dev/null 2>&1 || true
  systemctl enable --now unattended-upgrades >/dev/null

  # Private home directories, including those OS Login creates for administrators.
  if grep -qE '^HOME_MODE' /etc/login.defs; then
    sed -i -E 's/^HOME_MODE.*/HOME_MODE\t0700/' /etc/login.defs
  else
    printf 'HOME_MODE\t0700\n' >> /etc/login.defs
  fi
  chmod 0700 /home/*/
}

install_host_files() {
  log "host files"
  install -d -m 0755 /etc/hyprn-agents /etc/hyprn-agents/agents /usr/local/libexec
  install -m 0644 "$HERE/files/egress.nft" /etc/hyprn-agents/egress.nft
  install -m 0644 "$HERE/files/hyprn-agents-egress.service" /etc/systemd/system/
  install -m 0755 "$HERE/files/hyprn-idle-stop" /usr/local/sbin/hyprn-idle-stop
  install -m 0644 "$HERE/files/hyprn-idle-stop.service" "$HERE/files/hyprn-idle-stop.timer" /etc/systemd/system/
  install -m 0755 "$HERE/files/hyprn-agent-session" /usr/local/libexec/hyprn-agent-session
  install -m 0644 "$HERE/files/hyprn-agent@.service" /etc/systemd/system/
  install -m 0644 "$HERE/files/profile.sh" /etc/profile.d/hyprn-agents.sh
  install -m 0755 "$HERE/files/hyprn-agent-secrets" /usr/local/libexec/hyprn-agent-secrets
  install -m 0755 "$HERE/files/hyprn-git-credential" /usr/local/libexec/hyprn-git-credential
  install -m 0755 "$HERE/files/hyprn-agent-github-token" /usr/local/libexec/hyprn-agent-github-token
  install -m 0644 "$HERE/files/hyprn-agent-github-token@.service" "$HERE/files/hyprn-agent-github-token@.timer" /etc/systemd/system/
  install -d -m 0755 /usr/local/libexec/hyprn-agent-bin
  install -m 0755 "$HERE/files/bin/gh" /usr/local/libexec/hyprn-agent-bin/gh
  install -m 0644 "$HERE/files/hyprn-agent-secrets@.service" /etc/systemd/system/

  # Plugin marketplace, root-owned; agents read it and install from it.
  rm -rf /opt/hyprn-agents/marketplace
  install -d -m 0755 /opt/hyprn-agents
  cp -r "$HERE/../marketplace" /opt/hyprn-agents/marketplace
  chown -R root:root /opt/hyprn-agents/marketplace
  chmod -R go-w,a+rX /opt/hyprn-agents/marketplace
  systemctl daemon-reload
  systemctl enable --now hyprn-agents-egress.service hyprn-idle-stop.timer >/dev/null
  systemctl restart hyprn-agents-egress.service
}

add_agent() {
  local name="$1" uid="$2" app_slug="$3" app_id="$4" installation_id="$5" bot_id="$6" display="$7"
  local home="/home/$name" sub=$((100000 + (uid - 20000) * 65536))
  log "agent $name ($uid)"

  if ! id "$name" >/dev/null 2>&1; then
    useradd --create-home --uid "$uid" --user-group --shell /bin/bash --comment "$display" "$name"
  fi
  chmod 0700 "$home"
  grep -q "^$name:" /etc/subuid || usermod --add-subuids "$sub-$((sub + 65535))" "$name"
  grep -q "^$name:" /etc/subgid || usermod --add-subgids "$sub-$((sub + 65535))" "$name"
  install -d -o "$name" -g "$name" -m 0700 "$home/work" "$home/.claude"

  loginctl enable-linger "$name"
  for _ in $(seq 1 30); do [ -S "/run/user/$uid/bus" ] && break; sleep 1; done
  as_agent() {
    runuser -l "$name" -c "set -o pipefail; export XDG_RUNTIME_DIR=/run/user/$uid DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus; $1" </dev/null
  }

  if ! as_agent "systemctl --user is-active --quiet docker"; then
    as_agent "dockerd-rootless-setuptool.sh install" >/dev/null
  fi
  as_agent "systemctl --user enable --now docker" >/dev/null 2>&1

  if ! as_agent "\$HOME/.local/bin/claude --version 2>/dev/null | grep -q '^$CLAUDE_CODE_VERSION'"; then
    as_agent "curl -fsSL https://claude.ai/install.sh | bash -s $CLAUDE_CODE_VERSION" >/dev/null
  fi
  if [ ! -e "$home/.claude/settings.json" ]; then
    printf '{\n  "env": {\n    "DISABLE_AUTOUPDATER": "1"\n  }\n}\n' > "$home/.claude/settings.json"
    chown "$name:$name" "$home/.claude/settings.json"
  fi
  if [ -f "$ROLES/$name.md" ]; then
    install -o "$name" -g "$name" -m 0644 "$ROLES/$name.md" "$home/.claude/CLAUDE.md"
  fi
  # GitHub App (ADR-0005): token broker configuration and the App bot's Git identity.
  printf 'APP_ID=%s\nINSTALLATION_ID=%s\n' "$app_id" "$installation_id" > "/etc/hyprn-agents/agents/$name.github"
  chmod 0644 "/etc/hyprn-agents/agents/$name.github"
  systemctl enable "hyprn-agent-github-token@$name.timer" >/dev/null
  systemctl start "hyprn-agent-github-token@$name.service"
  systemctl start "hyprn-agent-github-token@$name.timer"
  as_agent "git config --global user.name '$display'"
  as_agent "git config --global user.email '$bot_id+$app_slug[bot]@users.noreply.github.com'"
  as_agent "git config --global --replace-all credential.https://github.com.helper /usr/local/libexec/hyprn-git-credential"
  as_agent "git config --global init.defaultBranch main"
  as_agent "git config --global push.autoSetupRemote true"

  # Slack channel plugin from the local marketplace.
  as_agent "claude plugin marketplace add /opt/hyprn-agents/marketplace" >/dev/null 2>&1 || true
  as_agent "claude plugin marketplace update hyprn-agents" >/dev/null
  if as_agent "claude plugin list 2>/dev/null | grep -q 'slack@hyprn-agents'"; then
    as_agent "claude plugin update slack@hyprn-agents" >/dev/null
  else
    as_agent "claude plugin install slack@hyprn-agents" >/dev/null
  fi
  echo "--channels plugin:slack@hyprn-agents" > "/etc/hyprn-agents/agents/$name.args"
  chmod 0644 "/etc/hyprn-agents/agents/$name.args"

  systemctl enable "hyprn-agent-secrets@$name.service" >/dev/null
  systemctl restart "hyprn-agent-secrets@$name.service"

  # The session starts once the agent is signed in (B4); restarted to pick up changes.
  if [ -s "$home/.claude/.credentials.json" ]; then
    systemctl enable "hyprn-agent@$name.service" >/dev/null
    systemctl restart "hyprn-agent@$name.service"
  else
    log "agent $name not signed in yet; session not started"
  fi
}

install_base
install_host_files
grep -vE '^\s*(#|$)' "$HERE/agents.txt" | while read -r name uid app_slug app_id installation_id bot_id display; do
  add_agent "$name" "$uid" "$app_slug" "$app_id" "$installation_id" "$bot_id" "$display"
done
log "done"
