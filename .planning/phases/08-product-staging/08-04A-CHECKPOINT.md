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
