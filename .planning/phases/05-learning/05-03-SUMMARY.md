# Phase 05 Plan 03: Improvement Gate, Promotion Template, App Declaration — Summary

**Status:** done-with-blockers (code done; owner/live vendor steps blocked)
**Date:** 2026-10-14
**Requirements:** OPS-03, LRN-03, LRN-04

## What was built

Closed the learning loop on fixtures: the improvement-PR gate is
proven both directions, the promotion check ships as an honest
template, and the Boole App is declared-not-created.

- `agents/loops/meeting/prompts.md` — one small fixture improvement
  (new "Extraction multiplicity" rubric-clarity paragraph documenting
  multi-marker lines, matching the 05-01 extractor); loop YAML and
  autonomy fields untouched.
- `agents/eval/promotion.py` — promotion-check template copying the
  loop-validator structure (stdlib + PyYAML, stderr prefix, bool-style
  check plus usage-bearing main, exits 0/1/2/3): reads all three
  thresholds from the registry at check time, grades only real-origin
  runs, prints `INSUFFICIENT DATA (seeds excluded)` with non-zero exit
  under ten real runs, never writes the loop file. PASS prints template
  text only — executed promotion stays deferred to the trial.
- `runbooks/agents/learning.md` — learning runbook (seed-label rule,
  feedback-to-real replacement, improvement gate, promotion template
  use, Boole declaration + owner checklist, dated phase entry).
- `runbooks/agents/github.md` — Boole declaration row appended to the
  record table (declaration, not creation).
- `tests/agents/checks/learning.sh` — gate probes: `improvement_gate`
  (PASS verdict + prompts/skills-only diff queues for owner; FAIL
  verdict stays draft; autonomy/promotion diffs rejected) proven live
  against real runner output both directions; promotion probes
  (registry-read fidelity via tmp loop + real-origin eval,
  seed-exclusion, INSUFFICIENT DATA + non-zero exit, no autonomy
  change); declaration probes (scope, permissions, webhook inactive,
  broker path, owner checklist, no creation call, no key material).

## Verifies

- `python3 agents/eval/promotion.py agents/loops/meeting.yaml` —
  exits 3 with `INSUFFICIENT DATA (seeds excluded): 0 real runs` on
  seeds-only state (must NOT exit zero).
- `bash tests/agents/checks/learning.sh` — zero FAIL (3 live SKIP
  with reason: gateway/PR-post need agent host + broker token,
  channel wiring waits for the Boole bot).
- `bash tests/agents/run.sh` — `checks/learning` PASS; controller,
  meeting, loops stay PASS. Overall FAIL is the unchanged
  pre-existing off-host set (host-checks/accounts/codd/detect/
  egress/github/session).
- Forbidden-literal scan: no `gh pr merge` string in any new file.

## Blockers

Owner/live vendor steps (zero in-phase execution, per D-app-declared).
Exact owner commands:

1. Create the `boole-agent-hyprn` App: Organization Settings →
   Developer settings → GitHub Apps → New GitHub App, name
   `boole-agent-hyprn`, webhook inactive, Contents + Pull requests
   read and write (Metadata read automatic); note the App ID.
2. Install the App on `hyprn-platform` ONLY; record installation/bot IDs:
   `GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api orgs/hyprn-labs/installations --jq '.installations[] | "\(.app_slug) app=\(.app_id) installation=\(.id)"'`
3. Generate a private key, store the `.pem` in the company password
   manager, load it (owner only):
   `gcloud secrets versions add boole-agent-github-app-key --project=hyprn-agents --data-file=<key.pem>`
   then delete the downloaded `.pem` and run `agents/host/apply.sh`.
4. Trial owns the rest: real-run eval cases, improvement-PR merges,
   executed A1→A2 promotion after ten real runs.

## Deviations

None — plan executed as written.
