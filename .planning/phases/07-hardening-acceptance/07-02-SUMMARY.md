# 07-02 Summary: Enforcement-on assertions + drill (live gated)

**Plan:** 07-02 (wave 2, EGR-02 + ACC-10) — `checks/egress.sh` extended with
enforcement-on plus per-agent no-break drill assertions (static halves run
anywhere, live halves owner-gated). No new check domains. The live flip and
final aggregate run are owner-go checkpoints and were NOT executed.

## Tasks

1. **Enforcement-on plus drill assertions in egress.sh (auto, done)** —
   appended, not rewritten: static enforce-triple asserts (generated-ACL
   reference, per-port allow coverage, allowlist renders non-empty), a static
   per-agent drill loop (fleet-registry ada/codd routine set + Boole loop set
   of `gateway.internal`, `api.notion.com`, `slack.com` by name — Boole has no
   fleet entry or Squid port), live host-only probes (allowed succeeds login
   + container, disallowed refused + logged with agent port label, direct
   bypass drops). Observe-mode no-blocking assertion replaced with the
   enforce-mode per-port-deny counterpart (resolves the 07-01 transitional
   state). Cloud Logging flow check kept. Every live probe degrades to a clear
   `SKIP` off-host via a host gate (root + `nft` + table loaded).
2. **Checkpoint: owner applies enforce flip and runs no-break drill
   (blocking-human, NOT executed)** — see ## Blocked.
3. **Checkpoint: owner runs final aggregate acceptance run (blocking-human,
   NOT executed)** — see ## Blocked.

## Verify

- `bash -n tests/agents/checks/egress.sh` — clean.
- `EGRESS-CHECKS-OK` (`allowlist` + `SKIP` content greps) — pass.
- Static run off-host: 17 PASS (6 config-shape + 11 drill), all live probes
  SKIP, exit 0. No scope change, no deviations.

## Blocked

- **Checkpoint 1 (blocking-human): owner applies enforce flip and runs
  no-break drill.** Owner follows `runbooks/agents/egress-enforce.md` on the
  host: confirm the A1 subdomain form on the host Squid version, render and
  reload the enforce config, run the per-agent drill live for ada, codd, and
  the Boole loop path (allowed OK login + container, disallowed refused +
  logged, direct drops), rollback loaded and ready. Resume only on owner
  confirmation; failure means rollback first, then a fix plan. The agent must
  never run this.
- **Checkpoint 2 (blocking-human): owner runs final aggregate acceptance
  run.** Owner runs the full `tests/agents/run.sh` on the host as root with
  enforcement on, confirms overall PASS plus the appended dated record under
  `runbooks/agents/`. That kept record is the final acceptance artifact
  (ACC-10). Resume only on owner confirmation of the green run and record
  path; any red domain returns to a fix plan, not to verify-work. The agent
  must never run this.
- Phase gate: owner-confirmed green `run.sh` with enforcement on before
  verify-work.

## Files

- `tests/agents/checks/egress.sh` (modified)
- `runbooks/agents/egress-enforce.md` (unchanged — already holds the flip,
  rollback, and observation procedures from 07-01)
- Final `runbooks/agents/checks-<DATE>.md` record: pending owner Checkpoint 2.
