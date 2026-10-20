# Staging state bootstrap

This Terraform root owns one dedicated staging state bucket in the existing
`hyprn-bootstrap` project. The bucket uses Standard storage, uniform bucket-level
access, enforced public-access prevention and object versioning. Terraform
prevents replacement and destruction; nonempty deletion is disabled.

The backend is GCS. The root was initialized from a reviewed private local
state and then migrated with its recovery copy retained. Its remote destination is
`gs://hyprn-bootstrap-tfstate/staging-state-bootstrap/`. The resulting bucket
holds the separate staging environment and Access Terraform states.

[Bootstrap plan and execution record](../../../.planning/phases/08-product-staging/08-04C-CHECKPOINT.md).
