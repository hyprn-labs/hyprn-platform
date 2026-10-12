# slack (channel plugin)

Claude Code channel connecting one agent to its own Slack app. Design and audit: [`../../README.md`](../../README.md).

- Slack app: [`slack-app-manifest.yaml`](slack-app-manifest.yaml) — Socket Mode; bot scopes `app_mentions:read`, `chat:write`, `im:history`, `im:write`, `reactions:write`; events `app_mention`, `message.im`.
- Inputs, written by root on the host: `/run/hyprn-agents/secrets/<agent>/slack.env` (`SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`) and `/run/hyprn-agents/slack-allowed-users.json` (Slack member IDs).
- Session: `claude --channels plugin:slack@hyprn-agents`, allowed by the organization's `allowedChannelPlugins`.
- The agent answers direct messages, and mentions in channels it belongs to, from allowlisted users, reacting with :eyes: on receipt. Approvals arrive as messages asking for `yes <id>` or `no <id>`.
- After each start it delivers direct messages from the last 15 minutes not yet seen, retried at 5, 30 and 90 seconds, so the message that woke the host is answered.
- Log: `~/.local/state/hyprn-slack/server.log` (connections, deliveries, catch-up; no message content).
