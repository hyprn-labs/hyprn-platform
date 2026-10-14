# Finding: FLT-03 Slack app icon probe (apps.icon.set manager-app constraint)

**Date:** 2026-10-14
**Probe:** FLT-03 — can the generated icon be set via `apps.icon.set` (scope
`app_configurations:write`) on an app created via `apps.manifest.create` from
the reviewed `agents/marketplace/plugins/slack/slack-app-manifest.yaml`?
**Time-box:** ~2h, static evidence only (no live vendor access from this environment).

## Verdict: MANUAL STEP

Standing verdict: manual step. Manual icon upload (plus manual Socket Mode token
creation, spec section 12) is the standing procedure until a live
create-via-manifest-API then set-icon sequence is proven by the owner.

## Evidence

- Documented constraint: a manager app may set icons only for apps it created
  via `apps.manifest.create`; the endpoint needs scope
  `app_configurations:write`. The reviewed manifest pins the required scopes
  (app_mentions:read, chat:write, im:history, im:write, reactions:write, plus
  socket mode) — the input artifact for the live probe exists.
- This environment has no Slack vendor access, so no live
  manifest-create/set-icon sequence was possible here; the probe is recorded
  as blocked, not as a negative result.
- The working manual fallback is proven in-repo: paste the manifest in app
  settings, reinstall, upload the icon by hand (runbooks/agents/slack.md step
  1, dated record 2026-10-12).

## Standing procedure

1. Paste `agents/marketplace/plugins/slack/slack-app-manifest.yaml` with the
   agent's names; save; reinstall the app to the workspace.
2. Upload the generated icon by hand in the app settings.
3. Create the App-Level Token (`connections:write`, shape `xapp-`) and Bot
   User OAuth Token (shape `xoxb-`) by hand; store both in the company
   password manager; owner loads values to the `<name>-agent-slack-*` Secret
   Manager paths (never through scripts).

## Secrets

None handled: verified by shape only (`xapp-`, `xoxb-`); no values printed or stored.
