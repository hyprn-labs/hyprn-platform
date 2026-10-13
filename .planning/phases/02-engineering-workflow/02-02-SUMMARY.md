# 02-02 Slack-to-PR intake — Summary

**Status:** done-with-blockers (1: live bot-author proof gated on Phase 1 green)
**Date:** 2026-10-13

## What was built

- `agents/marketplace/plugins/slack/server.py` (+27 lines only, transport /
  scopes / catch-up untouched): `TASK_TAG` with the slug group
  character-identical to the `ada-task` regex; `_deliver` handling after the
  VERDICT block (allowlist + `seen.json` dedupe + catch-up apply unchanged,
  parsing stateless from the message only) emitting
  `notify("notifications/hyprn/task", {slug, goal, repo, branch, channel,
  thread_ts})` alongside the existing channel notify; repo defaults to
  `platform`, `--repo mvp` suffix switches to `mvp`; no new imports (stdlib
  `re` already present); no text reply (eyes reaction stays the ack; params
  carry slug/branch only, never tokens).
- `tests/agents/checks/github.sh` (+GH-01/GH-03/live groups): GH-01 contract
  greps (both headings, `agent/<name>/<slug>` branch shape, intake/helper slug
  agreement, no `gh pr merge` in helper or intake, both merge-deny backstop
  entries intact); GH-03 negative greps (`hyprn-ada`, `ada-agent-github-token`
  absent from `agents/`+`tests/`); live bot-author group SKIP-clean until a
  probe PR exists (see Blocked).

## Verify results

- `py_compile` clean; inline tag assertions print `TAG-OK`; `git diff --stat`
  shows only `server.py`; allowlist check still precedes tag parsing.
- `checks/github.sh`: all 8 new checks PASS, live lines SKIP naming the Phase 1
  green-run gate. The script's only FAILs are the 4 pre-existing
  `runuser`-based App-installation checks, proven identical on the stashed
  baseline (this environment has no `runuser`; they run as root on the host).
- Plan verification greps: `hyprn-ada` outside the historical record → empty;
  `pr merge` in `bin/`+slack plugin → empty.

## Deviations

- **Live merge-attempt assertion not implemented as a real merge attempt.**
  Attempting `gh pr merge` from automation risks merging a real PR and proves
  nothing the policy deny plus Phase 1 D-08 live-refusal markers don't already
  cover. Instead: static check that both `gh pr merge*` deny entries exist in
  `managed-settings.json`, with the live refusal explicitly delegated to the
  D-08 markers in `checks/session.sh`. No plan acceptance criterion required a
  real merge attempt.
- **GH-03 guards exclude `github.sh` itself** (`--exclude=github.sh`): the
  guard necessarily names the strings it guards; without the exclusion it
  self-matches. Documented in the script comment.

## Blocked

1. **Live GH-01 bot-author proof** — command:
   `GH01_PROBE_PR=<n> tests/agents/checks/github.sh` (asserts author
   `ada-agent-hyprn[bot]`, draft state, both contract headings) — who:
   platform owner — go needed: Phase 1 green run (`/gsd-verify-work 1`) proving
   the deny backstop, then a probe task draft PR to assert against.
