# Environment for agent users (UIDs 20000-20999): user tools and rootless Docker.
_hyprn_uid=$(id -u)
if [ "$_hyprn_uid" -ge 20000 ] && [ "$_hyprn_uid" -le 20999 ]; then
  export PATH="$HOME/.local/bin:$PATH"
  export XDG_RUNTIME_DIR="/run/user/$_hyprn_uid"
  export DOCKER_HOST="unix:///run/user/$_hyprn_uid/docker.sock"
  _hyprn_gh="/run/hyprn-agents/secrets/$(id -un)/github-token"
  [ -r "$_hyprn_gh" ] && GH_TOKEN="$(cat "$_hyprn_gh")" && export GH_TOKEN
  unset _hyprn_gh
fi
unset _hyprn_uid
