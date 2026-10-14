# Environment for agent users (UIDs 20000-20999): user tools and rootless Docker.
_hyprn_uid=$(id -u)
if [ "$_hyprn_uid" -ge 20000 ] && [ "$_hyprn_uid" -le 20999 ]; then
  export PATH="/usr/local/libexec/hyprn-agent-bin:$HOME/.local/bin:$PATH"
  export XDG_RUNTIME_DIR="/run/user/$_hyprn_uid"
  export DOCKER_HOST="unix:///run/user/$_hyprn_uid/docker.sock"
  # Observe-first egress (EGR-01): direct 80/443 is dropped for these UIDs
  # (agents/host/files/egress.nft), so every agent shell needs its per-agent
  # Squid port: ada (20001) -> 3128, codd (20002) -> 3129 (fleet registry).
  # Extend this case when the fleet gains agents; an unmapped UID gets no
  # proxy vars (loud failure, never traffic misattributed to another agent).
  case "$_hyprn_uid" in
    20001) _hyprn_proxy_port=3128 ;;
    20002) _hyprn_proxy_port=3129 ;;
  esac
  if [ -n "${_hyprn_proxy_port:-}" ]; then
    export http_proxy="http://127.0.0.1:$_hyprn_proxy_port"
    export https_proxy="http://127.0.0.1:$_hyprn_proxy_port"
    export HTTP_PROXY="http://127.0.0.1:$_hyprn_proxy_port"
    export HTTPS_PROXY="http://127.0.0.1:$_hyprn_proxy_port"
    # Loopback and the link-local metadata address never use the proxy
    # (metadata stays rejected by nftables; DNS on port 53 stays allowed).
    export no_proxy="localhost,127.0.0.1,::1,169.254.169.254"
    export NO_PROXY="localhost,127.0.0.1,::1,169.254.169.254"
  fi
  unset _hyprn_proxy_port
  # Rootless containers do NOT inherit this shell env on their own: docker
  # run forwards nothing unless asked, so every container invocation must
  # pass --env explicitly (precedent: agents/host/files/hyprn-run-runner and
  # the container live probes in tests/agents/checks/egress.sh use
  # --env https_proxy=http://host.containers.internal:<own-port>). Docker
  # itself is unchanged; this file only documents the contract.
fi
unset _hyprn_uid
