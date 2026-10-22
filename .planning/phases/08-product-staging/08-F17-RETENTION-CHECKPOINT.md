# Operational retention audit remediation

Status: repository implementation and focused tests complete; not deployed.
No cloud resources or live files were changed. Parent deployment owns applying the
exact retention plan alongside the reviewed release.

Implementation commit: `55edfc2` (platform). Exact source and test bytes were unchanged
between focused verification and commit.

## Change

- One platform journal policy is shared by fresh setup and a narrow existing-host
  plan/apply command. Persistent target 1 GiB, volatile 128 MiB, explicit free-space
  reserves, bounded files, daily rotation and 30-day maximum age.
- Existing Docker local logs already rotate at 10 MiB times three per container.
- Plan binds exact source/configuration hashes; apply refuses different existing
  policy, checks protected paths, verifies effective override precedence, restarts
  only journald and checks active state. No product/release deletion is supported.
- Parent activation optimization commit 0317ffb remains unchanged.

## Verification

- `python3 -B -m unittest discover -s tests/platform -p 'test_retention.py' -v`:
  6 passed, 0.385s. Actual read-only CLI determinism; isolated apply/repeat,
  protected data preservation, existing-policy refusal, override/missing-limit
  refusal, single fresh/existing policy. System service calls are doubles;
  this does not prove Linux service behavior on staging.
  Log: `/private/tmp/hyprn-platform-retention-tests.log`.
- `python3 -B -m unittest discover -s tests/platform -p 'test_host_setup.py' -v`:
  39 passed, 0.241s. Log: `/private/tmp/hyprn-platform-host-setup-retention.log`.
- Temporary test directories cleaned by TemporaryDirectory; no background processes.

## Remaining ownership risk and deployment action

The release installer only owns cleanup of its failed extraction stage. There is
no complete durable rollback/recovery retention set; active identity alone cannot
prove an older release safe to delete. AiiDA owns execution work and its unfinished
process evidence. No age-based platform deletion was invented. These areas may grow;
existing bootstrap free-space admission prevents insufficient-space installation
but does not constitute garbage collection. Parent must retain this concrete risk
and obtain owner-specific terminal/recovery retention before enabling removal.

Deployment should execute the new plan/apply before updated fresh-host verification,
verify actual effective journald configuration, active journal service and disk usage,
and record the release identity. New limits prune archived journals through systemd
rotation; no immediate vacuum is invoked. Managed cloud audit retention is unchanged.

## Deployment packet refinement

Preparing the offline activation packet exposed one imported source omitted from
retention's source manifest: `reconcile.py` imports the fixed sibling `secrets.py`.
Commit `31f42b1` pins that fifth source and checks its protected path before apply.
The focused retention suite was red at 5 pass / 1 fail, then green at 6 pass
(0.375 seconds), using `python3 -B -m unittest discover -s tests/platform -p test_retention.py`.
No policy limits, setup behavior or cloud state changed.

The exact offline packet is `/private/tmp/hyprn-retention-activation/REVIEW.md`, with
`plan.json` and `target-evidence.json`. Final retention plan digest:
`46a5aba739d15588bd8beaa5844d92d85f552bede04d8992b590712acb2235ed`.
The packet verifies the retained current release, prior host plan/bundle/source
hashes and old platform snapshot, and records target identity plus integration
ordering. Parent deploys through the existing controller from the new immutable
platform snapshot; this lane performed no SSH, cloud API, secret read or apply.
