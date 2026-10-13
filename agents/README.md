# agents

The agent fleet ([ADR-0001](../docs/adr/0001-agent-fleet.md)): engineering agents that turn Slack tasks into draft pull requests, and operations agents that run loops on schedules and events over company tools. Target: [agent fleet specification](../docs/specs/agent-fleet.md); further decisions up to [ADR-0006](../docs/adr/0006-agent-first-operating-model.md).

| Agent | Kind | Runtime | Slack app | GitHub App | Linux user | Status |
|---|---|---|---|---|---|---|
| Ada | Engineering | Claude Code, Claude Team Standard seat | Ada (AI agent) | `ada-agent-hyprn` | `ada` | In service |
| Boole | Operations | Open models at Fireworks, API key through the gateway; a fresh rootless container per run | Boole (AI agent), M2 | `boole-agent-hyprn`, after the ruleset (M2) | `boole` | Milestone M2 |

| Folder | Contents |
|---|---|
| [`roles/`](roles/README.md) | Role instructions per agent |
| [`policy/`](policy/README.md) | Reviewed copy of the organization-wide Claude Code policy |
| [`marketplace/`](marketplace/README.md) | Plugin marketplace `hyprn-agents` with the Slack channel plugin |
| [`host/`](host/README.md) | Agent host provisioning |
| [`wake/`](wake/README.md) | Wake service that starts the stopped host from Slack; grows into the fleet controller |
| [`measurement/`](measurement/README.md) | Usage telemetry for seat sessions |
