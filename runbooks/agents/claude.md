# Runbook: Claude Code organization policy

The Claude admin console serves `agents/policy/managed-settings.json` to every Claude Code session of the organization. Claude Code fetches it at start and every hour, and caches it in `~/.claude/remote-settings.json`.

## Change the policy

1. Change `agents/policy/managed-settings.json` by pull request; merge after review.
2. Claude admin console → Organization settings → Claude Code → managed settings: replace the content with the merged file, unchanged, and save.
3. Restart Ada's session so it fetches the policy: run `agents/host/apply.sh`. Its check `ada: console policy matches agents/policy/managed-settings.json` must pass, and Ada must answer in Slack.
4. Record the change below.

Never paste a policy from an unmerged branch. To undo a change, paste the previous merged version.

## Record

| Date | Change | Result |
|---|---|---|
| 2026-10-12 | Channels enabled; `allowedChannelPlugins` `hyprn-agents`/`slack`; bypass mode disabled | Ada's Slack channel registers (runbook `slack.md`) |
| 2026-10-14 | A policy from the unmerged branch of pull request 15 was pasted: no channel settings, marketplace allowlist naming a GitHub repository that does not exist, only managed permission rules, network sandbox limited to four domains | Provisioning failed at the marketplace refresh, and Ada's next restart would have lost Slack. The owner pasted back the 2026-10-12 policy; the host fetched it (identical keys) and provisioning completed |
