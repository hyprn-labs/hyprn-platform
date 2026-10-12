# Runbook: Slack control of agents

Each agent has its own Slack app, reached over Socket Mode by the channel plugin ([`agents/marketplace/`](../../agents/marketplace/README.md)) and, while the host is stopped, by the wake service ([`agents/wake/`](../../agents/wake/README.md)).

## 1. Slack app (per agent, Slack app settings)

1. App Manifest: paste [`slack-app-manifest.yaml`](../../agents/marketplace/plugins/slack/slack-app-manifest.yaml) with the agent's names; save; reinstall the app to the workspace.
2. Basic Information → App-Level Tokens: a token with scope `connections:write` (`xapp-…`).
3. OAuth & Permissions: Bot User OAuth Token (`xoxb-…`).
4. Store both in the company password manager.

## 2. Secret values

Copy each value to the clipboard from the password manager, then load it; the value never appears on screen or in shell history.

```bash
pbpaste | gcloud secrets versions add ada-agent-slack-app-token --project=hyprn-agents --data-file=-
pbpaste | gcloud secrets versions add ada-agent-slack-bot-token --project=hyprn-agents --data-file=-
```

The allowlist is a JSON list of Slack member IDs (`U…`). With a profile link (Slack profile → ⋯ → Copy link to profile) on the clipboard:

```bash
printf '["%s"]' "$(pbpaste | grep -oE '[UW][A-Z0-9]{6,}$')" | gcloud secrets versions add agents-slack-allowed-users --project=hyprn-agents --data-file=-
```

## 3. Claude organization settings (admin console)

Organization-wide Claude Code settings:

```json
{
  "channelsEnabled": true,
  "allowedChannelPlugins": [
    { "marketplace": "hyprn-agents", "plugin": "slack" }
  ],
  "permissions": {
    "disableBypassPermissionsMode": "disable"
  }
}
```

## 4. Provision and test

```bash
agents/host/apply.sh
agents/wake/apply.sh
```

Test: a direct message to the agent gets :eyes: and an answer; in a channel the agent belongs to, an @mention does the same. With the host stopped, a direct message gets "Waking up" and the answer after boot. A message from anyone else gets no reaction.

## Record

| Date | Step | Result |
|---|---|---|
| 2026-10-12 | Secrets | `infra/agents/` applied after plan review (9 added): secrets `agent-ada-slack-app-token`, `agent-ada-slack-bot-token`, `agents-slack-allowed-users` in europe-west1, readable by the host and wake identities only. No values yet. |
| 2026-10-12 | Slack app | Owner applied the manifest and reinstalled Ada's app; tokens stored in the company password manager. |
| 2026-10-12 | Secret values | Loaded from the clipboard with `pbpaste` (the terminal pane does not pass Ctrl-D). Checked by shape only, values never printed: app token latest `xapp-` (version 1 holds the bot token by mistake), bot token `xoxb-`, allowlist latest one valid member ID (versions 1-2 held an app ID). |
| 2026-10-12 | Provisioning | `agents/host/apply.sh` (now also shipping `agents/marketplace`): all 16 host checks pass, Slack tokens and allowlist loaded into tmpfs, plugin `slack@hyprn-agents` installed, session started with `--channels`. Session reports channels not yet enabled for the organization. `agents/wake/apply.sh`: wake service active. |
| 2026-10-12 | Cleanup | Disabled app-token version 1 and allowlist versions 1-2 (wrong values); active: app token v2, bot token v1, allowlist v3. |
| 2026-10-12 | Organization | Owner enabled channels and set `channelsEnabled`, `allowedChannelPlugins` (`hyprn-agents`/`slack`) and `disableBypassPermissionsMode` in the Claude admin console. After a session restart the channel server runs from `/opt/hyprn-agents/marketplace` with one outbound Socket Mode connection. |
| 2026-10-12 | Acceptance (D5, partial) | Direct message to Ada answered; @mention in a private channel answered after Ada was invited. Channels stay mention-only. Pending: permission relay in Slack, rejection of other senders, wake from a stopped host. |
| 2026-10-12 | Wake test 1 | Host stopped; wake service listening. Owner's direct message at 20:18:55 got the "waking" reply, host booted 20:19:14, session 20:19:19, but the message was not answered: the catch-up after start delivered nothing and left no trace (Claude Code replaced the first server instance a few seconds after start). Fix (plugin 0.1.1): catch-up repeated at 5, 30 and 90 s (delivered messages are skipped) and the server logs to `~/.local/state/hyprn-slack/server.log` (timestamps only, no message content). After deployment the missed message was delivered. |
| 2026-10-12 | Wake test 2 | Host stopped; owner's direct message woke it: start requested 20:55:07, boot 20:55:24, message delivered to Ada 20:55:57 (50 s) and answered without asking again. |
| 2026-10-13 | Secret names | Per-agent secrets renamed to `<name>-agent-<purpose>`: new secrets created (8 added), latest values copied without printing and verified identical, host loader and wake service switched. Host: 18 checks pass, tokens loaded, Slack reconnected; wake service active with no restarts. Former `agent-ada-*` secrets kept until deletion. |
