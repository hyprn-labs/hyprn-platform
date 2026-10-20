# Staging Access

This Terraform root manages the email PIN identity provider, named-email policy,
self-hosted application, remotely managed tunnel, connector ingress and proxied DNS
for staging.hyprn.ai. State is a dedicated GCS prefix with dedicated staging
authority. The sibling staging root owns the GCP host and database.

Inputs are the reviewed account and zone IDs, Access team name, exact admitted
emails and the host's loopback HTTP origin. The origin is restricted to
127.0.0.1 with an explicit port. The final ingress rule returns 404.
The connector checks the Access audience and issuer; the product origin verifies
JWT signature, issuer, audience and expiry independently.

The binding output supplies metadata to the host configuration. Tunnel
credentials are obtained outside Terraform by the approved Secret Manager loader
operation. Dependency provenance is in docs/dependencies/cloudflare-provider.md.
