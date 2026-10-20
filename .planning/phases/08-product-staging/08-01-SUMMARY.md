---
phase: 08-product-staging
plan: "01"
subsystem: deployment
tags: [contracts, staging, secrets, containment]
requires: []
provides:
  - Closed staging release and runtime schemas with deterministic preview CLI
  - Fixed secret consumers, artifact pins and safe native bundle inspection
affects: [08-02, 08-03, 08-04, product-06-05]
tech-stack:
  added: []
  patterns: [stdlib JSON validation, digest-pinned releases, immutable policy rendering]
key-files:
  created:
    - contracts/v1/deployment.schema.json
    - contracts/v1/fixtures.json
    - host/contract.py
    - tests/platform/run.sh
    - tests/platform/test_contract.py
  modified:
    - contracts/v1/README.md
    - .gitignore
key-decisions:
  - Embedded Assistant provider secret is application-only; no external MCP/OAuth functionality.
  - Authentication lookup, request, migration and backup database credentials remain separate.
  - Database TLS server identity and CA bytes must be explicit and verified.
requirements-completed: [PST-01]
actuals:
  tokens: 21717
  tasks: 1
  commits: 3
plan_head_before: 8ffbdf92c28eb607f753fed4e603a10cc44865e6
plan_head_after: 408ed98b61ffe57de565e0a79a5493a66ddff05c
duration: 15min
completed: 2026-10-20
status: complete
---

# Phase 08 Plan 01: Deployment contract summary

**A pinned release and staging binding now produce a deterministic runtime
preview with fixed secret, mount, network and privilege boundaries.**

## Delivered

- Four closed JSON Schema definitions and synthetic fixtures.
- Public stdlib CLI validates duplicate-free JSON, full pins, store versions,
  staging identity, desired inventories and effective render policy.
- Optional native tar verification rejects traversal, links, special files,
  duplicates, parent/file collisions, excessive expansion and digest mismatch.
  It never extracts files.
- Existing app/modeling UIDs and image entrypoints are retained. Application
  receives request and read-only authentication DB credentials plus modeling and Assistant secrets.
  Migration/backup secrets are separate; workers are networkless and secret-free.
- Read-only database CA mount and explicit verified server identity.
- Git ignore guards for local Terraform inputs/plans, keys and local stores.
  Tracked bootstrap configuration is preserved.

## Verification

- RED: one intentional assertion failure in the valid CLI-preview test:
  CLI returned `not_implemented` instead of success. Machine classification
  `RED_EVIDENCE_OK`; exact output and semantic assessment in `08-01-RED.json`.
- GREEN: `tests/platform/run.sh contracts` — 11 tests passed, 0 failed,
  on committed `408ed98`, 1.860 seconds.
- Focused tests cover 12 negative fixture mutations, additional malformed
  numbers/identities/TLS inputs, desired agreement and unsafe tar scenarios.
- `git check-ignore` confirms local secret/state examples excluded and
  `.env.example` remains available for safe templates.
- No tracked-file deletions. Temporary test scopes clean themselves up.
- No package installs, cloud calls, account/settings changes or live data use.

## Commits

- `3b28d6e`: test(08-01): specify closed staging deployment contract
- `2c3c947`: feat(08-01): validate and preview fixed staging deployments
- `408ed98`: fix(08-01): separate database authentication credentials

## Deviations and remaining integration

- Owner-authorized ADR-0014 supersedes external MCP/ChatGPT/Managed OAuth scope;
  Assistant provider-secret support replaces it.
- Added schema/renderer byte pins, documentation and ignore hygiene to make
  the public handoff reviewable and protect deployment inputs.
- Parent review identified the need for explicit Cloud SQL certificate identity
  and CA pins. Added them without any insecure fallback.
- Product integration added `hyprn_auth` for narrow credential lookup; provided
  its own app-only secret alias instead of overloading request credentials.
- The existing global STATE pointer concerns the independent fleet workstream.
  Per parent instruction it was not advanced or committed. Parent integrates the
  scoped product-staging progress; pre-existing dirty planning/spec files remain.
- Metadata commit's term hook rejected personal paths in the raw RED report.
  The unchanged report remains ignored local evidence; portable checkpoint
  commands use the resolved tooling variable. The hook remains enabled.
- The preview is not a bootable cloud edition. Product lifecycle/cloud adapters
  must consume these fields; the host must supply ingress, enforce egress and
  metadata denial, verify disk identity and acquire writer fencing. Preview flags
  explicitly distinguish structural validation from artifact-byte verification.
- Host attestation validity, evidence authenticity, image execution, live DB role
  denials and automatic deployment are subsequent tasks. No hosted acceptance
  is claimed by this contract test.

## Threat surface

All new surfaces are the planned local descriptor/archive validation boundaries.
No new endpoint, credential reader, arbitrary command or cloud authority exists.

## Self-Check: PASSED

All seven implementation paths exist. All three task commits are ancestors of the
delivery commit. Contract suite passed on that commit. Exact hashes and handoff
commands are recorded in `08-01-CHECKPOINT.md`.

## Integration follow-up: private-services DNS

`edc022f` corrects the allowed Cloud SQL DNS identity formats using current official
documentation: private services access uses `sql-psa.goog`, while PSC/public-IP
uses `sql.goog`. Both require the actual instance/project/region SAN name; exact
TLS verification and CA pinning remain mandatory. The committed-tree contract
suite now passes 12 tests. Current consumer hashes are in the checkpoint; the
original task metrics above remain the original delivery record.
