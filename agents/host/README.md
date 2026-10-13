# agents/host

Provisioning for the agent host `hyprn-agents-host-01` ([ADR-0001](../../docs/adr/0001-agent-fleet.md) section 4, [ADR-0002](../../docs/adr/0002-agent-host-on-demand.md)).

| File | Purpose |
|---|---|
| `agents.txt` | Agents: name, UID (20000–20999), GitHub App (slug, App ID, installation ID, bot user ID), display name |
| `provision.sh` | Idempotent, run as root on the host: packages (Docker and GitHub CLI from their signed repositories, signing keys checked), no rootful Docker daemon, unattended security upgrades, private home directories, the files below, and per agent a user without sudo, rootless Docker, Claude Code at a pinned version, its role file, Git identity, the Slack plugin and its session |
| `apply.sh` | Run from a workstation: ships `agents/host`, `agents/roles`, `agents/marketplace` and `tests/agents` over IAP, runs `provision.sh` and the host checks |
| `files/egress.nft`, `files/hyprn-agents-egress.service` | Agent users and their containers reach the metadata server for DNS only, never for credentials |
| `files/hyprn-agent-secrets`, `files/hyprn-agent-secrets@.service` | Root loader: reads an agent's Slack tokens and the Slack allowlist from Secret Manager and writes them to tmpfs, readable by that agent only |
| `files/hyprn-agent-github-token`, `files/hyprn-agent-github-token@.{service,timer}` | Root token broker ([ADR-0005](../../docs/adr/0005-agent-github-app.md)): signs with the agent's GitHub App key, held in memory, and mints a one-hour installation token every 30 minutes and on each secret reload |
| `files/hyprn-git-credential`, `files/bin/gh` | Git credential helper and `gh` wrapper, both serving the agent's current installation token |
| `files/hyprn-agent@.service`, `files/hyprn-agent-session` | One tmux session per agent running Claude Code with its channel; resumes the last conversation after each boot |
| `files/hyprn-idle-stop*` | Powers the host off after 30 minutes with no SSH session, no load and no agent activity; `/run/hyprn-agents/hold` keeps it on |
| `files/profile.sh` | `PATH` (wrappers first), `XDG_RUNTIME_DIR` and `DOCKER_HOST` for agent users |

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
