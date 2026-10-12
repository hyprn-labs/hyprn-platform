# Runbook: agent GitHub access

Ada works on GitHub through its machine account `ada-agent-hyprn` ([ADR-0004](../../docs/adr/0004-agent-github-machine-account.md)).

## Access

- `ada-agent-hyprn` is a member of `hyprn-labs` with **Write** on each repository it works on (Repository → Settings → Collaborators and teams).
- Fine-grained token: resource owner `hyprn-labs`; selected repositories; Contents and Pull requests read/write; Metadata read; expiry 90 days or less.
- Secret `agent-ada-github-token` in `hyprn-agents`, readable by the host identity only.

## Rotate the token

1. In Ada's GitHub account, generate the replacement token with the settings above; save it in the company password manager.
2. Load it from the clipboard:

   ```bash
   pbpaste | CLOUDSDK_CONFIG="$HOME/.config/gcloud-hyprn" gcloud secrets versions add agent-ada-github-token --project=hyprn-agents --data-file=-
   ```

3. Run `agents/host/apply.sh` (reloads secrets, restarts the session).
4. Delete the old token in GitHub and disable its secret version:

   ```bash
   gcloud secrets versions disable <n> --secret=agent-ada-github-token --project=hyprn-agents
   ```

## Record

| Date | Step | Result |
|---|---|---|
| 2026-10-12 | Account and token | `hyprn-ada` member of `hyprn-labs`. Secret created by `infra/agents/` (2 added). Token versions 1 and 2 had no repository access (no repositories selected, then pending organization access); version 3 reaches `hyprn-platform` and `hyprn-mvp`. Owner granted Write on both; token shows push, no admin. |
| 2026-10-12 | Host | `apply.sh`: 18 host checks pass; token loaded into tmpfs for `ada` only; Git identity `Ada (AI agent)` with the account's no-reply address; `gh` authenticated as `hyprn-ada`; Git authenticates to `hyprn-platform`. |
| 2026-10-13 | Rename | Account renamed from `hyprn-ada` to `ada-hyprn` (numeric ID `341672319`). Token, organization membership and Write access unchanged. Git identity switched to the ID-based no-reply address, which survives renames; host re-provisioned, 18 checks pass, `gh` authenticates as `ada-hyprn`. |
| 2026-10-13 | Rename | Account renamed from `ada-hyprn` to `ada-agent-hyprn` (same numeric ID). Token, membership and Write access unchanged; commits stay attributed through the ID-based address; host re-provisioned, 18 checks pass. |
