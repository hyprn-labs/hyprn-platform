# 01-04 Summary: misuse detection + account safeguards (reviewed TF + checks + owner checklists)

**Status:** done-with-blockers (1 owner checkpoint covering 6 hand steps)
**Date:** 2026-10-13

## Tasks done

1. **Author detection Terraform and the detect check script** — created
   `infra/agents/detect.tf` (DATA_READ audit config for Secret Manager,
   admins-group email channel, unexpected-access alert with host/wake
   exclusions, IAM-change alert over the agents project, folder sink into
   the agents project; no secret values) and `tests/agents/checks/detect.sh`
   (7 static content assertions + 5 live gcloud assertions: audit config,
   both policies enabled with channel, sink, deliverability). Apply NOT run.
2. **Add host-cleanliness, wake-limit, and IAM-search checks** — created
   `tests/agents/checks/accounts.sh` (11 checks: no user creds/keys/
   staging-prod, wake get/start/stop-only + instance-scoped grant, idle-stop
   poweroff disk persistence, 3 owner-credential procedures with expected
   outputs). Header records the confirmed wake finding: service on
   `hyprn-agents-wake-01` as `hyprn-agents-wake`, custom role
   `agentHostPower` (infra/agents/wake.tf).
3. **Checkpoint: owner applies detection, confirms safeguards, live-tests
   alerts** — extended `runbooks/agents/gcp.md` with six owner-go checklist
   sections (detect.tf apply, break-glass, 2FA with member-notice decision
   gate, both canary alert tests, org-wide IAM search) plus a sign-off
   table with pending rows. **Not automatable — owner go required.**

## Verify results

- `bash -n` clean on both scripts; `ACCOUNTS_CHECKS_OK` (11 named checks).
- `detect.sh` standalone: **7/7 static PASS**, 5 live FAIL (no owner
  credentials in this worktree — expected, see Blocked).
- `accounts.sh` standalone: **8 static PASS**, 3 owner-credential FAILs
  (expected), 1 false-positive FAIL (see Deviations).
- `SAFEGUARDS_RECORD_OK` (runbook has dated sign-off rows + content).
- `terraform fmt -check`: **could not run** — terraform is not installed
  here and must not be (see Blocked). Formatting follows the repo `fmt`
  style manually (2-space indent, aligned `=`).
- `tests/agents/host-checks.sh` re-run after commit: fails
  environmentally (needs root), as before.

## Deviations

- **`agents_folder_id` declared inside `detect.tf`:** the folder is owned
  by `bootstrap/` and `infra/agents/` has no folder reference, so the sink
  needs the folder ID from somewhere. Added the variable in `detect.tf`
  itself (rather than touching `variables.tf`, outside this plan's file
  list); value comes from bootstrap output `agents_folder` at apply time.
- **Controller/gateway exclusions deferred:** those identities do not exist
  yet (Phases 3-5). The secret-alert filter excludes host + wake and the
  file comments that controller/gateway exclusions land with those
  identities — never as silent widenings.
- **False-positive FAIL, `accounts.sh` "no private-key files":** the match
  is `.planning/codebase/TESTING.md` *quoting the scan pattern itself*
  (lines 86, 158) inside this checkout under `/home/codd`. The identical
  pre-existing `host-checks.sh` check false-positives the same way
  wherever that doc is checked out. Left strict (consistent idiom);
  follow-up for the owner at the host run: adjudicate, and optionally
  narrow the scan (e.g. JSON-shape match) under its own reviewed change.
- **Fixed during work:** unbound `$ORG` under `set -u` in the org-search
  check (escaped to eval-time expansion).

## Blocked

1. **Owner checkpoint (gate blocking-human): apply detection, confirm
   safeguards, live-test both alerts, run the IAM search.** Order: review
   the exact `detect.tf` revision → `terraform plan/apply` (reviewed plan
   only) → break-glass confirmation → member notice THEN 2FA toggle
   (one-way decision gate) → canary secret read + mail arrival → canary
   IAM change + mail arrival → org-wide IAM search matching declared
   roles → sign all six rows in `runbooks/agents/gcp.md`. Who: owner with
   console + owner credentials. This worktree cannot perform any of it:
   no terraform, no gcloud identity, and per D-08/AGENTS.md these steps
   must never be automated. Cloud apply is reversible (plan-reviewed).
