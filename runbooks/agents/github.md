# Runbook: agent GitHub access

Each agent reaches GitHub through its own GitHub App ([ADR-0005](../../docs/adr/0005-agent-github-app.md)); a root broker on the agent host mints one-hour installation tokens.

## Create an agent's App

1. `hyprn-labs` → Settings → Developer settings → GitHub Apps → New GitHub App: name `<name>-agent-hyprn`; homepage `https://github.com/hyprn-labs`; webhook **inactive**; repository permissions Contents and Pull requests **read and write** (Metadata read is automatic); installable only on this account.
2. Note the App ID; generate a private key; store the `.pem` in the company password manager.
3. Install the App on `hyprn-labs`, **selected repositories** only.
4. Look up the installation and bot IDs:

   ```bash
   GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api orgs/hyprn-labs/installations --jq '.installations[] | "\(.app_slug) app=\(.app_id) installation=\(.id)"'
   GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api 'users/<app>%5Bbot%5D' --jq .id
   ```

5. Add the agent's line to `agents/host/agents.txt`, load the key and provision:

   ```bash
   gcloud secrets versions add <name>-agent-github-app-key --project=hyprn-agents --data-file=<key.pem>
   agents/host/apply.sh
   ```

   Then delete the downloaded `.pem`.

## Rotate an App key

Generate a new private key on the App's page, load it as a new secret version, run `agents/host/apply.sh`, confirm the host checks pass, then delete the old key on the App's page and disable the old secret version.

## Repository access

Repositories are chosen on the App's installation (Organization → Settings → GitHub Apps → Configure). Tokens never exceed the App's permissions.

## Record

| Date | Step | Result |
|---|---|---|
| 2026-10-12 | Account and token | `hyprn-ada` member of `hyprn-labs`. Secret created by `infra/agents/` (2 added). Token versions 1 and 2 had no repository access (no repositories selected, then pending organization access); version 3 reaches `hyprn-platform` and `hyprn-mvp`. Owner granted Write on both; token shows push, no admin. |
| 2026-10-12 | Host | `apply.sh`: 18 host checks pass; token loaded into tmpfs for `ada` only; Git identity `Ada (AI agent)` with the account's no-reply address; `gh` authenticated as `hyprn-ada`; Git authenticates to `hyprn-platform`. |
| 2026-10-13 | Rename | Account renamed from `hyprn-ada` to `ada-hyprn` (numeric ID `341672319`). Token, organization membership and Write access unchanged. Git identity switched to the ID-based no-reply address, which survives renames; host re-provisioned, 18 checks pass, `gh` authenticates as `ada-hyprn`. |
| 2026-10-13 | Rename | Account renamed from `ada-hyprn` to `ada-agent-hyprn` (same numeric ID). Token, membership and Write access unchanged; commits stay attributed through the ID-based address; host re-provisioned, 18 checks pass. |
| 2026-10-13 | GitHub App | App `ada-agent-hyprn` (App ID 5299141, installation 170941397, bot user 341930344) created and installed; key loaded as `ada-agent-github-app-key` v1 and deleted from the download folder. Broker deployed; first run lost the token to a secret reload (fixed: the loader now mints on every start). Host: 20 checks pass; Ada commits as `ada-agent-hyprn[bot]`, reaches `hyprn-platform` and `hyprn-mvp`. |
