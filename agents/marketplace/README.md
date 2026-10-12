# agents/marketplace

Our Claude Code plugin marketplace `hyprn-agents` (`.claude-plugin/marketplace.json`). On the agent host it is installed root-owned at `/opt/hyprn-agents/marketplace` and each agent installs from it; agents need no access to this repository.

## Plugins

| Plugin | Purpose |
|---|---|
| [`slack`](plugins/slack/) | Claude Code channel to Slack for one agent per Slack app |

## Audit record: Slack channel (2026-10-12)

Requirements ([ADR-0001](../../docs/adr/0001-agent-fleet.md) section 6): Socket Mode only; sender allowlist by Slack user ID, also for permission replies; tokens read from files; outbound only to Slack; pinned dependencies; licence allowing our use.

Community candidates reviewed:

- `Reef-Digital/claude-code-slack` (Apache-2.0): allowlist kept in a file the agent can write, with "empty list = anyone" semantics and only a skill instruction preventing self-modification; dependencies installed from npm at every start with caret ranges; needs the Bun runtime; approvals through its own shell hooks. Rejected.
- `Muneshige1567/claude-channel-slack`: no licence. Rejected.

Decision: our own server, [`plugins/slack/server.py`](plugins/slack/server.py), about 300 lines of Python using only the standard library and Debian's `python3-websocket`:

- MCP over stdio; declares `claude/channel` and `claude/channel/permission`; answers with MCP revision `2025-06-18`, since channel servers are not registered under the 2026 revision.
- Inbound only through Socket Mode (outbound WebSocket to Slack); envelopes acknowledged and deduplicated by event ID.
- Delivers only direct messages and mentions whose sender is in the root-written allowlist `/run/hyprn-agents/slack-allowed-users.json`; everything else is dropped and logged without content.
- Permission requests go to the allowlisted user's last conversation; only `yes <id>` / `no <id>` from an allowlisted sender, for an ID Claude Code issued, becomes a verdict.
- Tokens from `/run/hyprn-agents/secrets/<agent>/slack.env` (tmpfs, mode 0400, written by root); the server writes only its own deduplication state.
- Network calls go only to `slack.com` and the Socket Mode URL Slack returns.

Residual risk: the server runs as the agent user, so an agent that is already compromised could alter its installed copy or use its own bot token directly. The allowlist protects the session from other people's messages; the Linux user boundary limits what a compromised agent can reach.
