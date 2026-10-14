# Runbook: agent GitHub access

Each agent reaches GitHub through its own GitHub App ([ADR-0005](../../docs/adr/0005-agent-github-app.md)); a root broker on the agent host mints one-hour installation tokens.

## Create an agent's App

1. `hyprn-labs` → Settings → Developer settings → GitHub Apps → New GitHub App: name `<name>-agent-hyprn`; homepage `https://github.com/hyprn-labs`; webhook **inactive**; repository permissions Contents and Pull requests **read and write** (Metadata read is automatic); installable only on this account.
2. Note the App ID; generate a private key; store the `.pem` in the company password manager.
3. Install the App on `hyprn-labs`: engineering agents on Claude Code on **all repositories**; Codd on `hyprn-platform` only; operations agents on the repositories their loops change.
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

Ada's App is installed on all `hyprn-labs` repositories, Codd's on `hyprn-platform` only (Organization → Settings → GitHub Apps → Configure). Tokens never exceed the App's permissions or its installation's repositories.

## Protect `main`

`agents/github/main-ruleset.json` is the ruleset for every repository: no deletion or force push of `main`, changes through pull requests approved by a code owner (`CODEOWNERS`: the `owners` team), stale approvals dismissed, and the last push approved by someone other than its author. Organization admins may merge their own pull requests; agents' Apps cannot bypass it.

1. Create the team `owners` in `hyprn-labs` (Teams → New team, visible) and add the platform owner. Teams are available on the Free plan.
2. Once `hyprn-labs` is on the Team plan (rulesets on private repositories need it), apply the ruleset to each repository:

   ```bash
   GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api repos/hyprn-labs/<repo>/rulesets --method POST --input agents/github/main-ruleset.json
   ```

3. Check with `tests/agents/owner-checks.sh`.

Until then the Claude Code deny rules (`agents/policy/managed-settings.json`) and Codd's OpenCode policy are the only controls on `main`.

## Record

| Date | Step | Result |
|---|---|---|
| 2026-10-12 | Account and token | `hyprn-ada` member of `hyprn-labs`. Secret created by `infra/agents/` (2 added). Token versions 1 and 2 had no repository access (no repositories selected, then pending organization access); version 3 reaches `hyprn-platform` and `hyprn-mvp`. Owner granted Write on both; token shows push, no admin. |
| 2026-10-12 | Host | `apply.sh`: 18 host checks pass; token loaded into tmpfs for `ada` only; Git identity `Ada (AI agent)` with the account's no-reply address; `gh` authenticated as `hyprn-ada`; Git authenticates to `hyprn-platform`. |
| 2026-10-13 | Rename | Account renamed from `hyprn-ada` to `ada-hyprn` (numeric ID `341672319`). Token, organization membership and Write access unchanged. Git identity switched to the ID-based no-reply address, which survives renames; host re-provisioned, 18 checks pass, `gh` authenticates as `ada-hyprn`. |
| 2026-10-13 | Rename | Account renamed from `ada-hyprn` to `ada-agent-hyprn` (same numeric ID). Token, membership and Write access unchanged; commits stay attributed through the ID-based address; host re-provisioned, 18 checks pass. |
| 2026-10-13 | GitHub App | App `ada-agent-hyprn` (App ID 5299141, installation 170941397, bot user 341930344) created and installed; key loaded as `ada-agent-github-app-key` v1 and deleted from the download folder. Broker deployed; first run lost the token to a secret reload (fixed: the loader now mints on every start). Host: 20 checks pass; Ada commits as `ada-agent-hyprn[bot]`, reaches `hyprn-platform` and `hyprn-mvp`. |
| 2026-10-13 | Machine account removed | Owner revoked the fine-grained token and removed `ada-agent-hyprn` (account) from `hyprn-labs`; the organization's only member is the owner. The App stays installed on all repositories; Ada reaches `hyprn-platform` and `hyprn-mvp` and authenticates with Git. |
| 2026-10-13 | Old secret | `ada-agent-github-token` and its grant deleted by `infra/agents/` (2 destroyed); a fresh plan shows no changes. |
