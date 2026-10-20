---
phase: 08-product-staging
plan: "04A"
type: execute
autonomous: true
depends_on: ["08-01"]
files_modified:
  - infra/modules/environment/
  - infra/modules/host/
  - infra/environments/staging/
  - environments/staging/access.json
  - tests/platform/test_infrastructure.py
  - runbooks/product-staging.md
---
# Offline private staging foundation

Approved scope amendment: deliver the independent Terraform foundation before
08-02/03 integration. Product ADR-0014 supersedes external MCP/ChatGPT requirements
and authorizes a fresh application database. No source data transfer is required.

## Task
Implement private network/NAT, private PostgreSQL with DNS-verified shared CA,
durable storage, secret metadata and scoped IAM, plus a stopped private VM.
Use existing reviewed Terraform/provider binaries only. Validate the real modules
with provider-schema validation and evaluated mock-provider plans, including
negative configuration cases. Preserve unrelated repository edits.

## Acceptance
`tests/platform/run.sh infrastructure` passes with the reviewed provider cache.
No cloud apply, IAM setting change, secret value, running workload or live plan is
claimed. Record missing runtime inputs and the work retained in 08-04.

## Retained dependencies
08-02 owns host bootstrap, effective container firewall, metadata isolation,
quota enforcement and lifecycle integration. 08-03 owns deployment identities and
GitHub protection gating. 08-04 completion still requires a concrete owner-reviewed
live Terraform plan, price/permission review and configured observability.
08-05/06 prove effective cloud policies and the full staging journey.
