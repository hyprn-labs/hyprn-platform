#!/usr/bin/env bash
# Provisions the agent host (ADR-0001 section 4, ADR-0002). Idempotent.
# Run as root on hyprn-agents-host-01; see README.md for how it is shipped.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROLES="$HERE/../roles"
CLAUDE_CODE_VERSION="2.1.287"
DOCKER_KEY_FPR="9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
OPENCODE_VERSION="1.19.0"
OPENCODE_SHA256="7bb9e61ad6feacf2e89c10a6a2c1840e3de4220bb50ba1fc7110f31806076aec"  # opencode-linux-x64.tar.gz
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
  install -m 0755 "$HERE/files/bin/hyprn-worktree-cleanup" /usr/local/libexec/hyprn-agent-bin/hyprn-worktree-cleanup
  install -m 0644 "$HERE/files/hyprn-worktree-cleanup@.service" "$HERE/files/hyprn-worktree-cleanup@.timer" /etc/systemd/system/
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

# OpenCode (runbooks/agents/opencode.md): pinned release, root-owned binary and
# managed configuration; the wrapper runs it only for agents whose harness is opencode.
install_opencode() {
  log "OpenCode $OPENCODE_VERSION"
  local dest=/usr/local/lib/opencode tmp
  if ! "$dest/opencode" --version 2>/dev/null | grep -qF "$OPENCODE_VERSION"; then
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/opencode.tar.gz" \
      "https://github.com/anomalyco/opencode/releases/download/v$OPENCODE_VERSION/opencode-linux-x64.tar.gz"
    echo "$OPENCODE_SHA256  $tmp/opencode.tar.gz" | sha256sum -c --quiet
    tar -xzf "$tmp/opencode.tar.gz" -C "$tmp"
    install -d -m 0755 "$dest"
    install -m 0755 -o root -g root "$(find "$tmp" -type f -name opencode | head -1)" "$dest/opencode"
    rm -rf "$tmp"
  fi
  install -d -m 0755 /etc/opencode
  install -m 0644 "$HERE/files/opencode.json" /etc/opencode/opencode.json
  install -m 0755 "$HERE/files/bin/opencode" "$HERE/files/bin/opencode-task" /usr/local/libexec/hyprn-agent-bin/
}

# Egress observation (EGR-01): Squid logs every agent request, the Ops Agent
# ships its log to Cloud Logging; agents use it once hyprn-egress-proxy is on.
install_egress() {
  log "egress observation"
  apt-get install -y -q squid
  if [ ! -f /etc/apt/sources.list.d/google-cloud-ops-agent.list ]; then
    echo "deb https://packages.cloud.google.com/apt google-cloud-ops-agent-bookworm-all main" \
      > /etc/apt/sources.list.d/google-cloud-ops-agent.list
    apt-get update -q
  fi
  apt-get install -y -q google-cloud-ops-agent
  curl -sf -H 'Metadata-Flavor: Google' \
    http://169.254.169.254/computeMetadata/v1/instance/network-interfaces/0/ip > /etc/hyprn-agents/host-ip
  install -m 0644 "$HERE/files/squid.conf" /etc/squid/squid.conf
  install -m 0644 "$HERE/files/ops-agent.yaml" /etc/google-cloud-ops-agent/config.yaml
  install -m 0755 "$HERE/files/hyprn-egress-proxy" /usr/local/sbin/hyprn-egress-proxy
  local host_ip conf=/etc/hyprn-agents/squid-agents.conf.tmp
  host_ip="$(cat /etc/hyprn-agents/host-ip)"
  printf 'acl from_host src %s/32\n' "$host_ip" > "$conf"
  grep -vE '^\s*(#|$)' "$HERE/agents.txt" | while read -r name uid _; do
    local port=$((3100 + uid - 20000))
    printf 'http_port 127.0.0.1:%s\nhttp_port %s:%s\nacl port_%s localport %s\nnote agent %s port_%s\n' \
      "$port" "$host_ip" "$port" "$name" "$port" "$name" "$name" >> "$conf"
    echo "$port" > "/etc/hyprn-agents/agents/$name.proxy-port"
    chmod 0644 "/etc/hyprn-agents/agents/$name.proxy-port"
  done
  mv "$conf" /etc/hyprn-agents/squid-agents.conf
  squid -k parse 2>&1 | grep -iE 'FATAL|ERROR' && { echo "squid configuration invalid" >&2; exit 1; }
  systemctl enable squid google-cloud-ops-agent >/dev/null 2>&1
  systemctl restart squid google-cloud-ops-agent
}

add_agent() {
  local name="$1" uid="$2" harness="$3" app_slug="$4" app_id="$5" installation_id="$6" bot_id="$7" display="$8"
  local home="/home/$name" sub=$((100000 + (uid - 20000) * 65536))
  log "agent $name ($uid, $harness)"
  case "$harness" in claude|opencode) ;; *) echo "unknown harness for $name: $harness" >&2; exit 1 ;; esac

  if ! id "$name" >/dev/null 2>&1; then
    useradd --create-home --uid "$uid" --user-group --shell /bin/bash --comment "$display" "$name"
  fi
  chmod 0700 "$home"
  grep -q "^$name:" /etc/subuid || usermod --add-subuids "$sub-$((sub + 65535))" "$name"
  grep -q "^$name:" /etc/subgid || usermod --add-subgids "$sub-$((sub + 65535))" "$name"
  install -d -o "$name" -g "$name" -m 0700 "$home/work"
  printf '%s\n' "$harness" > "/etc/hyprn-agents/agents/$name.harness"
  chmod 0644 "/etc/hyprn-agents/agents/$name.harness"

  loginctl enable-linger "$name"
  for _ in $(seq 1 30); do [ -S "/run/user/$uid/bus" ] && break; sleep 1; done
  as_agent() {
    runuser -l "$name" -c "set -o pipefail; export XDG_RUNTIME_DIR=/run/user/$uid DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$uid/bus; $1" </dev/null
  }

  if ! as_agent "systemctl --user is-active --quiet docker"; then
    as_agent "dockerd-rootless-setuptool.sh install" >/dev/null
  fi
  as_agent "systemctl --user enable --now docker" >/dev/null 2>&1

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
  systemctl enable "hyprn-agent-secrets@$name.service" >/dev/null
  systemctl restart "hyprn-agent-secrets@$name.service"
  systemctl enable --now "hyprn-worktree-cleanup@$name.timer" >/dev/null

  if [ "$harness" = opencode ]; then
    # Role file, read by OpenCode as the agent's global rules.
    install -d -o "$name" -g "$name" -m 0700 "$home/.config" "$home/.config/opencode"
    [ -f "$ROLES/$name.md" ] && install -o "$name" -g "$name" -m 0644 "$ROLES/$name.md" "$home/.config/opencode/AGENTS.md"
    return 0
  fi

  install -d -o "$name" -g "$name" -m 0700 "$home/.claude"
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
install_opencode
install_egress
grep -vE '^\s*(#|$)' "$HERE/agents.txt" | while read -r name uid harness app_slug app_id installation_id bot_id display; do
  add_agent "$name" "$uid" "$harness" "$app_slug" "$app_id" "$installation_id" "$bot_id" "$display"
done
log "done"
