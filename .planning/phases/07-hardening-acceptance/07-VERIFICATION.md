---
status: human_needed
score: 6/8
phase: 07-hardening-acceptance
verified: 2026-10-14
next_action: Owner applies the observe-to-enforce flip on the agent host per runbooks/agents/egress-enforce.md, runs the per-agent no-break drill live, then runs the full tests/agents/run.sh as root with enforcement on and confirms the green dated record.
next_command: "On the agent host as root: follow runbooks/agents/egress-enforce.md (render, squid -k parse, reload, drill), then tests/agents/run.sh"
---

# Phase 7: Hardening and acceptance — Verification Report

**Goal:** The fleet runs with egress enforced and every control proven in one final run.
**Requirements:** EGR-02, ACC-10.
**Mode:** Goal-backward; all auto work verified in codebase, live steps are owner gates.

## Per-criterion verdicts

### SC1 — The egress allowlist is enforced without breaking Ada's or Boole's work (EGR-02)

**Verdict: CONFIG-COMPLETE, LIVE-PROOF PENDING (owner gate).**

Evidence (all read in working tree, branch `agent/codd/phase-1-discuss`):

- `agents/policy/egress-allowlist.txt` — carries all 7 declared destinations
  (`github.com`, `api.github.com`, `api.anthropic.com`, `registry.npmjs.org`,
  `api.notion.com`, `slack.com`, `gateway.internal`), an explicitly empty
  observed section (observe mode never ran live — no fabricated entries), and a
  fail-closed header. Verified by per-domain grep: all 7 OK.
- `agents/host/files/squid-hyprn.conf` — generated-ACL reference
  (`dstdomain "/etc/squid/hyprn-allowlist.acl"`), per-port allow stanzas
  (`http_access allow ada_port/codd_port allowlist`), explicit per-port denies
  plus `deny all` tail, `%lp` logformat preserved. Verified by grep.
- `runbooks/agents/egress-enforce.md` — render gate (empty output aborts, old
  ACL kept), `squid -k parse` pre-check before reload, one-command rollback to
  observe mode, first-live-observation mining procedure, A1 subdomain-form
  host confirmation step. Verified: `rollback` + `first-observation` present.
- `tests/agents/checks/egress.sh` — static drill loop (fleet-registry ada/codd
  routine set + Boole loop set by name) plus enforce-triple shape asserts;
  live probes degrade to `SKIP` off-host via host gate. `bash -n` clean.
- Live run of `bash tests/agents/checks/egress.sh` off-host: **17 PASS**
  (6 config-shape + 11 drill), all live probes SKIP, exit 0.

What is NOT proven: the live flip was never applied (no host apply in 07-01 by
design; 07-02 Checkpoint 1 NOT executed). Enforcement without breaking work is
proven statically only; live proof (allowed OK login+container, disallowed
refused+logged, direct drops) requires the owner on the host.

### SC2 — The full `tests/agents/run.sh` passes and its dated record is kept (ACC-10)

**Verdict: NOT RUN — owner gate pending.**

Evidence:

- `tests/agents/run.sh` aggregates `host-checks.sh` + every `checks/*.sh` and
  appends a dated record under `runbooks/agents/` — harness intact, no new
  check domains added by this phase (per CONTEXT aggregate-not-duplicates).
- Existing records `runbooks/agents/checks-2026-10-13.md` /
  `checks-2026-10-14.md` show **Overall: FAIL** with `checks/egress: FAIL` —
  these are pre-acceptance off-host runs, not the final acceptance artifact.
  No green record with enforcement on exists.
- 07-02 Checkpoint 2 (owner runs final aggregate run) NOT executed by design.

## Must-have score (6/8 auto items verified; 2 owner-gated)

| # | Must-have | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Allowlist fail-closed with empty observed section | VERIFIED | 7/7 domains present, empty observed header |
| 2 | Squid per-agent allow/deny + default-deny + render gate | VERIFIED | ACL ref, per-port allow+deny, `deny all` |
| 3 | One-command rollback to observe mode | VERIFIED | runbook rollback block |
| 4 | End-to-end static slice passes without a host | VERIFIED | 17 PASS, exit 0 |
| 5 | enforcement-on + drill asserts in egress.sh (observe assert replaced) | VERIFIED | `bash -n` clean, `allowlist`+`SKIP` present |
| 6 | Flip + final run happen only as owner-go checkpoints | VERIFIED | both checkpoints defined blocking-human, never automated |
| 7 | Live no-break drill (allowed OK, disallowed refused+logged) | PENDING-OWNER | static half green; live half needs host |
| 8 | Full run.sh green with enforcement on + kept dated record | PENDING-OWNER | no green record exists |

## Human verification required (owner gates)

1. **Enforce flip + live no-break drill** — owner follows
   `runbooks/agents/egress-enforce.md` on the host (confirm A1 subdomain form,
   render, `squid -k parse`, reload; drill ada/codd/Boole-loop path live with
   rollback loaded). Confirm: allowed OK login+container, disallowed refused
   + logged with port label, direct drops; or rollback executed on failure.
2. **Final aggregate acceptance run** — owner runs full `tests/agents/run.sh`
   on the host as root with enforcement on; confirm overall PASS and report the
   kept `runbooks/agents/checks-<DATE>.md` path. Any red domain returns to a
   fix plan, not to verify-work.

## Gaps

None blocking from agent work. The two pending items are the designed owner
checkpoints, not defects.
