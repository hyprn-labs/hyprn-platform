---
phase: 08-product-staging
plan: "04B"
type: execute
autonomous: true
depends_on: ["08-04A"]
---
# Declarative staging Access boundary

## Task
Implement a dedicated Cloudflare Terraform root and access module: email OTP,
one exact-email allow policy, a self-hosted staging.app.hyprn.ai application,
remote-managed tunnel metadata/configuration, and proxied DNS ordered after Access.
No cloud mutation or live credential read is authorized. Origin JWT verification
remains required independently of Access and connector checks.

## Ownership
infra/modules/access/, infra/environments/staging-access/,
tests/platform/test_access_infrastructure.py; only the access-infrastructure case
in tests/platform/run.sh; docs/dependencies/cloudflare-provider.md; this plan,
checkpoint and summary. Other changes remain with their owners.

## Acceptance
Write evaluated mock-plan tests first, validate against the real pinned provider,
prove exact admission, no bypass, loopback origin and final 404. Reject malformed,
wildcard and empty allowlists and non-loopback origins. Inspect evaluated resource
configuration, provider schema and dependency graph; no source-only substitute.
Run tests/platform/run.sh access-infrastructure on the committed tree.

## Prerequisites and retained obligations
Audit official release, source, hash, licence and tunnel state model before any
provider download. Live account/zone/team, named emails, loopback port, dedicated
HYPRN identity and isolated GCS state are owner runtime inputs outside Git.
Existing resources must be inventoried/imported before any live plan.
Secret retrieval into Secret Manager is a separately approved future runtime
operation; no token data source or secret input/resource/output belongs here.
08-05 retains exact reviewed-plan apply and observed denial/revocation checks.
The parent owns shared STATE/ROADMAP updates to avoid concurrent edits.
