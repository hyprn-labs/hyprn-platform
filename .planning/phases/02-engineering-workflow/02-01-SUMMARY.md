# 02-01 Tracer: worktree helper + PR contract — Summary

**Status:** done (static complete; live hermetic green here, on-host proof gated — see Blocked)
**Date:** 2026-10-13

## What was built

- `agents/host/files/bin/ada-task` (new, executable): shared Ada successor of
  `opencode-task` (untouched for Codd). Slug regex verbatim plus the
  `hyprn-platform` reservation; fetch-prune plus reopen-if-exists; index-derived
  env (`WORKTREE_INDEX` default 0, `PORT_BASE` 20000, stride 100,
  `COMPOSE_PROJECT_NAME="hyprn-wt-${WORKTREE_INDEX}-<slug>"`,
  `TEST_DB="hyprn_test_wt<index>"`); product env read with `${VAR:-default}` so
  the helper works without hyprn-mvp overrides; `cleanup` subcommand (worktree
  remove + branch delete + exact-prefix volume removal + dropdb + sibling
  `.env` removal); `pr-body` subcommand emitting the literal `## What changed` /
  `## How verified` template. No merge step anywhere.
- `tests/agents/checks/worktree.sh` (new, executable, wired into `run.sh`
  automatically): 19 static greps (derivation, stride, quoting,
  sibling-state, contract headings, no-merge, fail-fast host gate) plus a
  hermetic live two-worktree proof (temp clone with origin pointed at itself,
  consecutive indexes → ports 100 apart, distinct projects/DBs, full cleanup
  with zero residue) that SKIP off-host via the `id ada` guard.

## Verify results

- `bash -n` clean on both files; `tests/agents/checks/worktree.sh`: 28/28
  PASS (19 static + 9 live; live ran because this machine has the `ada` user,
  fully hermetic — real repo verified residue-free after).
- `grep -rn "pr merge"` over both files: only the check's own assertion text,
  no merge step.
- `tests/agents/run.sh`: `checks/worktree` SCRIPT-PASS. Full-suite Overall is
  FAIL on pre-existing environmental grounds only (no root/runuser/metadata
  here; untouched scripts fail identically — see 02-04 summary for the table).

## Deviations

- None from plan. Note: `shellcheck` is not installed in this environment (no
  sudo to install) — `bash -n` plus the executed live proof substituted; the
  host apply should re-run `shellcheck` where available (Blocked, item 5).

## Blocked

1. **Live two-worktree proof on-host after the 02-03 owner-go apply** —
   command: `tests/agents/checks/worktree.sh` as root on hyprn-agents-host-01 —
   who: platform owner (apply go) — go needed: `agents/host/apply.sh` for the
   reviewed 02-03 delta, then the script's live section runs for real.
