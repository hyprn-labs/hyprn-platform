# Phase 3 Plan 02: Controller expansion — Summary

**Status:** done
**Date:** 2026-10-13

## What was built

On the proven 03-01 slice, all on fakes (Socket Mode + gateway behind
injected seams):

- `controller/dispatcher.py` (extended): park/resume with owner-only gate
  (wake.py sender-allowlist idiom), pending-wake host signal, pre-dispatch
  budget gate over the injected spend ledger, three-scope kill flags
  (loop/agent/fleet) checked every dispatch, per-run cost ledger.
- `controller/test_dispatcher.py` (extended): TestParkedApproval
  (fake-clock multi-hour park, owner resume, stranger ignored, wake signal)
  + TestBudgetKill (over-budget refused, mid-run kill, fleet blocks all,
  cost accumulates). Suite now 12 tests, OK.
- `tests/agents/checks/controller.sh` (new): unit suite + in-memory
  schema load + POLL_SECONDS ≤ 60 bound + static shape assertions.

Parked runs hold a DB row only — no process, container, or timer retained
between park and resume (verified by construction: park() writes rows and
returns; no handle stored on the Dispatcher).

## Verifies

- `python3 -m unittest discover -s controller -v` → 12 tests OK
- `tests/agents/checks/controller.sh` → 6 PASS, exit 0

## Blocked

None — no key/cloud-gated steps in this plan. Gateway-side budget
backstop and live Socket Mode holder wait for 03-04/03-05 owner-go.

## Deviations

None — plan executed exactly as written.
