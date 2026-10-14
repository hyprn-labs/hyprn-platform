# 06-03 Summary: Workspace shape, spike findings, onboarding runbook

**Status:** done-with-blockers
**Plan:** 06-fleet-as-code / 03 (wave 2, depends on 06-01)

## What was built

- `infra/agents/workspace.tf`: Workspace automation shape, code + role shape
  only — `workspace_user_admin` service account, intended prebuilt User
  Management Admin grant, steady states; admin-role grant and Ada's
  group-to-user move marked as owner console steps; DWD explicitly forbidden.
- Three time-boxed spike findings from static evidence only (no live vendor
  access from this environment; each records the blocked attempt and locks the
  manual step — a "manual step" verdict is a complete result, not a rabbit hole):
  - `runbooks/agents/workspace-finding-2026-10-14.md` (FLT-02): manual step —
    owner-console creation until a DWD-free `users.insert` is proven live.
  - `runbooks/agents/slack-icon-finding-2026-10-14.md` (FLT-03): manual step —
    manual icon upload + manual Socket Mode token creation stand.
  - `runbooks/agents/setup-token-finding-2026-10-14.md` (FLT-05): manual step —
    interactive `/login` (host.md B4) stays until a live channel test.
- `runbooks/agents/onboarding.md` (FLT-08): prerequisites, per-kind add flows
  with owner-checklist callouts and the engineering seat-invite stop, remove
  flow + manual-remainder table, vendor appendix referencing the three findings,
  dated Record table, out-of-scope items stated.

## Verifies

- Task 1 automated: finding file + workspace.tf exist; body carries an explicit
  `Standing verdict: manual step` line → PASS.
- Task 2 automated: both finding files exist with body verdict lines → PASS.
- Task 3 automated: onboarding.md exists, non-empty, covers prerequisites,
  per-kind add flows, remove + remainder table, vendor appendix, Record → PASS.
- `bash tests/agents/checks/fleet.sh` → all PASS including the new
  `onboarding runbook exists and covers both kinds plus remove` assertion,
  exit 0. No secret values printed or stored anywhere (shape/handles only).

## Deviations

- Added the `onboarding runbook exists` assertion to `tests/agents/checks/fleet.sh`
  in this plan (the plan's verification requires it but files_modified did not
  list fleet.sh). [Rule 2 - plan's own verification requirement]
- Fixed a latent pipefail bug in fleet.sh found during this plan: `grep -v`
  exits 1 on empty input, which failed the tree-unmodified check on a clean
  tree; the check now snapshots to a file with `|| true`. [Rule 1 - bug]
- Finding verdicts use an explicit body line (`Standing verdict: manual step`)
  because the plan's verify filters heading lines (`grep -v '^#'`). [Rule 1]

## Blocked

- `Task 3: Owner trial checklist plus onboarding runbook acceptance`
  (`type="checkpoint:human-verify"`, `gate="blocking-human"`): the runbook is
  written and statically verified, but the human-check — owner confirms the
  runbook stands alone and approves the deferred live-trial checklist (vendor
  approvals as go items, ~8 human actions, engineering test stopping before the
  seat invitation) — needs the owner. No live vendor step was executed; the
  live trial is deferred scope per 06-CONTEXT.md.
- Live probes behind each finding (DWD-free users.insert, apps.icon.set
  sequence, setup-token channel test) are owner-gated by design
  (automatable-as-codd only; never live vendor approvals).
