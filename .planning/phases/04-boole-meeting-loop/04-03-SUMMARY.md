# 04-03 Summary: Boole identities declared, isolation proven, trial gated

**Status:** done-with-blockers
**Date:** 2026-10-13

## What was built

- `infra/agents/boole-notion.tf` — `boole-agent-notion-token` secret
  container declared-not-created (for_each + host-only secretAccessor,
  no values); Workspace user noted as hand-created with automation
  deferred to FLT-02; no GitHub App (Phase 5 OPS-03).
- `tests/agents/checks/isolation.sh` — ACC-07 across ada/boole/codd for
  homes, secrets, containers, tokens, bots: repo-static assertions run
  anywhere; live runuser cross-read probes gate on the user existing
  and skip with reason otherwise.
- `runbooks/agents/meeting-loop-go.md` — owner-go checklist: LOOP-01
  settle, Workspace user + original-database share (Insert Content),
  token shape check, exact-plan apply, 10-meeting/$30 trial approval —
  each step with Verify line and dated-record slot.

## Verifies

- `bash tests/agents/checks/isolation.sh` — green (live legs ran for
  ada/codd on this host; boole legs skipped cleanly, no boole user yet).
- `bash tests/agents/checks/meeting.sh` — green.
- `python3 -m unittest discover -s controller` — 19/19 OK.
- No credential values committed (terraform binary absent — shape
  asserted statically instead).

## Deviations

- Replaced a vacuous double-grep broker assertion with a direct
  `$AGENT-agent-` parameterization check.
- Simplified the secret-dir check to a single find for non-400 or
  non-agent-owned files.
- Added tf shape assertions (declared-not-created, host-only accessor)
  to isolation.sh's static section; terraform binary unavailable here.

## Blocked

- **Owner go for the 10-meeting live trial (blocking-human):** the poll
  seam + A1 workflow are green on fakes, declarations are
  reviewed-not-applied, isolation passes statically. The owner must
  confirm LOOP-01 is settled and recorded, the Workspace user and Notion
  integration share exist, tokens are in Secret Manager, and the
  10-meetings-in-two-weeks within $30 trial may start — dated entry by
  hand in `runbooks/agents/meeting-loop-go.md`. Until recorded: no live
  runs, no Terraform apply, no vendor objects created.
- **Boole Linux user provisioning:** `id boole` absent on this host;
  live isolation legs for boole skip until provisioning (owner/host step).
