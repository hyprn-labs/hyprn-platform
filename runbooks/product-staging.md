# Product staging

Status: approved staging infrastructure and Access resources are provisioned.
The VM is stopped and has no product startup script. The Assistant resource and
provider secret exist; remaining credentials and host setup are not installed.
This is not a running application or execution attestation. Operational evidence
and remaining obligations are recorded in the staging phase checkpoints.

## Resource boundary

The staging root creates a dedicated project directly under the supplied organization, explicit
service enablement, private IPv4 subnet, Cloud Router/NAT and static NAT address.
The VM has no external address; its only ingress rule admits IAP SSH. It has a
30 GiB boot disk and a separate protected 100 GiB data disk. A pinned image is
required; an image family is refused. No production or agent-fleet resources are
referenced.

A private Cloud SQL PostgreSQL 17 Enterprise instance starts at one vCPU,
3.75 GiB memory and 20 GiB SSD, with growth capped at 100 GiB, seven retained
backups and seven-day PITR. Shared CA is explicit: GOOGLE_MANAGED_CAS_CA. Terraform
selects the provider-returned PRIVATE_SERVICES_ACCESS/INSTANCE DNS name and creates
its private A record. The application must verify both the CA and that hostname
(verify-full), using the public CA bundle delivered with the reviewed runtime.
The SQL instance has no public IPv4 address.

Artifacts, desired state and backups use separate private, versioned buckets.
Soft delete retains seven days; force deletion is disabled. No irreversible
retention lock or automatic deletion lifecycle is introduced. Registry tags are
immutable; releases still pin image digests. Storage growth, pruning of obsolete
artifacts and complete-backup retention require the reviewed recovery procedure.

## Before a live plan

Supply the following through dedicated private operational configuration, outside
Git. None is inferred from the agent fleet.

| Input | Review |
|---|---|
| project_id | Dedicated available hyprn-staging identifier; no existing project is adopted silently |
| organization_id, billing_account | Exact target and billing authority |
| region, zone | Same-region resources; initial proposed region europe-west1 |
| host_image | Exact reviewed Linux amd64 image resource, not a family |
| subnet_cidr, sql_address | Nonoverlapping private subnet and /16 SQL allocation base |
| bucket_names | Three distinct globally available names |
| operator_group, recovery_group | Existing role groups, membership reviewed separately |
| https_egress_cidrs | Approved external HTTPS address ranges for pinned bootstrap and Assistant/JWKS destinations |
| tunnel_egress_cidrs | Current Cloudflare Tunnel IPv4 endpoints on TCP/UDP 7844 |
| GCS backend bucket/prefix | Separate pre-provisioned staging state and access; never fleet/prod state |
| Cloudflare account/zone/IdP/tunnel/allowlist | Exact settings rendering the Access template |
| Runtime secret version numbers | Existing, verified numeric versions; never latest |
| Runtime IDs and public CA bundle | Actual project number, disk UUID, installation/store identities and SQL DNS after provisioning |

The project list under the dedicated refreshed GCP identity returned no matching
hyprn-staging project on 2026-10-20. That observation is not an availability
reservation or permission to create one.

Use the dedicated CLOUDSDK_CONFIG, GOOGLE_APPLICATION_CREDENTIALS and GH_CONFIG_DIR.
The state bucket/bootstrap authority requires a separate reviewed bootstrap step;
the staging root intentionally cannot create the backend it already needs.
Declare that bucket and its IAM in the reviewed bootstrap Terraform root, with
its own recorded plan and approval; do not create workload resources through
console steps. An initial local bootstrap state, if required, stays private and
is migrated to the reviewed remote backend with the resulting state lineage
verified. Every workload VM, disk, SQL instance, bucket, network and IAM binding
is managed by Terraform; host bootstrap and services are versioned platform code.
Cloudflare Access, Tunnel and DNS still require a declarative resource owner
before activation: the current JSON review template alone is not reproducible
resource management.

Initial operational configuration may use the existing administration group for
both operator and recovery roles. This reduces setup but does not provide
separation of duties between operation and backup recovery. These remain
distinct IAM bindings so separate role groups can replace them later.

1. Resolve target inputs, read current IAM/org policies and prepare the exact cost
   and settings change list.
2. Run init with the reviewed GCS backend and then plan to an external private
   file. Record source commit, tool/provider identities, input digest and saved
   plan hash. Keep plan JSON/state/private tfvars outside Git.
3. Obtain owner approval for that exact plan and cost. Apply only that saved plan.
4. Resolve generated runtime bindings; verify secret versions and SQL roles using
   the private provisioning procedure. Never print password/token contents.
5. Integrate and qualify the host services from 08-02 before changing the VM
   target from TERMINATED. Admission stays closed until actual target attestation.
6. Complete 08-03 delivery controls and 08-05/06 activation/recovery verification.

## Runtime authority

| Principal | Granted here | Not granted here |
|---|---|---|
| Trusted host service account | Read own artifact bucket, registry and desired bucket; create backup objects; read declared secret payloads; write logs/metrics | Desired-state writes, backup deletion/read, IAM administration, other environments |
| Staging operator group | IAP to this VM on port 22, staging OS Admin Login, act-as this host identity | Fleet/prod access or secret administration |
| Recovery group | Read backup objects | Delete backups or publish releases |
| Application request SQL role | Provisioned separately as hyprn_request | Schema ownership, superuser, BYPASSRLS |
| Authentication SQL role | Provisioned separately as hyprn_auth | General request/migration authority |
| Migration / backup SQL roles | Separate hyprn_migration / hyprn_backup operational credentials | Permanent mounts into ordinary app/modeling/worker containers |
| Artifact / desired publisher | 08-03 supplies distinct identities | No publisher permissions or WIF activation in this slice |

Terraform creates only secret metadata and per-secret reader IAM, never secret
versions, database passwords or SQL users. Aliases: modeling-auth, modeling-rails,
assistant-provider, db-app-request, db-app-auth, db-app-migration, db-app-backup,
cloudflare-tunnel, db-assistant-background and db-dispatcher-background. The host
is the trusted loader, not a container credential source: deliver only each component's authorized numeric-version files on tmpfs.
The tunnel credential is host-only. Modeling and the worker never receive
application/database/provider credentials.

The assistant background SQL login is app-only; the dispatcher background login
is for the dedicated application dispatcher process, separate from native execution.
The existing execution consumer must never receive that credential. Both are NOINHERIT, with EXECUTE-only access to their
reviewed product functions, no direct table privileges and no migration-role
membership. These credentials are never sent to provider agents or workers.

SQL bootstrap is a separate private operation against the fresh database using
the product's reviewed role/grant script. Keep bootstrap credentials out of
Terraform and revoke temporary privileged access. Verify role attributes, grants,
RLS and pooling scope with positive and negative application tests. Cloud SQL
network/TLS configuration alone does not establish database authorization.

## Networking and Access

The VPC denies other egress. It allows the private Google API VIP on HTTPS,
explicit external HTTPS ranges, Tunnel ranges on 7844, and the SQL allocation on
5432. Private DNS routes googleapis.com and pkg.dev to private Google access.
NAT routes permitted external traffic; it does not enforce hostname policy.

08-02 must supply the bounded hostname proxy and effective per-container
forwarding rules. Metadata IPv4, aliases and IPv6 must be blocked for every
container, while trusted host services retain metadata identity. A stopped VM
and offline Terraform checks do not prove that isolation. Verify it after Docker
start, restart and reboot before opening scientific execution. Cloudflare edge
IP ranges and third-party HTTPS addresses can change: resolve and review the
current sets, and fail closed when a destination is not admitted.

[access.json](../environments/staging/access.json) is a review template, not an
executable or complete API request bundle. Resolve placeholders and duplicate
the email include entry for each named invited user; no domain-wide admission.
Create the Access policy before DNS/tunnel publication. Use a scoped short-lived
Cloudflare API token and revoke it after configuration. Required permissions are
Tunnel Edit, Access Apps and Policies Edit, DNS Edit on the one zone, and Access
Identity Providers and Groups Edit only if creating the PIN provider.

The application is self-hosted Access at staging.hyprn.ai using email PIN.
Origin traffic must carry the verified Access JWT with the actual issuer and
application audience. There is no MCP, ChatGPT, Managed OAuth or bypass policy.
The tunnel has one reviewed loopback origin and a final 404 catch-all. Live checks
must cover admission, unauthorized denial, private studies and revocation.

## Preliminary operating cost

Planning estimate, not a quote or approved spend: EUR 170–220/month before tax
for 730 running hours in europe-west1, one e2-standard-4 host (4 vCPU, 16 GiB),
the single PostgreSQL Enterprise instance above, 130 GiB balanced VM disks and
20 GiB SQL SSD. Allowance assumes 50–200 GiB retained artifacts/backups and low
traffic/log volume. No commitments, free-tier credits or negotiated discounts
are assumed. The host size leaves room for the current bounded services and
scientific worker; a smaller machine needs measured memory acceptance.

The Cloud Billing public catalogue was read in EUR on 2026-10-20, with effective
prices at 07:00 UTC. Rate identities below make the estimate reproducible without
storing account identifiers or credentials in Git.

| Item | Monthly amount at declared sizing | Catalogue SKU |
|---|---:|---|
| VM compute: 4 cores and 16 GiB | EUR 94.71 | 9FE0-8F60-A9F0; F268-6CE7-AC16 |
| SQL compute: 1 core and 3.75 GiB | EUR 43.39 | 2154-E036-4CB2; 8A88-5E4B-2265 |
| SQL SSD: 20 GiB | EUR 2.99 | B14E-2B60-F10B |
| VM balanced disks: 130 GiB | EUR 11.44 | 6AE1-525F-8B80 |
| SQL backups | EUR 0.0704 per retained GiB-month | FB45-227E-BC1B |
| NAT/address, objects, registry, DNS, secrets, logs and modest transfer | EUR 17–67 allowance | Usage-dependent; reprice before approval |

The compute/disk subtotal is approximately EUR 152.54/month. The remainder is a
planning allowance, not a measured bill. Public NAT additionally charges per VM,
external address and processed byte; transfer-out charges can also apply.
Retained objects, SQL storage growth and logging can exceed this allowance.
A stopped VM does not eliminate disk, SQL, address or storage costs.

Assistant provider spending, Cloudflare/GitHub paid plans, support, tax and
unusually large scientific artifacts are excluded. Confirm the current
region-specific catalogue and all usage assumptions before plan approval.
Budget alerts are notifications, not hard caps; worker concurrency/time limits
and storage quotas must enforce operational bounds.

## Recovery and activation work retained

08-02 owns systemd/reconciler integration, container firewall, disk identity,
quotas, bounded worker startup and secret delivery. 08-03 owns CI/publisher IAM
and actual repository protection prerequisites. This root supplies no startup
script and no automatic deployment authority.

08-04/05 still need real alerts to named operator/recovery roles for disk pressure,
failed deployments, stale complete backups, authentication anomalies and
desired/applied release mismatch. Logging/metric writer IAM is not monitoring.
No alert receiver is invented here.

Cloud SQL PITR does not recover modeling/AiiDA/evidence state. Before retaining
new studies, demonstrate a coherent complete backup and isolated restore;
fence the previous writer before mounting data elsewhere. Never rewind the
application database over newly accepted writes to undo a deployment.

## Offline validation and provenance

Run `HYPRN_TF_PROVIDER_DIR=<reviewed-provider-cache> tests/platform/run.sh infrastructure`.
The tests copy modules into a temporary scope, initialize without a backend or
network acquisition, validate against the provider schema, and evaluate seven
mock-provider plans. Inputs and providers are synthetic; no cloud account is
contacted and scratch scopes are released.

Existing local tooling reused, no package installed:
- Terraform 1.16.5, existing Homebrew binary, BSL 1.1; official source
  https://releases.hashicorp.com/terraform/1.16.5/ .
  Observed darwin_arm64 executable SHA256:
  `22df21d6313d216a8c43737fc8c07411dd744925059f946e86d60cbad1acea23`.
- hashicorp/google 8.6.0, MPL-2.0; source
  https://github.com/hashicorp/terraform-provider-google/tree/v8.6.0 .
  Lock checksums copied from the already-used bootstrap lock; offline init
  verifies those hashes. Observed cached darwin_arm64 executable SHA256:
  `5c10db03fc0f377f85554a0566bccd051b2208a6fa8cc1d1a41e72c1d0a9529d`.
  The offline cache is not a fresh publisher-signature verification.
- Docker/cloudflared/host image acquisition and Linux binary attestation remain
  08-02/05 inputs. No versions or checksums for unreviewed downloads are invented.

Official references checked 2026-10-20:
- [Google provider 8.6 SQL schema](https://github.com/hashicorp/terraform-provider-google/blob/v8.6.0/website/docs/r/sql_database_instance.html.markdown)
- [Cloud SQL TLS and PSA DNS](https://docs.cloud.google.com/sql/docs/postgres/configure-ssl-instance#server-identity-verification)
- [Private Google Access DNS/routes](https://docs.cloud.google.com/vpc/docs/configure-private-google-access)
- [Cloudflare Tunnel firewall](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/)
- [Terraform provider mocking](https://developer.hashicorp.com/terraform/language/tests/mocking)
- [Compute pricing](https://cloud.google.com/products/compute/pricing)
- [Cloud SQL pricing](https://cloud.google.com/sql/pricing)
- [NAT pricing](https://cloud.google.com/nat/pricing)
- [Storage pricing](https://cloud.google.com/storage/pricing)

## State bootstrap execution — 2026-10-20

The platform owner approved creation of the staging-state bucket and initialization
of the three isolated state namespaces. The exact initial plan was SHA256
`59066c7fc6605638b252861d588c33c6fbee77c9e0f59b3a7453e864a52676dc`.
Expired application-default authentication stopped creation. A dedicated CLI
identity remained valid; readback confirmed no bucket and zero local resources.
The failed attempt advanced local state, making the saved plan stale. The refreshed
plan's resource changes and planned values were identical; SHA256
`4bdc963c13f841f3fd9f47211fe8e0d260ceb316cace53a77ad90a9e42d4f8a2`.
It applied the same approved one-bucket operation successfully.

Backend transition commit `89429d2` changed the bootstrap root to GCS. Migration
and both empty-state initializations succeeded in the namespaces enumerated in
[08-04C checkpoint](../.planning/phases/08-product-staging/08-04C-CHECKPOINT.md).
Bootstrap readback owns exactly one bucket; main and Access states are empty.
The bootstrap plan is no-op. Original local state and backup are retained privately.
Short-lived dedicated CLI tokens were passed only in process environment; backend
metadata was checked not to retain the token. No existing fleet state was touched.

Actual main staging and Access saved plans were produced at this checkpoint: respectively
76 creates and 6 creates, zero updates/deletes. Main SHA256
`f28a7719fec047dfd224318afa4a8adb22491c2bdf309bc0c4e8c91e7fc82e40`;
Access SHA256 `f2e1956b02842ac5f1ea03d9fce9c6c2f0892de68163e866050553c9463c15d2`.
Source snapshot `8a5ca936e60560132e227eff1c2163757cc55359`; operational inputs,
plans, logs and cost review stay outside Git. No application infrastructure,
provider resource, secret transfer, GitHub setting or workload activation occurred.

## Application infrastructure provisioning — 2026-10-20

The owner approved the two exact plans above and the EUR 170–220 monthly
planning envelope. Both applied successfully: 76 GCP creates and six Cloudflare
creates, no updates/deletions. GCP readback and refreshed plan show no drift.
Cloudflare refresh shows no resource changes; the policy's computed app_count
changed from zero to one after attachment, affecting the review output only.
No second apply was run to write this computed output.

Independent readback confirms the VM is stopped, private, shielded and
deletion-protected. PostgreSQL 17 is ready with private IP, encrypted connections,
shared CA mode, backups/PITR and a 100 GiB growth cap. Product buckets are private,
uniform-access and versioned. All ten secret containers remain empty. Access
admits exactly the owner-supplied two addresses through email PIN; the tunnel
requires the matching Access assertion, has the loopback origin and final 404,
and has no running connector. No provider resource, secret transfer, GitHub
setting change or application activation was performed.

The external HTTPS check failed at TLS for the reviewed nested staging hostname.
The zone is an active full zone on Cloudflare Free: Universal SSL covers only
the apex and first-level subdomains. Certificate-pack reads are denied by the
current token, so no certificate inventory is claimed. Prepare the unused
first-level staging.hyprn.ai as a narrow separately reviewed hostname correction;
do not buy a subscription or weaken TLS. Source:
[Universal SSL limits](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/limitations/).

Private operation records retain the exact approved plans, source/input hashes,
apply logs, live readback, post-apply plans and failed edge check. The temporary
verifier initially used a Terraform-style disk growth key; correcting it to the
actual GCP API storageAutoResizeLimit field allowed all resource assertions to
pass. This did not change infrastructure or weaken the growth-cap assertion.
Application availability, actual sign-in, Linux runtime containment, backup
restore and automatic deployment remain unverified.

## Approved hostname correction — 2026-10-20

The owner approved saved plan SHA256
`0d9ad1c5f34ed8e7c488a665a62bec1270e5533b1d5309e93010a1497ebf5993`.
Three in-place updates renamed the DNS record, Access domain and tunnel route
to staging.hyprn.ai. Apply exited 0; there were no creates, deletes or replacements.
Verified HTTPS returns 302 to the configured Access team; no redirect was followed
and no login email was sent. Post-apply Access plan exits 0 with no changes.
Resource readback still confirms the approved policy, stopped private VM and
protected storage/database. Application activation remains pending.

Platform source `da47395`, with derived fixture pins completed at `fb7bf11`,
aligns Terraform, deployment contract and review template. Acceptance on that
source: `tests/platform/run.sh contracts` 20 passed (11.463 seconds);
`HYPRN_TF_PROVIDER_DIR=<reviewed-cache> tests/platform/run.sh infrastructure`
2 passed/eight mocked plans (2.318 seconds);
`HYPRN_CF_PROVIDER_DIR=<reviewed-cache> tests/platform/run.sh access-infrastructure`
1 passed/twelve mocked plans (2.498 seconds). Initial sandbox runs could not
start provider IPC; reruns outside that filesystem sandbox passed. Initial
contract tests correctly rejected a stale synthetic schema hash; schema, release
and rendered configuration hashes were regenerated, without loosening validation.
Temporary test scopes were released. No product/native checks were repeated
for this platform-only hostname correction.

## Product runtime wiring — 2026-10-20

Admission contract source `e3ca6d2` and invocation documentation `8a1cb19`
passed parent checks: contracts 20 passed (5.052 seconds), secrets 18 passed
(8.541 seconds). These are offline checks, not application activation.

Linux composition inspection found missing application control/Assistant inputs
and modeling mount targets that differed from the actual image entrypoint.
The renderer now binds host-owned read-only control records and explicit model,
artifact, UI and database CA settings. Modeling uses its existing store/key paths.
No cloud resources changed. Initial updated contracts check failed one exact
Assistant-settings expectation; the fixture was extended for the two required
control-file paths, without dropping exactness assertions.

A read-only provider inventory and retained local ledger reconcile five idle
HYPRN sessions: 476 USD cents in the local ledger plus the same 25-cent session
already carried by the local allowance, total 501 cents. It must not be counted
twice. The existing approved EUR 100 conversion ceiling is preserved. This is a
provisional transition review: refresh usage and fence old local delivery before
new cloud admission. Private session identities and evidence remain outside Git.

Committed wiring `1e5915d` passed parent `tests/platform/run.sh contracts`
(21 tests, 4.566 seconds) and `tests/platform/run.sh secrets` (18 tests,
8.300 seconds), both exit 0 with scopes released. No Terraform plan or cloud
operation was repeated for this source-only wiring correction. Actual Linux
startup remains the product lifecycle task's next boundary check.


## Native execution projection — 2026-10-20

Contract source `231bad2` adds an execution-only projection with exact source,
native environment, interpreter, private execution home and Unix Docker endpoint.
The native dependency lock participates in release identity. Network Docker
endpoints and noncanonical paths are refused. Product lifecycle binds the stable
execution projection digest separately from the full host configuration digest,
so changing admission does not create an attestation hash cycle. Logical store
identity remains distinct from the native UUIDs observed at initialization.

Parent acceptance: `tests/platform/run.sh contracts` passed 23 tests in 5.282
seconds on the committed source (development run: 23 in 4.838 seconds). Exact
private logs are retained with the deployment review. This extends the earlier
application store identity source `72d533e`, whose contracts passed 21 tests in
4.540 seconds. No secret delivery implementation changed and no cloud operation
was repeated. Product consumer `44b87a0` pins the exact updated contract files.
Installed Linux execution, host socket permissions, containment attestation and
release replacement remain required before application activation.

## Host inspection and recovery authority — 2026-10-21

The owner approved and applied the four-resource recovery IAM plan: database
backup create/read authority scoped to this installation, and exact VM/data-disk
metadata reads. Exact role/binding readback matched. No backup was created.
The reviewed plan SHA256 is
`c3101b526c57211277acb6daccbe4f91f78e33e7472eed22a14b4b336bf07c37`.

Two separately approved temporary start/inspect/stop operations followed. The
first reached RUNNING before guest SSH was ready and stopped cleanly after IAP
refused. The revised operation captured boot diagnostics and retried only the
read-only inventory. Operator OS Login over IAP succeeded on its second attempt;
the same VM was stopped and TERMINATED was confirmed afterwards. No cloud
firewall change was needed. Ephemeral operator SSH keys expire after 15 minutes.

Actual host inventory: Debian 12 AMD64, systemd, kernel 6.1.0-53-cloud-amd64, no swap;
Docker/connector and execution account are absent. The 100 GB data disk has no
filesystem or mount; the 30 GB boot disk contains the OS. iptables is installed
(version 1.8.9-2), though absent from the unprivileged login PATH. No packages,
application process, secrets or disk formatting were introduced by inspection.
Inventory SHA256:
`552b44970d1e3718b82f66e0babf6fae1f09ab18df2bbc26f017b8da8552dc48`.

Private review/evidence root:
`/private/tmp/hyprn-staging-inventory-3k0g1h31`, in recovery-authority,
host-inspection and host-inspection-ready. Exact approved inspection hashes:
`79c1e4bdb24838ff97618d5b70b0c4651b76315c40b67f923594055d38e6aa59` and
`d183a4ab1756448d9b9e4c10d86a6a695ac5b8e2035a23a12213d5938ea3a08f`.

Next: prepare pinned package acquisition and declarative host setup for approval;
then qualify actual AMD64 execution, update/recovery and external Access sign-in
before admission. The local ARM rehearsal of the released lifecycle wrapper
refused the AMD64 worker's architecture-warning-prefixed output; it does not
establish execution qualification for the rebuilt native bundle.
