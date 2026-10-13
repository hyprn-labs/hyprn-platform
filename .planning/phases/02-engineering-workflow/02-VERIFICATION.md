---
phase: 02-engineering-workflow
verified: 2026-10-13T00:00:00Z
status: human_needed
score: 13/13 must-haves verified (implementation); 4 owner-gated live proofs pending
next_action: Owner runs the Phase 1 green run, then executes the 02-03 laptop-cockpit-install plus host-herdr-apply plus reboot-proof checklist from runbooks/agents/engineering-workflow.md.
next_command: /gsd-verify-work 1
---

# Phase 2: Engineering workflow — Verification Report

**Phase goal:** Ada turns Slack tasks into draft pull requests from clean worktrees, and the owner sees every session in one cockpit.
**Plans:** 02-01 (done), 02-02 / 02-03 / 02-04 (done-with-blockers, all blockers owner/host-gated).
**Method:** goal-backward, read-only. No applies, no mutations, no secret reads. SUMMARY.md claims cross-checked against the actual files and by executing the check scripts.

## Per-criterion verdicts (ROADMAP.md Phase 2, success criteria 1–6)

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | Slack task yields a bot-authored draft PR; Ada does not merge it | IMPLEMENTED, live proof pending owner | `TASK_TAG` regex in `agents/marketplace/plugins/slack/server.py:39` slug group character-identical to `ada-task` regex; allowlist check (line 200) precedes tag parse (line 227); `notifications/hyprn/task` notify present; `github.sh` GH-01 contract greps PASS; `grep "pr merge" bin/ slack-plugin` empty; both `gh pr merge*` denies intact in policy (count exactly 2). Live bot-author probe-PR assertion SKIP-clean, gated on Phase 1 green run. |
| 2 | Two worktrees side by side; merge/close leaves nothing behind | IMPLEMENTED, on-host re-run pending owner apply | `agents/host/files/bin/ada-task` carries `hyprn-wt-` derivation, `## What changed` / `## How verified` template, `cleanup` subcommand; `checks/worktree.sh` 28/28 PASS here (19 static + 9 hermetic live: ports 100 apart, distinct projects/DBs, zero residue). On-host proof after the 02-03 apply remains. |
| 3 | Fresh worktree runs product tests without installing toolchains | IMPLEMENTED, on-host confirmation pending owner apply | `provision.sh` floor pins (`PYTHON3_PIN`, `DOCKER_PIN`, `GH_PIN`, `GIT_PIN`); per-agent `work/.cache/{npm,pip}` sibling dirs, agent-owned `0700`, never inside worktrees; `checks/eff.sh` 15/15 PASS incl. 2 live (cache-marker round-trip). hyprn-mvp unreadable so host set stands as fallback, gap recorded in runbook — no versions guessed. |
| 4 | Laptop cockpit shows local + host sessions; host sessions run under herdr and survive reboot | IMPLEMENTED, owner-go checkpoint pending | `HERDR_VERSION="0.9.4"` + both arch SHA256 in `provision.sh`; `install_herdr()` mirrors `install_opencode()`; `herdr@.service` has `User=%i`, `Restart=on-failure`; tmux fallback present-but-disabled; hooks allowlisted, denies intact, policy valid JSON; `checks/herdr.sh` 14 PASS + 5 SKIP, exit 0; runbook COK-01 checklist (`herdr machine add`, `Remote Control`, `\| Date \|`) present. Laptop install, apply, reboot-resume are owner hands only. |
| 5 | Daily usage report posted to Slack | IMPLEMENTED, first real post pending owner | `agents/host/files/bin/ada-digest` `--dry-run` and `--zen-check` exit 0; loopback-only collector conf with spike evidence in-file; `checks/obs.sh` 14 PASS + 1 SKIP (CODD-03 row absent, owner records at checkpoint). Real 07:15 post observed after apply. |
| 6 | Codd works from herdr sessions; free-tier terms re-checked monthly | IMPLEMENTED, monthly row pending owner | herdr units are per-agent (cover Codd); digest `--zen-check` passes (`muse-spark-1.3-contributor-free` confirmed on Zen page); `obs.sh` CODD-03 staleness is SKIP-when-absent / FAIL-when-stale. First dated verdict row is owner-recorded. |

## Must-have truth verification (13 across 4 plans)

All 13 plan truths resolve to code that exists, is substantive (not stub), is wired (checks + runner + runbook), and passes its automated checks. Detail:

- **02-01 (3/3):** isolation derivation, full cleanup, PR body contract — `ada-task` + `worktree.sh` verified above; `run.sh` shows `SCRIPT-PASS checks/worktree`.
- **02-02 (3/3):** task-to-branch/PR intake, no self-merge path, no machine-account resurrection — `server.py` diff is +27 lines, transport/scopes/catch-up untouched; `github.sh` 8 new checks PASS; `hyprn-ada` / `ada-agent-github-token` greps empty outside the historical record. Documented deviations accepted: live refusal delegated to Phase 1 D-08 markers (no real merge attempt — correct call); GH-03 guard excludes its own file (self-match avoidance, commented).
- **02-03 (3/3):** herdr runtime + resume + cockpit-from-checklist — verified above. Documented deviations accepted: no `ARGS_FILE` in `herdr-session` (herdr server takes no harness args — correctness call); regression tail runs siblings, not `run.sh` (avoids recursion, same coverage).
- **02-04 (4/4):** pinned toolchains, persistent caches, daily digest, monthly terms check — verified above. Documented deviations accepted: cost attributed not estimated (no metered price table — fiction avoided); cron via `/etc/cron.d` heredoc (keeps plan file list exact); pipefail SIGPIPE bug found by testing and fixed.

**Pre-existing failures (not phase regressions):** `run.sh` Overall FAIL off-host is environmental only — `SCRIPT-FAIL checks/github` comes solely from the 4 `runuser`/App-installation checks needing root + owner creds + metadata server (4 FAILs also present with phase files untouched by the failure path; untouched sibling scripts fail identically). `shellcheck` unavailable in this environment; `bash -n` plus executed proofs substituted, host to re-run where available.

## Human verification required (owner/host-gated — not implementation failures)

1. **Phase 1 green run** (`/gsd-verify-work 1`) — precondition for the GH-01 bot-author proof, COK-02 live proof, and OBS-01 live proof.
2. **02-03 checkpoint:** laptop herdr 0.9.4 install, `herdr machine add` over IAP SSH, `machine status` reachable, `agents/host/apply.sh` for exactly the reviewed diff, host `run.sh`, reboot-resume confirmation; evidence dated row + `live/herdr-reboot.ok`.
3. **Live GH-01 bot-author proof:** `GH01_PROBE_PR=<n> tests/agents/checks/github.sh` after a probe-task draft PR exists.
4. **02-04 checkpoint:** apply for the toolchain/telemetry delta, host `run.sh`, first real 07:15 Slack post confirmed, initial CODD-03 verdict row; evidence dated rows + `live/digest-first-post.ok`.

## Gaps summary

No implementation gaps. The four outstanding items are all live proofs that require the owner's hands, the laptop, the host, or Phase 1 green — they cannot be closed from this environment and are classified `human_needed`, not failed.

---
_Verified: 2026-10-13_
_Verifier: gsd-verifier (read-only)_
