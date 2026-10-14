# Environment for agent users (UIDs 20000-20999): user tools and rootless Docker.
_hyprn_uid=$(id -u)
if [ "$_hyprn_uid" -ge 20000 ] && [ "$_hyprn_uid" -le 20999 ]; then
  export PATH="/usr/local/libexec/hyprn-agent-bin:$HOME/.local/bin:$PATH"
  export XDG_RUNTIME_DIR="/run/user/$_hyprn_uid"
  export DOCKER_HOST="unix:///run/user/$_hyprn_uid/docker.sock"
  # Egress observation proxy, while switched on (hyprn-egress-proxy).
  _hyprn_port_file="/etc/hyprn-agents/agents/$(id -un).proxy-port"
  if [ -e /etc/hyprn-agents/egress-proxy ] && [ -r "$_hyprn_port_file" ]; then
    _hyprn_proxy="http://127.0.0.1:$(cat "$_hyprn_port_file")"
    export HTTP_PROXY="$_hyprn_proxy" HTTPS_PROXY="$_hyprn_proxy" http_proxy="$_hyprn_proxy" https_proxy="$_hyprn_proxy"
    export NO_PROXY="localhost,127.0.0.1,::1,169.254.169.254,metadata.google.internal" no_proxy="localhost,127.0.0.1,::1,169.254.169.254,metadata.google.internal"
  fi
  unset _hyprn_port_file _hyprn_proxy
fi
unset _hyprn_uid
