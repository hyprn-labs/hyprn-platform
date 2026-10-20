---
phase: 08-product-staging
plan: "01B"
status: complete
subsystem: deployment-contract
tags: [dispatcher, least-privilege, preview]
requires: [08-01]
provides: [scoped background roles, isolated dispatcher template]
affects: [product-06-05, host-lifecycle]
tech-stack:
  added: []
  patterns: [fixed stdio bridge, closed credential consumers]
key-files:
  created: [.planning/phases/08-product-staging/08-01B-PLAN.md, .planning/phases/08-product-staging/08-01B-CHECKPOINT.md]
  modified: [host/contract.py, contracts/v1/deployment.schema.json, contracts/v1/fixtures.json, contracts/v1/README.md, tests/platform/test_contract.py]
key-decisions:
  - Host owns run/attach and dispatcher lifetime; no inert keeper.
  - Dispatcher receives request/discovery/modeling credentials only.
  - Private SQL route and egress enforcement remain explicit unproved startup prerequisites.
duration: 18min
completed: 2026-10-20
commits: 4
plan_head_before: 520e1890519f0546d8090671a4e5af135826a083
plan_head_after: 48963080e9e4249dc4ade52ab5e9615ff4175234
---

# Phase 08 Plan 01B: Dispatcher contract Summary

A separate app-image dispatcher template scopes discovery credentials, artifact
access and stdio ownership while preserving credential-free native execution.

## Task and verification

One task complete. RED commit `dde3e04`; GREEN commit `4896308`.
The persisted ledger measures four commits because two independently owned
08-04B commits landed concurrently; only two belong to this task.

[Checkpoint](08-01B-CHECKPOINT.md) records exact commands, counts, hashes and
consumer interfaces. Committed-tree contract verification passed all 15 tests.

## TDD Gate Compliance

RED executed the target assertion for missing dispatcher, with 12 other tests
passing. Classifier returned RED_EVIDENCE_OK. Semantic review confirmed the
intended missing behavior, not a fixture/import fault. GREEN implemented the
fixed template and explicit roles. Refactor was unnecessary.

## Deviations from Plan

None. Parent approved host-owned run/attach and explicitly retains global state
integration; existing unrelated state edits were preserved. This amendment
completes declarative preview only, not pending lifecycle/boot qualification.

## Remaining obligations

Product 06-05 owns actual cloud entrypoints and host bridge launch adaptation.
Host acceptance must prove private SQL routing, restricted egress, mounted
credentials and bounded database grants. Automated preview is not live or
human acceptance. No implementation stubs were introduced into this scope.

## Self-Check: PASSED

Plan/checkpoint and all implementation artifacts exist. Both task commits are
ancestors of HEAD. Required committed-tree tests passed; exact pins verified.
