# agents/wake

Wake service for the agent host ([ADR-0002](../../docs/adr/0002-agent-host-on-demand.md)), running on `hyprn-agents-wake-01` as the unprivileged system user `hyprn-wake`.

- Every 15 seconds it reads the host's status. While the host is stopped it holds a Socket Mode connection to each agent's Slack app (outbound only); while the host runs it holds none, so the agent alone receives its app's events.
- On a direct message or mention from an allowlisted Slack user it replies that the agent is waking, starts the host and disconnects. The agent picks up that message after boot.
- Identity `hyprn-agents-wake`: get, start and stop on the host instance only, and read access to the agents' Slack secrets and the allowlist. Nothing secret is stored on disk or here.

| File | Purpose |
|---|---|
| `wake.py` | The service (Python standard library and Debian's `python3-websocket`) |
| `wake.json` | Project, zone, host and agent names |
| `hyprn-agents-wake.service` | systemd unit, hardened (no new privileges, read-only system, no home access) |
| `provision.sh`, `apply.sh` | Install on the wake VM; run `agents/wake/apply.sh` from a workstation |
