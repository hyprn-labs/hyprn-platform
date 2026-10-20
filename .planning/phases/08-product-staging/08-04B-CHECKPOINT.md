# 08-04B — offline Cloudflare Access checkpoint

Status: implementation complete; live Access is unverified. No cloud mutation,
live-token read, login attempt, Terraform apply or token retrieval occurred.

## Commits and evidence
- 520e189: test-first boundary, registration, compact plan and audited provenance.
- c9baa7c: six-resource module, isolated staging root, lock and evaluated tests.
- Acceptance tested at c9baa7c64cc23642d60092eb70d42952dd0ef307.

Exact acceptance command:
`HYPRN_CF_PROVIDER_DIR=/tmp/hyprn-cf-provider-cache tests/platform/run.sh access-infrastructure`

Result on committed tree: exit 0; unittest 1 passed, 0 failed (2.531 s).
Within it: Terraform 1.16.5 init with isolated local persistence, validate,
providers schema, 12 evaluated mock plans (12 passed, 0 failed, 0 skipped),
dependency graph reachability, and deliberate bypass mutation detected by an
evaluated assertion. The graph proves DNS depends on application, exact policy,
and connector configuration. No live boundary is simulated as a proven service.

Additional commands: `terraform fmt -check -recursive infra/modules/access infra/environments/staging-access`
and `git diff --check`, both exit 0.

## Failures
1. Initial RED: `python3 -B -m unittest discover -s tests/platform -p test_access_infrastructure.py -v`,
   exit 1, one targeted assertion failure: declarative root did not yet exist.
2. First acceptance attempt: exit 1, one failure, schema command required backend
   initialization despite init -backend=false. The production root retains GCS;
   tests now override only persistence to a local backend in their scratch copy.
3. First scratch override had invalid single-line nested HCL: exit 1, one failure;
   corrected to multiline HCL. GCS initialization stopped at the deliberately
   nonexistent credential file, before authenticating; no live credentials read.
4. Working-tree acceptance then passed (1 unittest, 12 plans, zero failures, 2.833 s);
   committed-tree acceptance above confirms the delivery source.

Research diagnostics: sandbox curl could not resolve api.github.com; the approved
network read succeeded. Web fetches for two versioned metadata URLs returned cache
misses; official HTTPS source/API reads resolved them. GSD init --pick with comma
fields was invalid; no project state was changed by that read.

## Pins and cleanup
Cloudflare provider 5.28.0, Apache-2.0; source revision
fa63ebaea80e153d0d9325f818adc36187a8e12a.
Archive SHA256 886714cfd9ada7876dd39ed857661766d9b75ba205079c3b70c4d5b56e9955b8.
Executable SHA256 7f2ed119cddfbf94c3cca4171080a1e9735856bde4d3a6cc63c43e3467244632.
Official links and existing Terraform pin: docs/dependencies/cloudflare-provider.md.
Only darwin_arm64 is qualified; other operator platforms require separately
audited binary acquisition and lock hashes before use.

Every test/init TemporaryDirectory was released, including local synthetic state,
mock plans, invalid credentials paths and copied source mutations. Provider cache
at /tmp/hyprn-cf-provider-cache is retained for the parent's committed-tree rerun;
the parent may remove this task-owned directory after acceptance. Research files
at /tmp/hyprn-cf-docs are nonsecret official source material and may be removed.
No generated files were left untracked inside the repository by this task.
Other agents' unrelated modifications and staging entries were preserved.

## Operational plan preparation requirements
Owner/runtime operator retains these inputs outside Git:
- Exact Cloudflare account and hyprn.ai zone IDs; existing Access team subdomain.
- Nonempty exact lowercase admitted emails; no domain invitations or bypass.
- Reviewed host loopback HTTP port matching the renderer and origin JWT settings.
- Dedicated HYPRN GCS backend bucket/prefix for this root, separate from the GCP
  staging root and all production state, plus restricted state/plan access.
- Dedicated HYPRN CLOUDSDK_CONFIG, GOOGLE_APPLICATION_CREDENTIALS and GH_CONFIG_DIR;
  short-lived scoped CLOUDFLARE_API_TOKEN injected by the operator outside tfvars.
- Token permissions: account Tunnel Edit, Access Apps and Policies Edit, Access
  Identity Providers and Groups Edit for managed IdP, and hyprn.ai zone DNS Edit.
  Confirm the exact current permissions on the dedicated token before live plan.
- Existing application/IdP/policy/tunnel/DNS inventory. Import/adopt matching
  resources into this isolated state through a separately reviewed operation;
  do not create a duplicate shared OTP IdP or overwrite unmanaged policy/DNS.

With external protected backend/input files and dedicated credentials, the
operator can initialize this root with `terraform init -backend-config=<external-backend-file>`
and create `terraform plan -input=false -var-file=<external-input-file> -out=<external-saved-plan>`.
No live plan was generated here. Record source commit, provider lock, input digest,
state lineage/serial, saved-plan SHA256, resource actions, permission scope and
costs. Review all six resources, full hostname coverage, exact admitted emails,
no additional policy, connector JWT checks, loopback origin, final 404, proxied
DNS and dependency order. Explicit owner go must name that unchanged plan.
Any deletion requires its own go under AGENTS.md; changed inputs require replan.

Disable Terraform/provider debug logging. Real emails appear in protected state
and saved plans but not Git. Secret values never belong in either. Never add a
tunnel-token data source, secret input/output or Secret Manager secret-version
resource. After metadata apply, a separately approved nonlogging runtime step
retrieves the tunnel token directly to Secret Manager, checks shape only, pins
its numeric secret version, and leaves it out of stdout, argv, state and Git.

Before claiming live Access: bind actual issuer/audience at the application origin,
verify invalid/missing/expired/wrong-audience JWT denial, unauthorized and revoked
user denial, no direct origin access, connector fallback, then exact invited
email login. Embedded Assistant is retained; external MCP/ChatGPT/OAuth remain
retired. 08-05/06 own deployment and live/human acceptance.
