# Phase 05 Plan 02: Full Eval Corpus and Runner — Summary

**Status:** done
**Date:** 2026-10-14
**Requirements:** LRN-02, LRN-03

## What was built

Expanded the 05-01 tracer into the full eval corpus and runner that
the 05-03 improvement gate runs against, every check green off-host.

- `agents/loops/meeting-eval.jsonl` — 20 seed lines (every line
  `origin: seed`, `seed-` id prefix), non-empty regression subset
  (12/20), covering: multi-decision, multi-action, open-question-only,
  empty and malformed degrade-to-propose-nothing (3 shapes: empty
  strings, whitespace body, null body), 3 injection-attempt pages that
  grade propose-only with empty patch, quote-the-source positives.
  No thresholds hard-coded; registry pointer untouched.
- `agents/loops/testdata/eval-fixtures/` — `SEED-README.md` header
  (seed-only, no real meeting text, no credentials), 4 canned input
  pages (`seed-page-good/malformed/injection/empty.json`, flat
  page-JSON convention), 4 canned model outputs keyed by case id
  (`seed-001/004/005/006.json`) consumed by the runner offline.
- `agents/eval/run.py` — fixture/live/post modes: sorted
  `seed-page-*.json` smoke scan (`fixture pages: N/N shape-ok`),
  tampered canned outputs fail the gate, live gateway path as a strict
  superset (declared-tools guard reading names ONLY from the reviewed
  loop file, broker token flow, SKIPs with reason off-host), `--post`
  prints the draft-PR `## Eval result` section with seed-labeled
  tallies, `--post-pr` guards on broker token + `gh` (SKIP off-host).
  Deterministic verdicts remain the only gate. No `gh pr merge`
  literal anywhere in the new code.
- `tests/agents/checks/learning.sh` — extended probes: 20-case
  minimum, injection/malformed coverage, injection propose-only +
  empty-patch, full-set fixture green, tampered-canned rejection,
  declared-secrets marker, `--run`/`--post` flag presence, offline
  post-section shape, live paths SKIP with reason, secret guard
  extended to eval + fixtures + runner output + loop file.

## Verifies

- 20-case probe: `len>=20`, all `origin==seed`, regression non-empty.
- `run.py --fixture eval-fixtures`: `fixture pages: 4/4 shape-ok`,
  `seed: 20/20 pass`, `overall: PASS`.
- `bash tests/agents/checks/learning.sh` — zero FAIL (3 live SKIP
  with reason: gateway needs agent host, PR post needs broker token,
  channel wiring waits for the Boole bot owner step).
- `bash tests/agents/run.sh` — `checks/learning` PASS; controller,
  meeting, loops stay PASS. Overall FAIL is the unchanged
  pre-existing off-host set (host-checks/accounts/codd/detect/
  egress/github/session), identical before this plan.

## Blockers

None. Live gateway grading, PR posting, and real-run cases arrive
with the host/trial and are SKIP-with-reason probes, not blockers.

## Deviations

None — plan executed as written. (The 05-01 extractor fixes that this
plan inherits were committed under 05-01.)
