# tests/agents

[`host-checks.sh`](host-checks.sh) runs as root on the agent host after each provisioning: metadata server unreachable for agent users, private homes, no administrative groups, rootless Docker only, DNS and outbound HTTPS, Claude Code and the Slack plugin installed, secrets readable only by their agent, Git identity per agent, root-owned Slack allowlist, idle-stop timer active, no service-account key files.
