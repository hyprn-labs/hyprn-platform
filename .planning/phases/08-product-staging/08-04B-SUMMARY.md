---
phase: 08-product-staging
plan: "04B"
status: complete
subsystem: infrastructure
tags: [cloudflare, terraform, access]
requires: [08-04A]
provides: [declarative-staging-access-boundary, offline-evaluated-access-policy]
affects: [08-05, 08-06]
tech-stack:
  added: [cloudflare/cloudflare@5.28.0]
  patterns: [remote-tunnel-metadata-without-credentials, dns-after-access]
key-files:
  created:
    - infra/modules/access/main.tf
    - infra/environments/staging-access/main.tf
    - infra/environments/staging-access/.terraform.lock.hcl
    - tests/platform/test_access_infrastructure.py
    - docs/dependencies/cloudflare-provider.md
  modified: [tests/platform/run.sh]
key-decisions:
  - Remote tunnel credentials are retrieved outside Terraform into Secret Manager.
  - The complete hostname uses one email PIN provider and one exact-email allow policy.
  - Offline tests replace only the backend with isolated local persistence.
duration: 20min
completed: 2026-10-20
actuals:
  tokens: 7232
  tasks: 1
  commits: 3
plan_head_before: 79198a56b77a0a3fd6b7fc8cdd8709de60a1d0f1
plan_head_after: c9baa7c64cc23642d60092eb70d42952dd0ef307
---

# Phase 08 Plan 04B: Declarative staging Access Summary

Six pinned Cloudflare resources enforce named-email admission, connector JWT
validation, loopback routing, final 404 and DNS publication after Access.

The scoped offline task is complete. This does not complete Phase 08 or establish
live Access. Provider schema, 12 evaluated plans, dependency graph, and a detected
bypass regression passed at c9baa7c. Exact commands, failures, hashes, scratch
cleanup and runtime inputs are in [08-04B-CHECKPOINT.md](08-04B-CHECKPOINT.md).

## Task commits
- 520e189 — tests first, dependency provenance, runner registration and plan.
- c9baa7c — implementation and passing evaluated acceptance.
The measured shared-branch ledger count of 3 includes another executor's
dde3e04 commit; it is not claimed as this task's work. Two commits belong to this
task before this metadata commit.

## Decisions and limitations
Cloudflare 5.28.0 is Apache-2.0 and its remote tunnel model supports omitted
tunnel_secret without a computed token. The resource model audit, schema and
plan confirm the selected configuration carries metadata only. Token retrieval
remains a future explicit operation outside Terraform. Host-side application JWT
verification remains mandatory independently of the connector.

No cloud/settings mutation, live-token read or live plan occurred. Actual
account/zone/team, invited users, loopback port, backend and dedicated authority
remain external operational inputs. Existing resource inventory/adoption must
precede a reviewed live plan. Only the audited darwin_arm64 provider is qualified.

## Deviations from Plan
[Rule 3 - Blocking] Terraform providers schema and graph require an initialized
backend. Tests replace only the GCS backend with local persistence in temporary
copies; production configuration retains GCS. The first override syntax was fixed.
No architecture or security invariant changed.

Shared STATE/ROADMAP updates remain with the parent orchestrator under explicit
file ownership; this executor did not overwrite concurrent planning edits.

## Self-Check: PASSED
Both task commits are ancestors of the tested revision. All declared Terraform,
test, provenance, checkpoint and summary files exist. No task-file deletions,
unwired stubs or skipped offline acceptance checks remain.
