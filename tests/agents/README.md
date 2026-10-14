# tests/agents

Safety checks for the agent fleet (ACC-08). Each line prints `PASS`, `FAIL` or `SKIP`; a script exits non-zero when any check fails.

| Script | Where | Checks |
|---|---|---|
| [`run.sh`](run.sh) | Agent host, as root; run by `agents/host/apply.sh` after each provisioning | Runs `host-checks.sh` and every `checks/*.sh`, keeps a dated record in `/var/lib/hyprn-agents/checks/` |
| [`host-checks.sh`](host-checks.sh) | Agent host | Metadata server unreachable for agent users, private homes, no administrative groups, rootless Docker only, DNS and outbound HTTPS, Claude Code and the Slack plugin for Claude Code agents, OpenCode for OpenCode agents and refused for the others, Codd's GitHub App limited to `hyprn-platform`, secrets readable only by their agent, Git identity per agent, OpenCode pinned with its root-owned policy, root-owned Slack allowlist, idle-stop timer active, daily worktree cleanup scheduled and runnable per agent, no service-account key files |
| [`checks/accounts.sh`](checks/accounts.sh) | Agent host | No gcloud user credentials, no cloud credential variables, agent secrets limited to Slack and GitHub tokens |
| [`checks/policy.sh`](checks/policy.sh) | Agent host | The Claude Code policy the console serves matches `agents/policy/managed-settings.json`; the Slack plugin comes from the root-owned local marketplace |
| [`checks/egress.sh`](checks/egress.sh) | Agent host | Proxy, log shipping and the direct-connection log in place; with the proxy on, each agent's shell, HTTPS and Docker go through it, logged under its name, and Ada's Slack reconnects |
| [`owner-checks.sh`](owner-checks.sh) | Owner's workstation, HYPRN configurations, read-only | Reviewed ruleset and policy files; no person holding cloud roles; Secret Manager audit logs and both alerts; wake identity and service; GitHub two-factor requirement, `owners` team and, on the Team plan, the ruleset in every repository |
