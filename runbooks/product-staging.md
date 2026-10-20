# Product staging

Status: offline infrastructure foundation. No cloud resource or Access policy has
been created by this work. The VM is deliberately stopped and has no product
startup script. This is not an application deployment or execution attestation.

## Resource boundary

The staging root creates a dedicated project under the supplied folder, explicit
service enablement, private IPv4 subnet, Cloud Router/NAT and static NAT address.
The VM has no external address; its only ingress rule admits IAP SSH. It has a
30 GiB boot disk and a separate protected 100 GiB data disk. A pinned image is
required; an image family is refused. No production or agent-fleet resources are
referenced.

A private Cloud SQL PostgreSQL 16 Enterprise instance starts at one vCPU,
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
| folder_id, billing_account | Exact target and billing authority |
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
assistant-provider, db-app-request, db-app-auth, db-app-migration, db-app-backup and
cloudflare-tunnel. The host is the trusted loader, not a container credential
source: deliver only each component's authorized numeric-version files on tmpfs.
The tunnel credential is host-only. Modeling and the worker never receive
application/database/provider credentials.

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

The application is self-hosted Access at staging.app.hyprn.ai using email PIN.
Origin traffic must carry the verified Access JWT with the actual issuer and
application audience. There is no MCP, ChatGPT, Managed OAuth or bypass policy.
The tunnel has one reviewed loopback origin and a final 404 catch-all. Live checks
must cover admission, unauthorized denial, private studies and revocation.

## Preliminary operating cost

Planning estimate, not a quote or approved spend: USD 180–300/month before tax
for 730 hours in a typical European region, one e2-standard-4 host, the single
small Cloud SQL instance above, 130 GiB VM disks, 20 GiB SQL storage, 50–200 GiB
artifact/backup objects and low traffic/log volume. Region, currency, actual
retained bytes and workloads change the bill. No commitments or discounts assumed.

| Item | Approximate monthly allowance |
|---|---:|
| VM compute | USD 100–140 |
| Cloud SQL compute, SSD and ordinary backup use | USD 55–85 |
| VM disks | USD 13–20 |
| NAT gateway + one external address | USD 4.67 at published rates, plus traffic |
| Buckets, registry, DNS, secret operations and logs | USD 7–40 |

Public NAT currently charges USD 0.0014 per assigned VM-hour, USD 0.005 per
external-IP-hour and USD 0.045/GiB processed, plus applicable transfer-out charges.
The 730-hour base is 730 × (0.0014 + 0.005) = USD 4.672.
A stopped VM does not eliminate disk, SQL, address or storage costs.
Assistant provider spending, Cloudflare/GitHub paid plans, support, tax and
unusually large scientific artifacts are excluded. Confirm the region-specific
calculator/price export before plan approval. Budget alerts are notifications,
not hard caps; worker concurrency/time limits and storage quotas must enforce
operational bounds.

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
