# Phase 3 Plan 03: Broker + runner — Summary

**Status:** done
**Date:** 2026-10-13

## What was built

- `agents/host/files/hyprn-credential-broker` (new, executable): per-run
  broker on the hyprn-agent-secrets loader pattern. Fetches ONLY
  loop-declared secret names (never trigger payload), warns-and-continues
  on declared-but-absent, agent-owned per-run dir mode 0500, write-temp +
  chown + atomic move, 1h GitHub token mint with immediate key unset,
  `--cleanup` removal on run end, `--fixture` no-network mode for checks.
- `agents/host/files/hyprn-run-runner` (new, executable): kill-flag early
  exits, idle-stop hold registration, loop-allowlist → ALLOWED_HOSTS
  translation, per-run read-only mount, runuser agent-user exec,
  `--rm --read-only` fresh container, MODEL_BINDING config-only switch,
  broker cleanup on exit.
- `tests/agents/checks/runner.sh` (new): 19 static assertions +
  fixture-mode probe, container dry-run with SKIP fallback (no boole
  user here → SKIP, static assertion stands).

## Verifies

- `bash -n` on all three files → clean
- `tests/agents/checks/runner.sh` → 19 PASS + 1 SKIP, exit 0
- broker `--help` probe + no-key-material gate → pass
- `python3 -m unittest discover -s controller` → 12 tests OK (unchanged)

## Blocked

- Live container dry-run (disallowed-refused proof on host) needs the
  agent host with docker + boole user — recorded as SKIP; full proof at
  the 03-05 live-run checkpoint. No keys, applies, or Secret Manager
  writes performed.

## Deviations

- Auto-fix: fixture mode initially sat below the metadata token fetch,
  so `--fixture` needed network; moved the fetch below the fixture
  early-exit (no-network now proven by the passing probe).
- Design note: broker cleanup is an explicit `--cleanup` call (wired
  into the runner EXIT trap), not a broker EXIT trap — the broker must
  exit leaving the run dir for the container to mount.
