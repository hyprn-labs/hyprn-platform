# agents/host

Provisioning for the agent host `hyprn-agents-host-01` ([ADR-0001](../../docs/adr/0001-agent-fleet.md) section 4, [ADR-0002](../../docs/adr/0002-agent-host-on-demand.md)). Unrelated to the product host adapter in [`host/`](../../host/README.md). No secrets here.

| File | Purpose |
|---|---|
| `agents.txt` | Agent users: name, UID (20000–20999), display name |
| `provision.sh` | Idempotent, run as root on the host: packages (Docker and GitHub CLI from their signed repositories), no rootful Docker daemon, unattended security upgrades, host files below, and per agent a user with a private home and no sudo, rootless Docker, Claude Code at a pinned version with auto-update off, and the role file from [`../roles/`](../roles/README.md) |
| `apply.sh` | Run from a workstation: ships `agents/host`, `agents/roles` and `tests/agents` over IAP SSH, runs `provision.sh` and the host checks |
| `files/egress.nft`, `files/hyprn-agents-egress.service` | Agent users and their rootless containers cannot reach the metadata server, so they cannot use the VM identity |
| `files/hyprn-idle-stop*` | Powers the host off after 30 minutes with no SSH session, no load and no agent transcript activity; `/run/hyprn-agents/hold` keeps it on |
| `files/hyprn-agent@.service`, `files/hyprn-agent-session` | One tmux session per agent running Claude Code, resumed after each boot; extra arguments (such as `--channels`) in `/etc/hyprn-agents/agents/<name>.args`. Enabled once the agent is signed in |
| `files/profile.sh` | `PATH`, `XDG_RUNTIME_DIR` and `DOCKER_HOST` for agent users |

## Use

```bash
gcloud compute instances start hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents
agents/host/apply.sh
```

Sign an agent in (B4), then re-run `apply.sh` to start its session:

```bash
gcloud compute ssh hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap
sudo -iu ada claude      # then /login with the code sent to the agent's address
sudo -iu ada tmux attach -t agent   # watch or take over a running session (detach: Ctrl-b d)
```

On an agent's first session start, Claude Code asks once to trust `~/work`; answer it in the tmux session.
