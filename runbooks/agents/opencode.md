# OpenCode on the agent host

OpenCode runs on the agent host as a second harness for Ada, steered by the platform owner over SSH. Its default model is Meta's Muse Spark 1.3 on OpenCode Zen's free tier. It is an interim tool to speed up the platform build until the model gateway exists (milestone M2).

## Data use

The free Muse Spark model is offered in exchange for Meta's use of prompts and completions to train future models ([OpenCode Zen](https://opencode.ai/docs/zen/)). Everything an OpenCode session reads can therefore reach Meta. The platform owner accepted this for `hyprn-platform` only (2026-10-13). Product repositories never enter an OpenCode session.

## Controls

| Control | Where |
|---|---|
| Pinned release, checksum verified, root-owned binary at `/usr/local/lib/opencode/opencode` | `agents/host/provision.sh` |
| Managed configuration that users and projects cannot override: default model, the `opencode` provider only (no Claude or ChatGPT sign-in), no automatic updates, sharing disabled | `agents/host/files/opencode.json` → `/etc/opencode/opencode.json` |
| Starts only inside a `hyprn-platform` checkout; takes no arguments other than `--continue` | `agents/host/files/bin/opencode` |
| Paths outside the checkout refused | `external_directory: deny` in the managed configuration |
| GitHub token minted for `hyprn-platform` only, one hour | `OPENCODE_REPOS` in `provision.sh`, `files/hyprn-agent-github-token` |
| Every push asked in the session; pushes to `main`, force pushes, `gh pr merge` and `git config` refused | `permission.bash` in the managed configuration |
| Host checks: version, policy, token scope, refusal outside `hyprn-platform` | `tests/agents/host-checks.sh` |

The session runs as the Linux user `ada`, with Ada's limits: private home, no sudo, metadata server unreachable, rootless Docker. Commits and pull requests appear as `ada-agent-hyprn[bot]`.

Residual risk: these controls are enforced by OpenCode and by wrappers running as `ada`, not by a separate identity. A command the rules do not recognize could still read Ada's other files or use Ada's all-repository token. The GitHub ruleset on `main` (Phase 1) is the hard backstop.

## Use

```bash
gcloud compute ssh hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap
sudo -iu ada
```

One task = one branch `agent/ada/<slug>` = one worktree:

```bash
[ -d ~/work/hyprn-platform ] || git clone https://github.com/hyprn-labs/hyprn-platform ~/work/hyprn-platform
git -C ~/work/hyprn-platform fetch --prune origin
git -C ~/work/hyprn-platform worktree add ~/work/platform-<slug> -b agent/ada/<slug> origin/main
cd ~/work/platform-<slug> && opencode
```

State "via OpenCode (Muse Spark)" in the pull request description. Remove the worktree after merge with `git -C ~/work/hyprn-platform worktree remove ~/work/platform-<slug>`.

## Change the model

Set `model` and `small_model` in `agents/host/files/opencode.json` and run `agents/host/apply.sh`. Free Zen models change often; check [the Zen model list](https://opencode.ai/docs/zen/) and its data terms first.

## Remove

Delete `install_opencode`, `OPENCODE_*`, `files/opencode.json`, `files/bin/opencode` and the OpenCode host checks, then run `apply.sh`. On the host: `rm -rf /usr/local/lib/opencode /etc/opencode /usr/local/libexec/hyprn-agent-bin/opencode`.

## Record

| Date | Action | Result |
|---|---|---|
| 2026-10-13 | OpenCode 1.19.0 and its policy installed by `apply.sh` | Host checks: 26 pass. As `ada` in `~/work/hyprn-platform`, the default model answers without an API key; outside a `hyprn-platform` checkout the wrapper refuses; the OpenCode token sees one repository |
