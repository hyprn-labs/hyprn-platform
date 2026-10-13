# Codd: OpenCode on the agent host

Codd (AI agent) is an interim engineering agent for `hyprn-platform`. It runs OpenCode under its own Linux user `codd`, steered by the platform owner in the terminal, with Meta's Muse Spark 1.3 on OpenCode Zen's free tier as its default model. It speeds up the platform build until the model gateway exists (milestone M2).

## Data use

The free Muse Spark model is offered in exchange for Meta's use of prompts and completions to train future models ([OpenCode Zen](https://opencode.ai/docs/zen/)). Everything a Codd session reads can therefore reach Meta. The platform owner accepted this for `hyprn-platform` only (2026-10-13). Codd has no access to product repositories.

## Identity and limits

| Item | Value |
|---|---|
| Linux user | `codd` (UID 20002): private home, no sudo, rootless Docker, metadata server unreachable |
| GitHub | App `codd-agent-hyprn`, installed on `hyprn-platform` only; commits as `codd-agent-hyprn[bot]` |
| Slack, Workspace | None: Codd is steered in the terminal and signs in nowhere |
| Model | `opencode/muse-spark-1.3-contributor-free`, no API key (Zen's free tier) |

The operating system and GitHub set Codd's reach: other agents' homes, tokens and processes are unreadable, and its App sees one repository. Inside that, Codd works freely: any command, any path on the host except `/run/hyprn-agents`.

The managed configuration `/etc/opencode/opencode.json` (from `agents/host/files/opencode.json`, root-owned, not overridable) also:

- loads only the `opencode` provider, so no Claude or ChatGPT sign-in is ever used;
- turns off automatic updates and session sharing;
- refuses pushes to `main`, force pushes, `gh pr merge` and global Git configuration changes; asks before `gh api`.

The GitHub ruleset on `main` (Phase 1) is the hard backstop for pushes and merges.

## Use

From the laptop, one terminal or herdr pane per task (lowercase task name, letters, digits and dashes):

```bash
CLOUDSDK_CONFIG=$HOME/.config/gcloud-hyprn gcloud compute ssh hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap -- -t 'sudo -u codd -H bash -lc "opencode-task <task>"'
```

`opencode-task` clones `hyprn-platform` on first use, fetches, creates the worktree `~/work/<task>` on branch `agent/codd/<task>` from the latest `main` (or reopens it), and runs OpenCode there in a tmux session named after the task. Codd keeps working when the connection drops; detach on purpose with Ctrl-b d. Running the same command again reattaches. Codd opens a draft pull request; the owner reviews and merges.

The host stays on while Codd writes to its session, while a terminal has input, or while an SSH command runs; it powers off 30 minutes after all three stop. An idle Codd at its prompt does not keep it on; `sudo touch /run/hyprn-agents/hold` does.

After merge, remove the worktree:

```bash
sudo -u codd -H bash -lc "git -C ~/work/hyprn-platform worktree remove ~/work/<task>"
```

## Change the model

Set `model` and `small_model` in `agents/host/files/opencode.json` and run `agents/host/apply.sh`. Free Zen models change often; check [the Zen model list](https://opencode.ai/docs/zen/) and its data terms first.

## Retire

Remove Codd's line from `agents/host/agents.txt` and `codd` from `var.agents` in `infra/agents/`, uninstall and delete the App `codd-agent-hyprn`, delete `install_opencode`, the OpenCode files and checks, then apply. On the host: `userdel -r codd` and `rm -rf /usr/local/lib/opencode /etc/opencode /usr/local/libexec/hyprn-agent-bin/opencode*`.

## Record

| Date | Action | Result |
|---|---|---|
| 2026-10-13 | OpenCode 1.19.0 and its policy installed for Ada by `apply.sh` | Host checks: 26 pass; the default model answers without an API key |
| 2026-10-13 | Codd prepared: Linux user, policy relaxed to the Linux user boundary; OpenCode removed from Ada | App `codd-agent-hyprn` (App 5306008, installation 171119571, bot 342187193) created by the owner, installed on selected repositories. `infra/agents/` applied: secret `codd-agent-github-app-key` and the host's read access (2 added). Key loaded as v1 by the owner. |
| 2026-10-13 | `apply.sh` | Host checks: 40 pass. Codd clones `hyprn-platform` and gets "Repository not found" for `hyprn-mvp`; the default model answers. Ada's `platform-opencode` worktree and branch removed; Ada has no OpenCode token |
