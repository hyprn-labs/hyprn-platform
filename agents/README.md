# agents

The agent fleet: background coding agents that take tasks, open draft pull requests and are steered from Slack. Decision: [ADR-0001](../docs/adr/0001-agent-fleet.md); tasks: [plan](../docs/plans/agent-fleet.md). No secrets, tokens, keys or session data here; they live in the password manager and the `hyprn-agents` secret store.

| Agent | Role | Claude seat | Slack app | GitHub App | Linux user |
|---|---|---|---|---|---|
| Ada | Coding agent | Team Standard | Ada (AI agent) | `hyprn-ada` (after publication) | `ada` |

- `roles/` — role instructions per agent.
- `policy/` — reviewed copy of the organization-wide Claude Code policy.
- `marketplace/` — our plugin marketplace with the audited Slack channel plugin.
- `host/` — agent host provisioning.
- `wake/` — wake service that starts the stopped host from Slack.
- `measurement/` — usage and cost measurement.
