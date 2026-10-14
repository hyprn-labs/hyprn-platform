# agents/host

Provisioning for the agent host `hyprn-agents-host-01` ([ADR-0001](../../docs/adr/0001-agent-fleet.md) section 4, [ADR-0002](../../docs/adr/0002-agent-host-on-demand.md)).

| File | Purpose |
|---|---|
| `agents.txt` | Agents: name, UID (20000–20999), harness (`claude` or `opencode`), GitHub App (slug, App ID, installation ID, bot user ID), display name |
| `provision.sh` | Idempotent, run as root on the host: packages (Docker and GitHub CLI from their signed repositories, signing keys checked), no rootful Docker daemon, unattended security upgrades, private home directories, OpenCode at a pinned version, the files below, and per agent a user without sudo, rootless Docker, its GitHub App token and Git identity, its role file and, for Claude Code agents, Claude Code at a pinned version, the Slack plugin and the session |
| `apply.sh` | Run from a workstation: ships `agents/host`, `agents/roles`, `agents/marketplace`, `agents/policy` and `tests/agents` over IAP, runs `provision.sh` and `tests/agents/run.sh` |
| `files/egress.nft`, `files/hyprn-agents-egress.service` | Agent users and their containers reach the metadata server for DNS only, never for credentials; their other new connections are logged unless they go to the proxy on this host |
| `files/squid.conf`, `files/ops-agent.yaml`, `files/hyprn-egress-proxy` | Egress observation: Squid with one port per agent, its log shipped to Cloud Logging, and the switch that puts agents on the proxy ([runbook](../../runbooks/agents/egress.md)) |
| `files/hyprn-agent-secrets`, `files/hyprn-agent-secrets@.service` | Root loader: reads an agent's Slack tokens and the Slack allowlist from Secret Manager and writes them to tmpfs, readable by that agent only |
| `files/hyprn-agent-github-token`, `files/hyprn-agent-github-token@.{service,timer}` | Root token broker ([ADR-0005](../../docs/adr/0005-agent-github-app.md)): signs with the agent's GitHub App key, held in memory, and mints a one-hour installation token every 30 minutes and on each secret reload |
| `files/bin/hyprn-worktree-cleanup`, `files/hyprn-worktree-cleanup@.{service,timer}` | Removes an agent's task worktrees and local branches once their pull request is merged or closed and nothing would be lost; daily and at each `opencode-task` |
| `files/hyprn-git-credential`, `files/bin/gh` | Git credential helper and `gh` wrapper, both serving the agent's current installation token |
| `files/opencode.json`, `files/bin/opencode`, `files/bin/opencode-task` | OpenCode's managed configuration, its wrapper (agents whose harness is `opencode` only) and the task launcher: one worktree, branch and tmux session per task ([runbook](../../runbooks/agents/opencode.md)) |
| `files/hyprn-agent@.service`, `files/hyprn-agent-session` | One tmux session per agent running Claude Code with its channel; resumes the last conversation after each boot. herdr replaces tmux as the session runtime in milestone M1 ([agent fleet specification](../../docs/specs/agent-fleet.md), section 4) |
| `files/hyprn-idle-stop*` | Powers the host off after 30 minutes with no terminal input, no SSH command running, no load and no agent activity (Claude Code conversations, OpenCode sessions); `/run/hyprn-agents/hold` keeps it on |
| `files/profile.sh` | `PATH` (wrappers first), `XDG_RUNTIME_DIR`, `DOCKER_HOST` and, while switched on, the proxy variables for agent users |

## Use

```bash
gcloud compute instances start hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents
agents/host/apply.sh
```

Watch or take over an agent's session (detach with Ctrl-b d):

```bash
gcloud compute ssh hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap
sudo -iu ada tmux attach -t agent
```

A new agent signs in once with `sudo -iu <agent> claude` and `/login`, answers the workspace trust question for `~/work`, then `apply.sh` starts its session.
