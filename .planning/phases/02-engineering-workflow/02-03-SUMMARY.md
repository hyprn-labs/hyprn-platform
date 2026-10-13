# 02-03 herdr runtime + cockpit — Summary

**Status:** done-with-blockers (1: blocking-human owner-go checkpoint, see Blocked)
**Date:** 2026-10-13

## What was built

- `agents/host/provision.sh`: `HERDR_VERSION="0.9.4"` +
  `HERDR_SHA256="49330…b23"` (x86_64) + `HERDR_SHA256_AARCH64="9511c…bfd"`
  resolved live from `https://herdr.dev/latest.json` (checksum verified against
  the downloaded 0.9.4 binary before writing); `install_herdr()` mirroring
  `install_opencode()` (arch select, `sha256sum -c`, root-owned
  `/usr/local/lib/herdr/herdr`, idempotent version guard); `herdr-session` +
  `herdr@.service` installed; `add_agent()` enables `herdr@<name>` and disables
  `hyprn-agent@<name>` (tmux stays installed as present-but-disabled fallback).
- `agents/host/files/herdr-session` (new): mirrors the old session structure
  (strict mode, profile sourcing, restart loop + 10 s backoff) with a headless
  `herdr server` start; `unset HERDR_ENV` locks agent-to-agent prompting off
  (herdr's own skill gate requires `HERDR_ENV=1`); idle-stop heartbeat touch.
- `agents/host/files/herdr@.service` (new): `Type=simple`, `User=%i`,
  `Restart=on-failure`, same egress/secrets/user ordering as the old unit,
  `ExecStop=herdr server stop`.
- `agents/policy/managed-settings.json`: allowlisted the herdr pane-lifecycle
  report commands (`report-agent*`, `report-agent-session*`,
  `release-agent*`, `status*`) and ADDED `Bash(herdr agent prompt*)` to deny
  (defense in depth for the locked prompting posture). All prior allow entries
  intact (a dropped `git show` line was caught and restored); both
  `gh pr merge` denies intact; valid JSON.
- `tests/agents/checks/herdr.sh` (new, in `run.sh`): pin/SHA/checksum-guard
  greps, unit-shape greps, prompting-off greps (launcher + policy),
  hooks-in-policy grep, fallback-shipped grep, runbook-checklist grep;
  host-only live unit/pin/fallback checks SKIP elsewhere; regression tail runs
  sibling checks (not `run.sh` itself — that would recurse), host-only.
- `runbooks/agents/engineering-workflow.md` (new): helper use + env contract,
  shared Ada/Codd PR body contract, COK-01 owner checklist (laptop pin
  `0.9.4`, one config dir per seat, Remote Control owner-seat-only,
  `herdr machine add` over IAP SSH, `machine status` reachable proof),
  apply authority rule, dated-record table.

## Verify results

- `bash -n` clean (provision, herdr-session, herdr.sh); policy valid JSON;
  `grep -c "gh pr merge"` policy = exactly 2; `herdr.sh`: 14 PASS + 5 SKIP,
  exit 0; runbook contains `herdr machine add`, `Remote Control`, `| Date |`.
- `run.sh`: `checks/herdr` SCRIPT-PASS.

## Deviations

- **No `ARGS_FILE` in herdr-session** (plan suggested structural parity):
  `herdr server` takes no harness arguments — passing Claude channel flags to
  it would be a bug. The `.args` file remains the harness-pane concern;
  agent panes resume automatically (`resume_agents_on_restore`); one-time pane
  creation is an owner step in the runbook. Deliberate correctness call.
- **Regression tail runs siblings, not `run.sh`**: calling `run.sh` from a
  check `run.sh` executes would recurse. Same Slack/wake/checks coverage, no
  recursion. Host-only so pre-existing off-host failures can't misreport.
- Real herdr 0.9.4 CLI (inspected, not assumed): `herdr server` headless,
  `herdr server stop` via socket, `herdr agent prompt` confirmed as the
  cross-agent surface being locked.

## Blocked

1. **Owner-go checkpoint (gate: blocking-human): laptop cockpit install + host
   herdr apply + reboot proof** — commands: runbook COK-01 checklist in order;
   `agents/host/apply.sh` for exactly the reviewed diff; post-apply
   `tests/agents/run.sh` on the host; `herdr machine status
   hyprn-agents-host-01` reachable from the laptop; reboot-resume confirmation
   — who: platform owner at the laptop with IAP SSH working — go needed:
   explicit apply approval per reviewed plan + Phase 1 green run
   (`/gsd-verify-work 1`) for the live COK-02 proof. Evidence: dated runbook
   row (HERDR_VERSION + `reachable` + pass count) and `live/herdr-reboot.ok`
   (`YYYY-MM-DD` first line, `owner: ` second). Executor must NOT create the
   marker without owner evidence.
