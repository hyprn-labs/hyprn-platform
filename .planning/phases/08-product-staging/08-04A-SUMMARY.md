---
phase: 08-product-staging
plan: "04A"
status: complete
subsystem: infrastructure
tags: [terraform, gcp, postgresql, staging]
requires: [08-01]
provides: [offline-private-staging-foundation]
affects: [08-02, 08-03, 08-04, 08-05, 08-06]
tech-stack:
  added: []
  patterns: [private-origin, shared-ca-dns-verification, stopped-host-before-qualification]
key-files:
  created:
    - infra/environments/staging/main.tf
    - infra/modules/environment/main.tf
    - infra/modules/host/main.tf
    - environments/staging/access.json
    - tests/platform/test_infrastructure.py
    - runbooks/product-staging.md
  modified: []
key-decisions:
  - Reuse the installed pinned Terraform and Google provider without acquisition.
  - Keep the VM stopped until host firewall and lifecycle qualification are implemented.
  - SQL passwords, roles and secret versions are provisioned outside Terraform.
completed: 2026-10-20
commits: 1
plan_head_before: 79b8e17ed12f73ceb4a12552e6d5ef047bafbd54
plan_head_after: 2c35587061f6ff8216996be6817186f3fef2484f
---

# Phase 08 Plan 04A: Offline private staging foundation

Terraform now defines a private stopped staging host, PostgreSQL with a shared-CA
PSA DNS identity, private storage and narrowly scoped runtime access.

## Delivery

Code commit: `2c35587061f6ff8216996be6817186f3fef2484f`.
The root creates only the reviewed staging class. No secret values, SQL passwords,
secret versions or managed SQL users are present in Terraform. The Access document
is an explicitly incomplete review template with required owner/environment inputs;
it has no external MCP/ChatGPT/OAuth paths.

## Verification

- `HYPRN_TF_PROVIDER_DIR=<existing bootstrap provider cache> tests/platform/run.sh infrastructure`:
  2 passed, 0 failed; the provider test evaluates 7 Terraform mock-provider plans.
- The test executes actual `terraform init -backend=false -lockfile=readonly`,
  `terraform validate -json` and `terraform test -json` against copied modules.
  Validate: 0 errors, 0 warnings. No live provider operations.
- `terraform fmt -check -recursive infra/modules infra/environments/staging`: pass.
- `git diff --cached --check`: pass before commit.
- Dedicated GCP project-list read: exit 0, no matching staging project returned.
- Parent integration verification on the committed tree remains the orchestrator's
  responsibility; no human acceptance or live cloud enforcement is claimed.

## Deviations from Plan

The orchestrator approved extracting 08-04A from 08-04 so offline implementation
can proceed before host lifecycle and publisher completion. The full 08-04
milestone is not complete. Effective host isolation, observability, exact live
plan/cost approval and activation are retained dependencies, not simulated features.

Official Cloud SQL documentation identifies PSA hostnames as sql-psa.goog.
Reported the mismatch to the contract owner, who separately amended and tested
the public platform deployment schema before this commit. No shared contract
files were edited by this task.

An initial sandboxed provider-schema process could not open its local plugin
socket. Repeating validation with approved local execution succeeded; no code
fix or credential retry was involved. Initial code-authoring orchestration had one
JavaScript syntax error before any writes; corrected invocation wrote the files.

## Remaining inputs and work

See the precise input and authority tables in `runbooks/product-staging.md`.
The live resource plan, state backend, confirmed regional pricing, role groups,
exact image and destination ranges, Cloudflare IDs/allowlist, secret numeric
versions, disk/store IDs and CA bundle remain unverified or unresolved.

08-02 supplies the host services, metadata/container firewall, quotas and actual
attestation. 08-03 supplies publisher identities/protections. 08-04/05 supplies
operational alert receivers and live plan approval. 08-05/06 supplies live
connectivity, two-user authorization, execution and coherent restore evidence.
Shared STATE/ROADMAP updates are delegated to the orchestrator to preserve its
active edits and fleet planning state.

## Known Stubs

No product implementation stub. `environments/staging/access.json` is intentionally
a non-executable parameterized review template; it cannot be treated as a resolved
Cloudflare request or applied configuration. Its completion belongs to 08-04/05.

## Threat Flags

| Flag | File | Description |
|---|---|---|
| threat_flag: cloud-authority | infra/modules/environment/main.tf | Creates network, SQL, storage and secret-reader IAM only upon later separately approved apply |
| threat_flag: admin-access | infra/modules/host/main.tf | Grants scoped IAP/OS Login and host act-as to supplied operator group upon apply |
| threat_flag: external-auth | environments/staging/access.json | Access policy input template; actual issuer/audience and revocation still require live verification |

## Self-Check: PASSED

All 15 committed paths exist; code commit is an ancestor of HEAD. No tracked-file
deletions occurred. Test temporary scopes were released, and the separate initial
offline Terraform cache scope was removed. Unrelated changes remain untouched.
