---
phase: 08-product-staging
plan: 02A
subsystem: infra
tags: [secret-manager, tmpfs, credentials, attached-service-account]
requires:
  - phase: 08-01C
    provides: Closed runtime secret bindings and fixed consumer file mounts
provides:
  - Pinned per-consumer private secret delivery and safe cleanup CLI
  - Explicit operator provider-key transfer with durable single-attempt receipt
affects: [08-02, host-lifecycle, staging-admission]
tech-stack:
  added: []
  patterns: [fixed metadata identity, private directory capabilities, atomic consumer publication]
key-files:
  created: [host/secrets.py, tests/platform/test_secrets.py, runbooks/runtime-secrets.md]
  modified: [tests/platform/run.sh]
key-decisions:
  - Attached runtime identity uses metadata and fixed HTTPS endpoints without ADC or CLI fallback.
  - Uncertain provider transfer blocks retry through a durable metadata-only receipt.
requirements-completed: []
commits: 2
plan_head_before: 8647fad9a5245fa5ee22b0f2089727a96654ba68
plan_head_after: 5f317c97a8440f10887590d0cd7309494f7e40b5
duration: 11min
completed: 2026-10-20
status: complete
---

# Phase 08 Plan 02A: Secret Delivery Prerequisite Summary

**Fixed consumer secret files use pinned Secret Manager versions; approved provider
key transfer uses stdin and a receipt that prevents uncertain redispatch.**

## Accomplishments

- Closed runtime validation, expected-project checks, Linux root/tmpfs/swap gate,
  per-consumer mode/UID policy, no-follow filesystem operations, exclusive locking,
  atomic publication, bounded fetches and safe cleanup.
- Explicit attached-service-account mode validates metadata project/principal,
  authenticates fixed Secret Manager HTTPS requests and verifies resource/checksum;
  separate operator mode uses the reviewed gcloud executable and dedicated identity.
- Explicit provider transfer preflight, private key reader, stdin-only payload,
  metadata-only receipt before dispatch and no automatic retry.
- Parent registered-group acceptance at `5f317c9`: 18 passed / 0 failed, 8.096s. Exact runs,
  limitations and cleanup are in [08-02A-CHECKPOINT.md](08-02A-CHECKPOINT.md).

## Task Commits

1. Scoped secret delivery and single-attempt provider transfer — `254da66`.
2. Bootstrap provider-secret version before runtime bindings exist — `5f317c9`.

The commit count is measured from the persisted Git ledger before this metadata
commit. No requirement is marked complete by this prerequisite.

## Decisions Made

Use attached host metadata identity rather than requiring operator ADC on a VM.
Keep provider transfer separate from delivery, and require explicit reviewed
target/source authority before invoking its cloud write. Retain its receipt even
after errors so uncertainty cannot trigger a duplicate automatic write.

## Deviations from Plan

The orchestrator explicitly scoped this prerequisite from full 08-02 because its
real product lifecycle is not yet available. The parent review identified that an
operator-only identity cannot serve the VM: attached-service-account mode was
added before source commit as required runtime correctness. No new dependencies
were installed. No lifecycle, boot, live-cloud or broad phase completion is claimed.

**[Rule 1 - Bug] Bootstrap dependency cycle:** Parent review found that requiring
a complete runtime for the first key transfer depended on the secret version and
agent IDs that transfer enables. `5f317c9` validates explicit staging project
identity and approval instead. The real transfer CLI test runs with no runtime
argument and a deliberately incomplete runtime fixture.

## Remaining Acceptance

Linux tmpfs/UID enforcement, attached-SA live IAM/TLS, real container file mounts,
host metadata containment, interrupted operation recovery and SDK transfer retry
semantics remain for isolated host qualification. The local suite substitutes host
facts and cloud transport and explicitly cannot prove those boundaries. Tunnel
credentials are outside this CLI's fixed consumer map. Full 08-02 remains open.
There are no unwired placeholders or skipped tests within the scoped CLI suite.

## Threat Flags

| Flag | File | Description |
|---|---|---|
| threat_flag: authenticated-cloud-access | host/secrets.py | Trusted host metadata token acquisition and Secret Manager read; fixed destinations, identity preflight, no redirects or ADC fallback |
| threat_flag: cloud-secret-mutation | host/secrets.py | Separately approved operator version creation; private source, stdin only and durable uncertain-attempt receipt |

## Shared State Handoff

Parent owns integration rerun and shared STATE/ROADMAP/requirements reconciliation;
pre-existing concurrent edits were preserved. Record this slice as implementation
complete, retain Linux/cloud/lifecycle acceptance and full 08-02 as outstanding.

## Self-Check: PASSED

Owned source, tests and runbook exist; both source commits are ancestors of HEAD.
The persisted base ledger measures two source commits. No deletion, untracked
generated output, secret-bearing artifact or unwired implementation stub exists.
