# agents

The agent fleet ([ADR-0001](../docs/adr/0001-agent-fleet.md)): background coding agents that take tasks in Slack, work in their own worktrees and open draft pull requests that humans review and merge.

| Agent | Role | Claude seat | Slack app | GitHub account | Linux user |
|---|---|---|---|---|---|
| Ada | Coding agent | Team Standard | Ada (AI agent) | `ada-agent-hyprn` | `ada` |

| Folder | Contents |
|---|---|
| [`roles/`](roles/README.md) | Role instructions per agent |
| [`policy/`](policy/README.md) | Reviewed copy of the organization-wide Claude Code policy |
| [`marketplace/`](marketplace/README.md) | Plugin marketplace `hyprn-agents` with the Slack channel plugin |
| [`host/`](host/README.md) | Agent host provisioning |
| [`wake/`](wake/README.md) | Wake service that starts the stopped host from Slack |
| [`measurement/`](measurement/README.md) | Usage and cost measurement |
