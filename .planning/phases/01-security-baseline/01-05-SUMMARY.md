# Phase 01 Plan 05: Session Proofs, Codd Both-Repo Scope, Final Sweep — Summary

**Phase:** 01-security-baseline
**Plan:** 05
**Status:** done-with-blockers (2 blockers — both live owner-hand tests, per plan)
**Date:** 2026-10-13

## Objective

Close Phase 1: live session proofs for the Slack relay and refusal behavior
(ACC-01/02/03), both-repository Codd scope with stale-line corrections
(CODD-01 groundwork per D-03), and the final full green check run with its
dated record (ACC-08, roadmap criteria 3/6/7).

## What was done

### Task 1 — `tests/agents/checks/session.sh` (new, executable)

Live session checks in the host-checks idiom (ACC-01/02/03, D-08), 9 named
`check` definitions expanding to 13 executions at runtime:

- Relay precondition: Slack allowlist root-owned, owner-only.
- `relay-owner-yes` / `relay-owner-no` / `relay-non-owner-rejected` (ACC-01).
- `allowlist-silence` — non-listed senders get no reaction, reach no session,
  wake nothing (ACC-02).
- Per repository (`hyprn-platform`, `hyprn-mvp`): merge, push-to-main,
  force-push, and bypass-mode refusals (ACC-03, POL-04 interim proof).

Slack-driven steps are performed live by the owner and recorded as marker
files `runbooks/agents/live/<test-id>.ok` (date first line, `owner:
<principal>` second line); a missing marker fails its check — nothing
simulates the sender. Command-text variants per refusal family are defined in
`runbooks/agents/live/README.md` (new): `gh pr merge` + `--admin` variants,
`git push origin main` / `+main:main` / `HEAD:main` / `git -C` variants,
`--force` / `-f` / `+HEAD:main` variants, and bypass invocations.

Verify: `SESSION_CHECKS_OK` (bash -n clean, 9 named checks ≥ 5).

### Task 2 — `tests/agents/checks/codd.sh` (new, executable) + host-check fix

Codd scope checks (CODD-01, D-03/D-04), 14 named checks:

- Per-repo App installation assertions (`hyprn-platform`, `hyprn-mvp`,
  total count 2), token freshness under 60 minutes, `codd` home private and
  unreachable from `ada`, no Slack tokens.
- Managed OpenCode config root-owned, restricted to the `opencode`
  provider, denying push-to-main variants and merge while asking for
  `gh api`; reviewed copy matches the host copy.
- No Slack app (`slack_agents` in `infra/agents/variables.tf`) and no Slack
  secret on host.

Stale single-repository App-scope assertion in `tests/agents/host-checks.sh`
fixed to the both-repository form (exact two-repo diff + count 2).
`tests/agents/README.md` summary line already described the both-repo scope —
no edit needed.

Verify: `CODD_CHECKS_OK` (both scripts bash -n clean, host-checks names
`hyprn-mvp`).

### Task 3 (partial) — stale scope-line corrections (done, automated part)

Corrected the four remaining platform-only Codd scope lines to both
repositories (D-03, CODD-01 groundwork):

- `README.md` — Codd setup paragraph → installed on `hyprn-platform` and
  `hyprn-mvp`.
- `.planning/PROJECT.md` — Codd setup sentence → same.
- `runbooks/agents/github.md` — install step 3 and Repository-access section
  → same.

Already correct, verified untouched: REQUIREMENTS.md CODD-01 row, spec §2
GitHub row, spec Codd-pattern row, `tests/agents/README.md`. A sweep for
remaining `platform.*only` lines returns only two legitimate non-Codd lines
(OPS-03 Boole scope, Slack-allowlist "platform owner only"); no stale Codd
line remains. ADR-0003 exists (`docs/adr/0003-own-slack-channel-server.md`,
DOC-01 evidence).

## Deviations from Plan

None — plan executed as written. The local `runbooks/agents/checks-2026-10-13.md`
FAIL rows appended by a trial `run.sh` execution off-host were reverted, not
committed: off-host failures are environmental (no agent users, no host
paths), not host results, and must not pollute the dated host record.

## Blocked checkpoints (live owner-hand tests — never automated)

### Blocker 1 — Live session proofs (ACC-01/02/03, roadmap criterion 3)

`tests/agents/checks/session.sh` fails every live check until the owner
drives the session tests. Owner steps per `runbooks/agents/live/README.md` —
for each test, perform the drive steps, observe, and write
`runbooks/agents/live/<test-id>.ok`:

```text
2026-10-13
owner: <owner-principal>
```

Tests: `relay-owner-yes`, `relay-owner-no`, `relay-non-owner-rejected`,
`allowlist-silence`, and per repository (`platform`/`mvp` short names)
`refuse-<repo>-merge`, `refuse-<repo>-push-main`, `refuse-<repo>-force-push`,
`refuse-<repo>-bypass` — all in Ada's session and as Codd, exercising the
command-text variants. Then, as root on the agent host:

```bash
tests/agents/checks/session.sh
```

All 13 checks must pass; the dated `run.sh` record captures each outcome.

### Blocker 2 — Final green host run + owner sign-off (ACC-08, criteria 6/7)

As root on the agent host, after Blocker 1 markers exist:

```bash
tests/agents/run.sh
```

Confirm every domain passes including the new session and codd scripts, keep
the dated record under `runbooks/agents/`, and sign that roadmap criteria 3
(relay plus refusals), 6 (run.sh green with record), and 7 (Codd covered by
the same run) hold. Local trial runs of `host-checks.sh`/`run.sh` off-host
fail on missing agent users and host paths — expected, environmental only.

## Verification after commit

- `bash -n` clean: `session.sh`, `codd.sh`, `host-checks.sh`.
- `SESSION_CHECKS_OK`, `CODD_CHECKS_OK`, `FINAL_SWEEP_OK` (ADR-0003 present).
- `tests/agents/host-checks.sh` off-host: fails on host-only prerequisites
  (no `ada`/`codd` users, no `/run/hyprn-agents`, no metadata) — environmental.
- `tests/agents/run.sh` off-host: same environmental failures; record-file
  side effect reverted.

## Files

- Created: `tests/agents/checks/session.sh`, `tests/agents/checks/codd.sh`,
  `runbooks/agents/live/README.md`,
  `.planning/phases/01-security-baseline/01-05-SUMMARY.md`.
- Modified: `tests/agents/host-checks.sh` (both-repo scope assertion),
  `README.md`, `.planning/PROJECT.md`, `runbooks/agents/github.md`
  (stale scope corrections).

## Self-Check: PASSED

All created/modified files exist; commit recorded below; no secret values
printed or committed (markers name the owner principal only, never tokens).
