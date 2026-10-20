# 08-04A checkpoint — 2026-10-20

Status: offline foundation complete; full 08-04 and staging deployment incomplete.

- Branch: codex/platform-contract.
- Code: 2c35587061f6ff8216996be6817186f3fef2484f.
- Previous head: 79b8e17ed12f73ceb4a12552e6d5ef047bafbd54.
- Source: 15 explicit paths in code commit; no unrelated changes staged.
- No cloud resources, account settings, secrets or application data modified.

## Checks

1. Initial direct local unittest development run: 2 passed / 0 failed,
   6 Terraform mocked plans.
2. Private Google DNS addition invalidated that result. Re-run: 2 passed / 0 failed,
   now 7 mocked plans.
3. Staged final batch: `HYPRN_TF_PROVIDER_DIR=<existing bootstrap/.terraform/providers>
   tests/platform/run.sh infrastructure` → 2 passed / 0 failed in 1.431 seconds;
   7 nested Terraform mocked plans.
4. Terraform schema validation → valid, 0 errors / 0 warnings.
5. `terraform fmt -check -recursive infra/modules infra/environments/staging` and
   `git diff --cached --check` → exit 0.
6. Read-only dedicated `gcloud projects list --filter='projectId:hyprn-staging'`
   → exit 0 with no rows after owner refreshed login.

Initial sandbox-only provider schema handshake failed; approved external local
execution succeeded. No package installed. Tool hashes/licences, official sources
and cache trust boundary are recorded in the runbook.

Tests use temporary isolated copies and mocked providers, with backend disabled
and invalid isolated credentials. Temporary scopes auto-clean. Initial manual
offline cache scope was also removed after validation. No Terraform live plan or
apply was run.

## Exact pending work

- Resolve dedicated staging project/folder/billing/region/zone, operator/recovery
  groups, exact image, nonoverlapping CIDRs, three bucket names and isolated backend.
- Supply exact Cloudflare account/zone/IdP/tunnel/allowlist and JWT issuer/audience.
- Private SQL bootstrap with product role script; no credentials in Terraform.
- Numeric runtime secret versions and actual instance/disk/store identifiers.
- 08-02 host services/firewall/metadata isolation/quotas/attestation.
- 08-03 publisher/WIF/GitHub protection setup.
- Alert receivers, exact pricing and reviewed saved plan before 08-05 apply.
- 08-05/06 real deployment, two-user study, Assistant/scientific journey and restore.
- Parent reruns infrastructure on committed batch; planning STATE remains parent-owned.

Preliminary cost USD180–300/month is a sizing estimate, not a quote or spending
authorization; details and exclusions in runbooks/product-staging.md.

## Read-only discovery and plan refinement — 2026-10-20

Code commit: 0f6417d2465f22508adb040ef568b2aa5677b421, seven owned paths.
This supersedes the initial folder target, PostgreSQL 16 and USD cost estimate;
the initial result remains historical evidence. Full 08-04 is still incomplete.

- The reviewed project parent is now the required organization root input,
  with a mocked-plan assertion. No new folder or invented runtime ID.
- PostgreSQL 17 Enterprise matches the product fixture major version.
  Actual available minor version and TLS identity remain live acceptance items.
- Separate metadata for db-assistant-background and db-dispatcher-background;
  no SQL users, passwords, secret versions or credential values in Terraform.
  The dispatcher is an app-side process, not the native execution consumer.
- Existing administration group may initially fill operator and recovery roles;
  the runbook explicitly records the absence of separation of duties.
- Every workload cloud resource is Terraform-managed. State-bucket bootstrap
  must also be declarative; Cloudflare JSON templates still require a declarative
  resource owner before activation. No manual cloud creation is authorized here.
- The EUR public catalogue gives EUR152.54/month compute/disks at 730 hours.
  EUR170–220/month remains a low-traffic planning allowance, excluding tax,
  Assistant usage and paid GitHub/Cloudflare plans. It is not spending approval.

Focused verification after the changes:
HYPRN_TF_PROVIDER_DIR=<existing bootstrap/.terraform/providers>
tests/platform/run.sh infrastructure -> 2 passed / 0 failed in 1.426 seconds,
including 8 mocked Terraform plans and successful provider schema validation.
terraform fmt -check -recursive infra/modules infra/environments/staging
and git diff --check -> exit 0. Isolated test scopes auto-cleaned.
No installed dependency changed; no live plan, apply or cloud mutation.

Read-only discovery established the organization and open EUR billing account,
existing administration group, EU location policy, UP proposed zone and an exact
READY official Debian image. No staging project or staging state bucket exists.
Operational IDs, personal allowlist entries and account details stay outside Git:
private inventory directory /private/tmp/hyprn-staging-inventory-3k0g1h31
(mode0700; JSON files0600). Parent supplied verified Cloudflare account/zone,
Access activation and named allowlist; this executor did not read its credential.

Read limitations: bootstrap Compute API is disabled; its zone query failed.
Global zone/machine metadata was read through the existing Compute-enabled
project only, without adopting fleet resources. The public image-project zone
query lacked permission. Initial groups CLI syntax was unsupported; explicit
group lookup succeeded. No rejected read was treated as proof of existence.

Private evidence hashes:
- cost-summary.json: 30ee2ac8452d3731cf93782784f76d1a682aaf4b17f0f206a67f65f71d337009
- inventory.json: 9a67bd9c768f6442a9695a235f5c19a648f33a46b55262f58e5e5214b493f39e
- pricing-eur.json: 6adc93bf93930635f8627448d4063a659e868925770ec4c2a3cb76ec353deeab

Remaining before a reviewable live apply: declarative isolated state bootstrap;
exact nonoverlapping network and external egress inputs; unique workload bucket
names; Cloudflare declarative resources/PIN provider; qualified host bootstrap,
publisher protection and alert receivers. Generated project number, SQL
hostname/CA, disk identity, numeric secret versions and Access audience can only
be bound after approved provisioning. Do not use mock output as runtime data.

Parent repeats the focused group against the committed refinement. No global
planning state or another executor's file was staged. A summary-writing tool call
had a JavaScript parse error before execution; the corrected call wrote this
checkpoint without changing implementation or invalidating its checks.

## Refinement self-check

Verified commit exists, modified seven owned files, and deleted no tracked files.
