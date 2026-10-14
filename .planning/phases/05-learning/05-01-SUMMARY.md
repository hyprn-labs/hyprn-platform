# Phase 05 Plan 01: Tracer Feedback-to-Eval Slice — Summary

**Status:** done
**Date:** 2026-10-14
**Requirements:** LRN-01, LRN-02

## What was built

Thinnest end-to-end learning slice: owner feedback stored with runs
(`controller/`), a seed-labeled eval file graded offline (`agents/`),
and a learning check wired into the one-command suite (`tests/`).
All seeds labeled seeds everywhere; no fabricated real results.

- `controller/schema.sql` — new `feedback` table beside runs/approvals
  (run reference, closed-kind text, JSON payload, sender, unique dedupe
  key, `datetime('now')` default; portable types only).
- `controller/dispatcher.py` — `Dispatcher.record_feedback` (closed
  `FEEDBACK_KINDS`, run-existence check before insert, repeated dedupe
  key returns the stored row id) plus approval-answer capture as one
  extra insert inside the existing owner-gated `resume` path, so
  stranger answers store nothing.
- `controller/test_feedback.py` — 4 TestCases (closed kinds, dedupe
  idempotency, unknown-run refusal, approval pairing incl. stranger
  gate), same fresh-DB/registry fakes as `test_dispatcher.py`.
- `agents/loops/meeting-eval.jsonl` — 6 seed lines, every line
  `origin: seed` with `seed-` id prefix, non-empty regression subset,
  fixture-shaped pages, rubric-shaped expectations; covers empty and
  malformed degrade-to-propose-nothing plus an injection-attempt page
  that must be quoted-not-followed.
- `agents/eval/run.py` — offline runner: `--fixture` grades every case
  deterministically (contract keys, required sources quoting page
  text, malformed must propose nothing), zero network/tokens; `--run`
  live path is a stub flag for 05-02; report prints `seed:` and
  `real:` tallies on separate lines.
- `tests/agents/checks/learning.sh` — executable check (auto-discovered
  by `run.sh`): schema/writer markers, unit suite green, JSONL origin +
  regression + page-shape probes, runner offline probes, live paths
  SKIP with reason off-host, secret-pattern guard over new files and
  runner output.

## Verifies

- `python3 -m unittest discover -s controller` — 26 tests, OK.
- `bash tests/agents/checks/learning.sh` — zero FAIL (2 live SKIP with
  reason: gateway path needs agent host, channel-server wiring waits
  for the Boole bot owner step).
- `bash tests/agents/run.sh` — `checks/learning` PASS; controller,
  meeting, loops stay PASS. Overall FAIL is pre-existing and unchanged:
  host-checks/accounts/codd/detect/egress/github/session fail off-host
  (agent-host users, DNS, live installations), identical set to the
  2026-10-13 record before this plan.

## Blockers

None. Owner/live items (Boole bot wiring, gateway live path) are
SKIP-with-reason probes, not blockers.

## Deviations

Two Rule-1 auto-fixes in the fixture extractor (`agents/eval/run.py`):
fixture bodies carry several markers on one line, so per-line
elif became independent per-marker checks, and repeated markers
(`DECISION: ... DECISION: ...`) became segment splits. Both found via
the runner's own FAIL output, verified by re-running to 6/6 PASS.
