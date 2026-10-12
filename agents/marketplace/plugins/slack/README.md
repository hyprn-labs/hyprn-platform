# slack (channel plugin)

Claude Code channel connecting one agent to its own Slack app. Design and audit: [`../../README.md`](../../README.md).

- Slack app configuration: [`slack-app-manifest.yaml`](slack-app-manifest.yaml) (Socket Mode; bot scopes `app_mentions:read`, `chat:write`, `im:history`, `im:write`, `reactions:write`; events `app_mention`, `message.im`).
- Runtime inputs, written by root on the host: `/run/hyprn-agents/secrets/<agent>/slack.env` (`SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`) and `/run/hyprn-agents/slack-allowed-users.json` (JSON list of Slack user IDs).
- Session: `claude --channels plugin:slack@hyprn-agents`; the organization must enable channels and allow this plugin.
- The agent answers direct messages and mentions from allowlisted users; it reacts with :eyes: on receipt. Approvals arrive as messages asking for `yes <id>` or `no <id>`.
- After a host start, direct messages from the last 15 minutes that were not yet delivered are picked up, so the message that woke the host is answered.
