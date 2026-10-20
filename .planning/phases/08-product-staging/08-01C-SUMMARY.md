---
phase: 08-product-staging
plan: "01C"
subsystem: deployment-contract
tags: [claude-managed-agents, shared-budget, secret-files]
requires:
  - phase: 08-01B
    provides: Separate dispatcher and bounded credential consumers
provides:
  - Release-bound managed Assistant resources and explicit approval to USD conversion
  - Mandatory retained shared-spending policy and application-only settings
affects: [product-06-05, host-startup, release-builder]
tech-stack:
  added: []
  patterns: [closed descriptors, exact decimal conversion, explicit startup prerequisites]
key-files:
  created: [08-01C-PLAN.md, 08-01C-CHECKPOINT.md, 08-01C-SUMMARY.md]
  modified: [host/contract.py, contracts/v1/deployment.schema.json, contracts/v1/fixtures.json, contracts/v1/README.md, tests/platform/test_contract.py]
key-decisions:
  - Preserve explicit EUR or USD approval and reviewed conversion, rounded down to provider cents.
  - Carry prior spending and retained session history across restarts; startup must reconcile continuity.
  - Export configuration hash but identify the remaining release/startup consumer explicitly.
requirements-completed: [PST-01]
commits: 5
plan_head_before: a9fcbafbd0c0926d6161b6206fd8bd4b2b4a8427
plan_head_after: 1f9a7fae0ef797509614e8bfbf84c9edec265fe0
duration: 20min
completed: 2026-10-20
status: complete
---

# Phase 08 Plan 01C: Managed Assistant runtime binding Summary

Closed deployment descriptors bind reviewed Claude resources and release hashes to
application Settings, preserving explicit approval currency, USD conversion and
one carried shared allowance.

## Task commits

- `2d8f042`: failing public-CLI Assistant environment test and task plan.
- `9c5deee`: schema, renderer, synthetic pins, negative CLI tests and contract docs.
- `1f9a7fa`: parent review adjustment to generic runtime approvals and USD unit-rate validation.

The measured ledger range contains five commits, including concurrent parent
commits `89429d2` and `74b1623`. This task owns the three commits listed above.
The range was measured before this task's metadata commit. Global planning
state and integrated acceptance remain parent-owned by explicit assignment.

## Verification and TDD gate compliance

RED: 15 passed, 1 intended assertion failure; classifier RED_EVIDENCE_OK. The
target executed and failed because the app lacked its real credential setting.
GREEN: 19 passed; after currency clarification, 20 passed. Required committed-tree
check at `9c5deee`: 20 passed. After parent review changes, required committed-tree
check at `1f9a7fa`: `tests/platform/run.sh contracts`, exit 0, 20 passed, 0 failed.
No refactor commit was necessary. Diff check passed; scoped test stores released.
Full compact evidence, hashes and tooling failures are in [the checkpoint](08-01C-CHECKPOINT.md).

## Decisions and deviations

The parent clarified that approval currency must not silently become USD;
mandatory exact decimal conversion and approval metadata implement that direction.
Review removed deployment-specific approval constants from the schema: amount
and supported currency belong to reviewed runtime bindings, and actual authority
remains in the private operational review. The fixture is synthetic only.
No architectural deviation or new dependency was required. Only owned paths were
staged. Infrastructure changes in the measured range belong to the parent.

## Remaining obligations

PST-01 metadata here records this contract task's contribution, not completion of
the entire staging requirement. No cloud boot, live provider setup, egress,
historical spending continuity or human acceptance is claimed. Required startup
consumers still enforce provider readback, configuration hash, reviewed conversion,
durable session/prior-spend reconciliation and private credential-file ownership.
The stateless preview cannot decide if historical zero spending is truthful.
No known implementation stubs or skipped verification were introduced.

## Self-Check: PASSED

Plan, checkpoint and summary exist. All three task commits are ancestors of HEAD.
Final diff check passed. Global planning reconciliation is explicitly parent-owned.
