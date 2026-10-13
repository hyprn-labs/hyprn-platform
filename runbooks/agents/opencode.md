# Codd: OpenCode on the agent host

Codd (AI agent) is an interim engineering agent for `hyprn-platform` and `hyprn-mvp`. It runs OpenCode under its own Linux user `codd`, steered by the platform owner in the terminal, with Meta's Muse Spark 1.3 on OpenCode Zen's free tier as its default model. It speeds up the platform and product build until the model gateway exists (milestone M2).

## Data use

The free Muse Spark model is offered in exchange for Meta's use of prompts and completions to train future models ([OpenCode Zen](https://opencode.ai/docs/zen/)). Everything a Codd session reads can therefore reach Meta. The platform owner accepted this for `hyprn-platform` (2026-10-13) and extended it to `hyprn-mvp` (2026-10-13): current development is rapid prototyping under personal accounts, and the IP moves to the future company, at which point the model binding moves to protective terms. Codd reaches the product repository `hyprn-mvp`, but no staging, prod, or secret values.

## Identity and limits

| Item | Value |
|---|---|
| Linux user | `codd` (UID 20002): private home, no sudo, rootless Docker, metadata server unreachable |
| GitHub | App `codd-agent-hyprn`, installed on `hyprn-platform` and `hyprn-mvp`; commits as `codd-agent-hyprn[bot]` |
| Slack, Workspace | None: Codd is steered in the terminal and signs in nowhere |
| Model | `opencode/muse-spark-1.3-contributor-free`, no API key (Zen's free tier) |

The operating system and GitHub set Codd's reach: other agents' homes, tokens and processes are unreadable, and its App sees two repositories. Inside that, Codd works freely: any command, any path on the host except `/run/hyprn-agents`.

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

`opencode-task` clones `hyprn-platform` on first use, fetches, creates the worktree `~/work/<task>` on branch `agent/codd/<task>` from the latest `main` (or reopens it), and runs OpenCode there in a tmux session named after the task. For `hyprn-mvp` tasks the worktree is created in the product checkout instead (`git -C ~/work/hyprn-mvp worktree add ~/work/<task> -b agent/codd/<task> origin/main`). Codd keeps working when the connection drops; detach on purpose with Ctrl-b d. Running the same command again reattaches. Codd opens a draft pull request; the owner reviews and merges.

The host stays on while Codd writes to its session, while a terminal has input, or while an SSH command runs; it powers off 30 minutes after all three stop. An idle Codd at its prompt does not keep it on; `sudo touch /run/hyprn-agents/hold` does.

After merge, remove the worktree:

```bash
sudo -u codd -H bash -lc "git -C ~/work/hyprn-platform worktree remove ~/work/<task>"
```

## Change the model

Set `model` and `small_model` in `agents/host/files/opencode.json` and run `agents/host/apply.sh`. Free Zen models change often; check [the Zen model list](https://opencode.ai/docs/zen/) and its data terms first.

## Model and terms

Codd is not retired. When the work moves under the company, change `model` and `small_model` in `agents/host/files/opencode.json` to a binding with protective terms and run `agents/host/apply.sh` (see Change the model above).

## Remove (contingency only)

If an agent is ever removed outright: remove its line from `agents/host/agents.txt` and its name from `var.agents` in `infra/agents/`, uninstall and delete its App, delete `install_opencode`, the OpenCode files and checks, then apply. On the host: `userdel -r <name>` and `rm -rf /usr/local/lib/opencode /etc/opencode /usr/local/libexec/hyprn-agent-bin/opencode*`.

## Record

| Date | Action | Result |
|---|---|---|
| 2026-10-13 | OpenCode 1.19.0 and its policy installed for Ada by `apply.sh` | Host checks: 26 pass; the default model answers without an API key |
| 2026-10-13 | Codd prepared: Linux user, policy relaxed to the Linux user boundary; OpenCode removed from Ada | App `codd-agent-hyprn` (App 5306008, installation 171119571, bot 342187193) created by the owner, installed on selected repositories. `infra/agents/` applied: secret `codd-agent-github-app-key` and the host's read access (2 added). Key loaded as v1 by the owner. |
| 2026-10-13 | `apply.sh` | Host checks: 40 pass. Codd clones `hyprn-platform` and gets "Repository not found" for `hyprn-mvp`; the default model answers. Ada's `platform-opencode` worktree and branch removed; Ada has no OpenCode token |
| 2026-10-13 | MVP reach | Owner extended Codd's reach to `hyprn-mvp` (decision, same prototyping terms; no staging, prod, or secret values). Pending owner step: install App `codd-agent-hyprn` on `hyprn-mvp` — until then Codd reads the checkout but cannot push branches there. Worktree `~/work/mvp-resume` on branch `agent/codd/mvp-resume` created for the resume. |
