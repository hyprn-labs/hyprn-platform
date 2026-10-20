---
phase: 08-product-staging
plan: "04C"
type: execute
autonomous: true
depends_on: ["08-04A"]
files_modified:
  - infra/bootstrap/staging-state/
  - tests/platform/test_state_bootstrap.py
  - tests/platform/run.sh
---
# Dedicated staging Terraform state bootstrap

## Task
Create a separate Terraform root managing only the private, versioned staging
state bucket in the existing bootstrap project. Use an explicitly declared local backend for the initial plan/apply, with state
in a private external directory. After approved creation, migrate this root to
the existing bootstrap bucket under isolated staging-state-bootstrap prefix.
This scope amendment avoids an unapproved initial GCS state write.
No IAM, existing bootstrap/fleet state or resource edits. Use existing pinned
Terraform 1.16.5 and Google 8.6.0, with tests written before implementation.

## Acceptance
Real provider validation and evaluated mock plans verify the one-resource
boundary, private/versioned storage, explicit EU location, rejected fleet and
bootstrap bucket names, and refusal to replace the protected bucket.
Run tests/platform/run.sh state-bootstrap against the committed source.
Prepare a real saved plan only when its backend can be used without writes.
Keep private inputs/evidence outside Git with restricted permissions.

## Authorization boundary
Only read-only cloud inspection and planning are authorized. New remote state
initialization writes are also cloud mutations. If Terraform requires these,
record the prerequisite and exact proposed resource; do not substitute a local
backend or another root's state and call that an apply-ready plan.
Main staging planning waits for its backend bucket. All applies and activation
require explicit approval of exact plan, cost and scope.

## Threat model
Accidental adoption/deletion of fleet or bootstrap state: isolated backend prefix,
one managed bucket, no IAM and rejected existing bucket names. State exposure:
uniform bucket-level access, enforced public-access prevention and versioning.
Deletion/replacement: force_destroy=false and lifecycle prevent_destroy.
