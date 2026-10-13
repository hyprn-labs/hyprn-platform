# 01-01 Summary: tracer — ruleset definition plus one-command check run

**Status:** done-with-blockers (2 host-side verifications need root on the agent host)
**Date:** 2026-10-13

## Tasks done

1. **Tracer: ruleset definition plus one-command check run with dated record** — created
   `agents/github/main-ruleset.json` (main-protection, branch target
   `refs/heads/main`, enforcement active, non-fast-forward + deletion +
   linear-history + pull-request rules with 1 approval, stale dismissal,
   code-owner review, last-push approval, empty bypass list),
   repo-root `CODEOWNERS` (`* @hyprn-labs/owners`, review-only per D-01),
   `tests/agents/checks/github.sh` (16 static checks + per-agent live
   installation assertions for both repositories per D-03/D-04), and
   `tests/agents/run.sh` (runs `host-checks.sh` unchanged first, then every
   executable `checks/*.sh` with per-script failure capture, appends a dated
   record with ISO date, checkout hash, per-script outcomes, overall result).
2. **Schema-validate the ruleset definition** — `checks/github.sh` carries
   jq structural assertions (name, enforcement, main ref, all four rule
   types, PR parameters); no ruleset write/apply call exists in any file
   (asserted by a checked-in negative grep).
3. **Prove the orchestrator aggregates failures and records the run** —
   proven with a scratch failing stub: the run continued past it, reported
   per-script PASS/FAIL lines, exited non-zero, and still wrote the record;
   scratch stub and scratch record removed afterwards.

## Verify results

- `python3 -m json.tool agents/github/main-ruleset.json` + `bash -n` on both
  scripts: **TRACER_STATIC_OK**
- `jq enforcement == active` + `rules | length >= 4`: **SCHEMA_OK**
- Orchestrator references the checks directory: **ORCHESTRATOR_OK**
- `checks/github.sh` standalone in this worktree: **16/16 static PASS**;
  4 live App-installation checks FAIL environmentally (see Blocked 1).
- `tests/agents/host-checks.sh` in this worktree: fails environmentally
  (needs root on the agent host: nft, systemctl, runuser, tmpfs secrets).
- Scratch aggregation run: all domains executed despite failures, exit 1,
  dated record written — then cleaned; final clean run left
  `runbooks/agents/checks-2026-10-13.md` as the first dated record.

## Deviations

- **CODEOWNERS team `@hyprn-labs/owners`:** no human team name exists in the
  repo (org's only member is the owner). Used the conventional owners-team
  name with a header comment stating the team must exist at Team-plan apply
  time. Owner to confirm/rename at apply.
- **Live-installation checks stay strict (no SKIP fallback):** consistent
  with the `host-checks.sh` idiom; they fail off-host and pass as root on
  the host. Documented as Blocked 1 rather than weakened.
- **Fixed during work:** `REPO_ROOT` in `checks/github.sh` needed
  `../../..` (script sits one level deeper than `host-checks.sh`);
  self-matching grep pattern in the no-apply check split via string
  concatenation.

## Blocked

1. **Live App-installation assertions need root on the agent host.**
   Command: `sudo tests/agents/checks/github.sh` (or full
   `sudo tests/agents/run.sh`). Who: owner/host hands (needs root for
   `runuser` into `ada`/`codd` plus App-token `gh`). Go needed: owner go
   per AGENTS.md authority for the exact host step. This worktree cannot
   run it: `runuser` absent, `/run/hyprn-agents/secrets/` not readable.
2. **Ruleset apply deferred to the Team-plan purchase (D-01).** Command
   (recorded, NOT run): `GH_CONFIG_DIR=... gh api
   repos/hyprn-labs/hyprn-platform/rulesets --input
   agents/github/main-ruleset.json`, plus the same for `hyprn-mvp`.
   Who: owner with org-admin credentials after the Team-plan purchase.
   Go needed: explicit per-step owner go; removals/changes get their own go.
