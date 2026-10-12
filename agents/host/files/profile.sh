# Environment for agent users (UIDs 20000-20999): user tools and rootless Docker.
_hyprn_uid=$(id -u)
if [ "$_hyprn_uid" -ge 20000 ] && [ "$_hyprn_uid" -le 20999 ]; then
  export PATH="$HOME/.local/bin:$PATH"
  export XDG_RUNTIME_DIR="/run/user/$_hyprn_uid"
  export DOCKER_HOST="unix:///run/user/$_hyprn_uid/docker.sock"
fi
unset _hyprn_uid
