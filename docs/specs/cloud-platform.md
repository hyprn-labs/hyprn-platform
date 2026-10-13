# Cloud platform specification

Status: current specification. In service: the organization baseline and the agent fleet (`bootstrap/`, `infra/agents/`). Staging, prod and the delivery pipeline follow this document.

It specifies how the HYPRN MVP cloud edition is hosted, delivered and operated on Google Cloud: infrastructure, identities, delivery, runtime lifecycle, recovery, observability, security and cost. Product behavior (scientific semantics, API, agent tools, UI) is specified in the product repository and appears here only where the platform must preserve it.

**MUST** marks an acceptance requirement. **Default** is the initial choice unless implementation finds a concrete incompatibility, which is then recorded in an ADR. **REQUIRED input** is a value the platform owner supplies before the dependent step.

## 1. Scope and non-goals

In scope:

- Two hosted environments, `staging` and `prod`, each in its own Google Cloud project.
- One full-stack host per environment running the fixed product workload (`app`, `modeling`, `execution`, `worker`) plus an edge proxy and a host reconciler.
- Terraform for infrastructure, reviewed Git and GitHub Actions for delivery, Secret Manager for runtime secrets.
- An explicit product lifecycle on the host (initialize, check, admission, drain, migrate, start/stop, qualify, backup, restore), coordinated multi-store backup and a timed restore drill.
- The cloud-edition integrations the platform must enable: outbound access to the managed-agent provider, a sign-in service and the application PostgreSQL database.

Non-goals: Kubernetes, Argo CD, Cloud Run, service mesh, message broker, developer portal, schema registry or generic workload framework; high availability, multi-zone or multi-region serving, autoscaling; remote or customer-site scientific execution; migration of old local or development run data (cloud stores start empty); a standing third cloud environment (development uses the local edition); product code in `hyprn-platform`; Google Cloud SDK calls inside product code.

## 2. Product constraints the platform preserves

| Constraint (approved architecture) | Platform consequence |
|---|---|
| One cohesive application owns API, authorization and records; all clients (UI, agents, MCP) use the HYPRN MVP API | One `app` component; the agent bridge runs inside it |
| A private, replaceable modeling service (a patched copy of WhatsOpt, GNU AGPL v3) owns editable composition and native static code generation behind the Modeling Backend Contract | `modeling` has no public listener, no application or AiiDA store, no execution authority, no provider or cloud credentials; its source notices ship with every release. Network separation is not a licensing conclusion; legal review gates commercial launch (Q13; facts and open items in `docs/legal/licensing.md` of the `hyprn-mvp` repository) |
| Preparation never executes candidate code; only the frozen generated program runs, in a restricted worker under a current host attestation | `worker` is networkless, credential-free and bounded. A changed host image, kernel, Docker, launcher or policy invalidates the attestation and requires requalification on the actual host |
| AiiDA owns scientific processes and artifacts, OpenMDAO owns numerics; no second scheduler or provenance engine | No cloud resource per run. The trusted `execution` host service owns AiiDA state and Docker launch authority |
| Exact pins; missing output is never zero; uncertain jobs are never redispatched | Drain, restore and reconciliation never reset, re-run or invent results |
| Local-first editions: one core, `editions/local/` now, `editions/cloud/` later, chosen by the installation configuration's `edition` field | Product code reads configuration and secret file paths; cloud retrieval (Secret Manager, GCS, metadata identity) lives in the platform host adapter |
| Studies are archived, never deleted; pilot records are retained from the pilot retention boundary | Complete backup sets; deletion-protected production data; no destructive maintenance without its own reviewed procedure |

## 3. Environments and authority separation

| Environment | Where | Purpose | Data |
|---|---|---|---|
| `local` | Developer machine, local edition | Development and owner testing | Never copied to the cloud |
| `staging` | Project `hyprn-staging` | Qualification of exactly the release later promoted | Synthetic only, engineering access |
| `prod` | Project `hyprn-prod` | Invited pilot, then the hosted product | Pilot and customer data |

Staging and prod never share a project, host, disk, database, bucket, secret, service account, Terraform state or scientific identity. Projects are the Google Cloud unit for services, billing and permissions ([resource hierarchy](https://docs.cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy)), so "staging cannot touch prod" becomes an IAM property, testable with negative checks. Each environment has its own Terraform root and state bucket; Terraform workspaces are not an access boundary. Production data is never restored into staging; restore drills use a temporary isolated host (section 9.6).

## 4. Repository ownership and the deployment contract

### 4.1 Two repositories

| Repository | Owns | Does not own |
|---|---|---|
| `hyprn-mvp` (product) | Application, UI, integration (AiiDA bridge, launcher, worker), modeling patches and notices, contracts, product Compose topology, lifecycle CLI, image build contexts, locks, editions, product ADRs | Cloud resources and identities, environment bindings, which release runs where |
| `hyprn-platform` | Terraform (bootstrap, staging, prod), cloud and CI identities, repository governance, the deployment schema set, naming rules, host adapter (renderer, reconciler, secret loader, systemd units, firewall), environment bindings and desired releases, runbooks, inventory, platform ADRs | Scientific and API contracts, database schemas, images |

Each effective field has one owner. Terraform owns cloud resources; the reconciler owns the rendered runtime on the host; neither rewrites the other. Each repository keeps MADR decisions under `docs/adr/`.

### 4.2 Workload contract

The schema set lives in `hyprn-platform/contracts/v1/`; product CI pins it by platform commit and file hashes. Contract `hyprn-workload/v1` declares `product: hyprn-mvp` and exactly four components:

| Component | Artifact | Data role | Secret aliases | Trust role (fixed mapping) |
|---|---|---|---|---|
| `app` | OCI image | application | `modeling-auth`; later only reviewed agent, identity and database aliases | Application behind the edge |
| `modeling` (implementation `whatsopt`) | OCI image | modeling | `modeling-auth`, `modeling-rails` | Private, no public port |
| `execution` | Native bundle installed on the host | execution | none | Trusted host service with Docker authority |
| `worker` | OCI image | ephemeral | none, ever | Restricted scientific job |

Platform-owned infrastructure roles: `edge` (TLS proxy), `reconciler` (host adapter and secret loader) and, from the identity milestone, `identity` (section 10.2).

Validation uses safe parsing, then schema and semantic checks. It rejects unknown fields, duplicate keys, executable YAML tags, unpinned images, unsupported versions, secret aliases without bindings, cross-environment references and any widening of secrets, mounts, capabilities or network. Allowed sets change only through platform review, so a product pull request cannot gain privileges by adding a field. Product Compose owns commands, ports and internal topology; the platform renderer supplies images, roots, UIDs, resource profiles, secret mounts and exposure from one validated binding and checks the effective output against policy. The rendered preview never shows secret values. Golden fixtures prove stable rendering; negative fixtures prove unsafe input fails.

### 4.3 Release descriptor

A release is the complete compatible artifact set built once from one product commit. Descriptor v1 is canonical JSON containing: schema, product, full source commit and source-inventory hash; workload contract digest and product contract versions; targets (`linux/amd64` mandatory); OCI digests for `app`, `modeling`, `worker`, the native bundle hash and size, and the UI asset manifest hash; build inputs (toolchain, base images, upstream sources, patches, locks); per-owner migrations (ordered IDs and checksums, readable range, writable version, rollback compatibility, backup requirement); execution identities (worker, launcher, evaluator, policy, native hashes, attestation format); and evidence digests (tests, provenance, SBOM, licence and source notices).

The descriptor digest plus target identifies the release. Deployment input is always a digest, never a tag, because tags can be moved to other content ([Artifact Registry images](https://docs.cloud.google.com/artifact-registry/docs/docker/manage-images)). Bundles are size- and hash-verified and rejected if they contain absolute paths or `..` segments, escaping links, device files, duplicates or unbounded expansion.

### 4.4 Environment binding and desired state

`environments/<env>/runtime.yaml` holds physical bindings: project, zone, host identity, external origin, registry and bucket bindings, data-disk identity, resource profile, allowed secret aliases with numeric versions, observability and recovery settings. No passwords, no shell.

`environments/<env>/desired.yaml` (`hyprn-desired/v1`) holds the environment, a monotonically increasing sequence, the release digest, target, rendered-config digest, platform adapter version and digest, maintenance policy and qualification references. Every change, including config-only changes and rollbacks, takes a new sequence.

### 4.5 Naming

- Company namespace `hyprn` for platform resources; each hosted product keeps its own product codename (`hyprn-mvp` for the first product); environments `local`, `staging`, `prod` only; components and roles as above. Never an architecture style, a person or a partner in durable identities.
- Physical names `hyprn-<env>-<role>[-<instance>]` (for example `hyprn-prod-host-01`, `hyprn-staging-backup`); purpose-named service accounts (`hyprn-prod-runtime`, `hyprn-prod-terraform`); secret alias `modeling-auth` maps to `hyprn-<env>-modeling-auth` at a pinned version.
- Labels `product`, `environment`, `component`, `owner`, `managed_by`.
- Helpers validate each resource type's name rules. Project and bucket IDs are global: plain names first, a random suffix only when a name is taken, recorded as an explicit binding. Names never grant authority, encode tenancy or contain personal data. Renames use a state move or import, never an accidental replace.
- The product name is HYPRN MVP in prose; product technical identifiers use `hyprn-mvp` and the `HYPRN_MVP_` environment prefix.

## 5. Infrastructure layout

### 5.1 Projects, region, APIs

- One project per environment under the company billing account and organization or folder (REQUIRED input).
- Default region `europe-west1`, zone `europe-west1-b`, same CPU architecture (`linux/amd64`) in both environments.
- Explicitly enabled APIs: Compute Engine, Artifact Registry, Secret Manager, IAM, IAM Credentials, Security Token Service, Resource Manager, Service Usage, Cloud Storage, Logging, Monitoring, IAP, OS Login; Cloud SQL Admin and Service Networking from the PostgreSQL milestone; Cloud DNS and Billing Budgets only where Terraform manages those resources.
- Google-managed encryption at rest. No application signing key initially.

### 5.2 Network

- One custom VPC and subnet per environment; no default network.
- Ingress: TCP 80/443 to the host's static IP; TCP 22 only from IAP's forwarding range `35.235.240.0/20` ([IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding)). Application, modeling, databases, metrics and the Docker API have no public listener.
- Egress: VPC firewall rules allow egress by default and apply per VM, not per container ([VPC firewall rules](https://docs.cloud.google.com/firewall/docs/firewalls)). So egress is enforced twice: a VPC deny-all egress rule with explicit allows for Google APIs and approved endpoints, and host rules per container network. `worker` uses Docker network `none`; `modeling` reaches only `app`; `app` reaches `modeling`, the database and an allowlist of named endpoints (section 10.1). Each new endpoint is a reviewed platform change.
- Docker diverts published-port traffic before ordinary host firewall chains ([Docker packet filtering](https://docs.docker.com/engine/network/packet-filtering-firewalls/)). The host pins one firewall backend, enforces rules on the forwarding path and verifies effective rules after Docker restart and reboot.
- Any process that can reach the metadata server can read all its values ([metadata server](https://docs.cloud.google.com/compute/docs/metadata/overview)). Metadata MUST be denied to every container (`169.254.169.254`, `metadata.google.internal`, the IPv6 address where enabled, and alternate paths), verified by tests. Only trusted host services use the VM identity.

### 5.3 Host

- One VM per environment. Initial profiles: staging `e2-standard-4` (4 vCPU, 16 GiB), prod `e2-standard-8` (8 vCPU, 32 GiB), 30 GiB boot disk, no GPU. Starting measurements, not capacity claims.
- Default OS Debian 12, pinned image. Python 3.12 for the native integration comes from a pinned, hashed distribution inside the native bundle, never from the OS.
- Bootstrap through pinned cloud-init or a reviewed image, not the deprecated container startup agent ([deprecation](https://docs.cloud.google.com/compute/docs/deprecations/container-startup-agent-on-compute)). It installs platform prerequisites only; product state arrives through the reconciler.
- Docker Compose runs `edge`, `app`, `modeling` (later `identity`); systemd runs trusted host services. Containers use `restart: no` so Docker cannot bypass startup gates; systemd restarts only validated units with bounded backoff.
- Administrative SSH only through OS Login and IAP ([OS Login](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin)); project-wide SSH keys blocked.
- Prod VM deletion protection on ([deletion protection](https://docs.cloud.google.com/compute/docs/instances/preventing-accidental-vm-deletion)).

```text
/etc/hyprn/                     root-owned config, delivery allowlist, host identity
/opt/hyprn/releases/<digest>/   immutable product artifacts and native venv
/opt/hyprn/platform/<version>/  pinned host adapter
/srv/hyprn/<env>/               persistent data disk: identity.json, application/, modeling/,
                                execution/ (AiiDA), edge/ (TLS), deployment/ (journal, ledger),
                                backup-staging/
/run/hyprn/                     tmpfs: locks and per-component secret files
```

### 5.4 Persistent data disk

- A separate balanced persistent disk holds all mutable data: 100 GiB staging, 200 GiB prod initially, with per-area quotas so candidate output, exports, backups or logs cannot fill it.
- Auto-delete disabled; Terraform `prevent_destroy` on prod. That guard does not survive deleting the resource block ([Terraform lifecycle](https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle)), so destructive diffs are also caught in plan review and IAM.
- `identity.json`, written once at initialization, records disk UUID, environment, project, installation ID, store IDs and AiiDA profile and repository identities. A missing mount, changed identity or unexpected pre-existing directory refuses startup. Only `initialize` may format, and only the exact Terraform-created blank device.
- One writer at a time: host replacement fences the old executor, moves the disk to exactly one new host and verifies identity before requalification. A local lock cannot fence two VMs.
- A zonal disk is not regional availability; another zone is reached through backups.

### 5.5 Buckets and registry

All buckets enforce public access prevention and uniform bucket-level access. Four purposes per environment, separated because writers, readers and retention differ:

| Bucket | Writer | Reader | Retention |
|---|---|---|---|
| `hyprn-<env>-tfstate` | Environment Terraform identity | Same, recovery admins | Versioning on; GCS backend state locking ([GCS backend](https://developer.hashicorp.com/terraform/language/backend/gcs)) |
| `hyprn-<env>-artifacts` | Build (staging) or promoter (prod) | Runtime | Active release plus two rollback-compatible releases, 30-day floor |
| `hyprn-<env>-desired` | Environment publisher only | Runtime, read-only | Create-once history plus `current.json` |
| `hyprn-<env>-backup` | Runtime, create-only | Recovery operator | 30 daily complete sets plus migration recovery points |

Soft delete (7 days default, up to 90) stays on for desired-state and backup buckets ([soft delete](https://docs.cloud.google.com/storage/docs/soft-delete)). Retention locks are never applied irreversibly without owner authorization. One Artifact Registry Docker repository per environment, IAM at repository scope ([access control](https://docs.cloud.google.com/artifact-registry/docs/access-control)); prod keeps its own copies so staging cleanup cannot break it.

### 5.6 Application database

The application moves from SQLite to PostgreSQL at the identity milestone, before confidential multi-organization use, to add database-enforced row policies beneath application authorization ([row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)). Modeling and AiiDA keep their own stores. Default (Q3): Cloud SQL for PostgreSQL, one zonal instance per environment, private IP through private services access ([private IP](https://docs.cloud.google.com/sql/docs/postgres/configure-private-ip)), automated backups and point-in-time recovery on; separate databases for `app` and `identity`; separate request, migration, backup and operator roles, with policy-bypassing roles audited. Before that milestone staging may run the SQLite checkpoint for synthetic engineering only; the external pilot uses PostgreSQL, and no permanent dual-engine target exists.

### 5.7 DNS and TLS

Hostnames under a company-owned domain (REQUIRED input), zone managed by Terraform or a documented external operator. TLS terminates at `edge` (default: pinned Caddy, minimal audited configuration, automatic renewal, HTTPS redirect, bounded request size, proxy to `app:8000`), with certificate state on the data disk. The edge strips client-supplied forwarding headers; the application trusts them only from the edge.

## 6. Identities and least privilege

### 6.1 People

Named accounts with MFA, group-based access; the company directory owns membership, with one writer per membership. Product users are application records, never GCP principals or Terraform resources.

| Group | Allowed | Denied |
|---|---|---|
| `engineering-viewers` | Selected resource, log and status viewing | Secret payloads, IAM, writes, prod SSH |
| `staging-operators` | Staging OS Login via IAP, staging operations | Any prod access |
| `prod-operators` | Named prod OS Admin Login via IAP, operations | Routine organization Owner, shared credentials |
| `recovery-operators` | Backup read, isolated restore and cutover | Implicitly opening restored execution |
| Break-glass | Named, audited emergency access | Use without a later Git reconciliation record |

A named platform owner and backup (REQUIRED input) can each operate, revoke access and recover both environments.

### 6.2 CI through OIDC and Workload Identity Federation

GitHub Actions gets short-lived Google credentials through Workload Identity Federation; no service-account keys exist ([WIF for pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)).

- One pool and provider per environment project. Attribute conditions use the numeric `repository_owner_id` and `repository_id` claims (Google warns name-based claims risk squatting), plus `ref`, `event_name`, `environment` and `job_workflow_ref` as each identity requires ([GitHub OIDC](https://docs.github.com/en/actions/reference/security/oidc)).
- Only specific trusted jobs get `id-token: write`. Pull-request jobs are read-only and credential-free. `pull_request_target` never runs untrusted code; untrusted caches never feed publication; credentialed jobs consume hash-verified outputs of the selected trusted build; actions are pinned to full commit SHAs ([secure use](https://docs.github.com/en/actions/reference/security/secure-use)).

| Machine identity | Allowed | Denied |
|---|---|---|
| `product-build` | Push staging images and bundles after trusted tests | Prod, secret payloads, desired state, IAM |
| `staging-publisher` | Write staging desired state | Secret payloads, prod, Terraform |
| `prod-promoter` | Read approved staging artifacts; write prod artifacts and desired state | Secret payloads, product source, IAM |
| `terraform-<env>` | Declared resources in its own project, IAM only where required | Other environment, secret values |
| `ci-verifier` | Read status logs, external HTTPS smoke | Any write |

Terraform identities and host root are privileged trust boundaries (an IAM administrator can grant itself access; root can read secrets). The permission matrix is tested, not inferred from missing bindings.

### 6.3 Runtime

- The VM runs as `hyprn-<env>-runtime` with metadata credentials, no key file ([service accounts](https://docs.cloud.google.com/compute/docs/access/service-accounts)); IAM, not OAuth scopes, carries authorization.
- Allowed: read own registry, artifacts and desired state; access only its named secrets; write logs and metrics; create backup objects. Denied: desired-state writes, IAM, backup deletion, the other environment.
- Only trusted host services use the VM identity. Containers on a shared VM do not get distinct cloud identities; they are denied metadata instead, and the platform does not claim per-container cloud isolation.

### 6.4 Agents

Engineering agents use the same CLI and short-lived identities as engineers: read-only inspect and validate, plan and render showing concrete changes, explicit apply bound to a reviewed plan or artifact; no agent-only privileged path. The agent fleet itself is specified in [`agent-fleet.md`](agent-fleet.md); it holds no authority in staging or prod. The in-app assistant is an application principal acting for a user and has no platform, cloud or host authority.

## 7. Secrets

Google recommends pinned numeric versions over `latest`, and warns that environment variables can leak through logging and that secrets on disk raise the impact of traversal bugs ([best practices](https://docs.cloud.google.com/secret-manager/docs/best-practices)). Product code must stay cloud-neutral for the local edition, so it reads secret file paths; the platform loader fetches through the API and limits the file risk with tmpfs, per-component files, single-file read-only mounts and non-root UIDs.

| Alias | Consumers |
|---|---|
| `modeling-auth` | `app` (including its dispatcher) and `modeling`; distinct value per environment |
| `modeling-rails` | `modeling` only |
| `agent-provider-<provider>` | `app` agent bridge only (agent milestone) |
| `identity-*`, `db-app-*` | `identity`, `app` sign-in client and database roles (identity milestone) |

1. Terraform creates secret resources and per-secret IAM only ([access control](https://docs.cloud.google.com/secret-manager/docs/access-control)). Values are added by an authorized CLI from generated material or a protected input stream, never argv, echo, logs, Git or state. Version pinning is loader policy, since IAM is per secret.
2. The loader runs under the deployment lock, validates environment and alias-to-consumer mapping, fetches with the VM identity and writes `/run/hyprn/secrets/<component>/` files on verified tmpfs with exclusive no-follow creation and the consumer's real UID. Compose `uid/gid/mode` do not remap host file ownership ([Compose secrets](https://docs.docker.com/reference/compose-file/services/#secrets)), so ownership is set and tested on the host. Environment variables may carry a path, never a value; core dumps are disabled for secret-bearing processes.
3. A missing, disabled or wrong-environment secret fails a new start. A transient Secret Manager outage does not restart healthy services holding the approved version. No fallback to another environment or unapproved version.
4. `execution` gets no application secrets; `worker` gets none; `edge` holds only its TLS state.
5. Rotation: new version, reviewed binding change, reconciliation. The modeling protocol uses one shared key, so `app` and `modeling` are drained and recreated together (bind mounts can keep an old inode). The old version stays enabled for the declared rollback window, then is disabled. Incident revocation is an explicit operator procedure, followed by Git reconciliation, and invalidates rollback releases needing the revoked version.
6. Injected secret files are never backed up. Local setup generates local-only credentials; no developer command downloads cloud secrets.

## 8. Delivery pipeline

### 8.1 Flow

```text
product PR → credential-free checks → merge → trusted build and tests on main
  → release descriptor and artifacts in staging stores
  → staging desired-state PR → protected merge → publisher writes manifest → host applies
  → staging qualification record
  → prod promotion PR (same digest) → protected merge
  → promoter copies identical artifacts to prod → publisher writes manifest → host applies
  → prod verification → deliberate admission opening
```

Build once; prod never rebuilds or retags different content. Release pull requests are opened manually at first.

### 8.2 Review and fast feedback

- `main` and production paths require checks, a reviewer other than the author, CODEOWNERS for infrastructure, IAM, host adapter, workflows and prod desired state, stale-approval dismissal, no force push and restricted bypass ([protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)). If the GitHub plan cannot enforce these on private repositories, automated prod promotion stays blocked (Q11).
- A reviewed change-impact map selects checks: UI-only changes run UI and API-boundary checks; application, auth or store changes add API, data and security tests; modeling, native, worker, lock or policy changes run the real scientific and containment suites; platform-only changes run schema, render, IAM and lifecycle checks without rebuilding products. A trusted aggregate job confirms every required check ran; skipped never counts as passed.
- The same scripts run locally and in CI; caches are keyed by lock, target and toolchain and isolated from publication.

### 8.3 Terraform plan and apply

1. On PR: format, validate and static policy checks, no credentials.
2. After code review, a credentialed job saves a binary plan with commit and state identifiers under restricted retention. Terraform code is executable, so plans run only on reviewed code.
3. The plan is reviewed, especially destroy or replace actions on stateful resources.
4. Apply uses exactly that unexpired plan under the environment identity and state lock; changed code or state invalidates it.
5. Scheduled drift detection produces a report and proposed plan, never automatic destructive repair.

Provider versions are constrained and the lock file committed ([providers](https://developer.hashicorp.com/terraform/language/providers)).

### 8.4 Desired-state transport and trust

- The host reads desired state over authenticated HTTPS with its VM identity from a fixed private GCS location set at bootstrap.
- GCS holds create-once `history/<sequence>-<sha>.json` (does-not-exist precondition) and `current.json` (generation-match precondition) ([preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions)). Publication is serialized per environment and rereads Git intent; a late job cannot overwrite a newer sequence; a conflict aborts and re-evaluates. Bytes are read at the generation whose metadata was checked.
- The manifest (≤ 1 MiB, canonical JSON, strict schema) carries environment, project number, installation identity, sequence, release digest, platform commit, config digest, target, artifact inventory, secret references, compatibility requirements and issue time. The host rejects lower sequences and an equal sequence with different bytes.
- **Trust boundary:** TLS and IAM authenticate the channel; hashes bind content. Anyone able to write desired state and supply allowed artifacts is a deployment authority; a compromised authorized publisher is not detected by the host. Initial controls: protected workflows, bucket-scoped IAM, data-access audit logs, environment separation and a periodic trusted comparison of GCS desired bytes with protected Git intent that alerts on mismatch. Independent signing ([Cloud KMS signatures](https://docs.cloud.google.com/kms/docs/create-validate-signatures)) is deferred until supply-chain policy, untrusted mirrors or offline distribution require it.

### 8.5 Promotion, release selection, rollback

- Promotion verifies that staging qualification binds the exact release digest, target, policy and configuration. The qualification record (commits, digests, tests, host identity, attestation, migration and backup IDs, external smoke, approval) is protected from build or PR mutation.
- Release selection is a reviewed edit of `desired.yaml`. Rollback is a new sequence selecting earlier artifacts compatible with the **current** stores' schemas, contracts, secrets and host policy. An incompatible rollback stays in maintenance or read-only mode and proceeds by forward repair. Automated rollback never restores an old database over newer writes.

## 9. Runtime lifecycle

### 9.1 Host services and reconciler

Units: `hyprn-bootstrap-check`, `hyprn-runtime` (Compose), `hyprn-execution` (foreground executor), `hyprn-reconcile` service and timer, `hyprn-backup` service and timer.

- Reconcile every 60 s with jitter and bounded timeouts, never in parallel. Timers and human commands share `/run/hyprn/deployment.lock`; the executor also holds its scientific ownership lock. Lock order: deployment/backup, admission/drain, component locks; child operations inherit the held lock.
- Each pass validates the manifest, compares actual state (digests, config hashes, store and mount identity, UID, capability and network policy, secret versions, native bundle, attestation), prestages verified artifacts and secrets and checks space and migration compatibility without mutating, applies the lifecycle only on real change, then persists the outcome atomically and publishes sanitized status.
- Checkpoints: `verified`, `prestaged`, `draining`, `quiesced`, `backed_up`, `migrating`, `starting`, `qualifying`, `applied`; failures record the last step and whether a migration began. Only transient fetch failures before mutation retry automatically. Unexpected store, mount or security drift closes admission and alerts; only safe stopped-service drift is repaired.
- The adapter stays bounded: one installation per host, fixed components, one serial lifecycle, no plugins, hooks or programmable manifests. If multi-host coordination is ever needed, adopt an established tool instead ([Argo CD](https://argo-cd.readthedocs.io/en/stable/) applies once there is a Kubernetes target). Continuous comparison with actual state follows [OpenGitOps](https://opengitops.dev/).

### 9.2 Bootstrap and first install

1. Validate inputs and caller authority; produce a preflight report without printing credentials.
2. A named bootstrap administrator creates the project, APIs, state bucket, IAM and federation (staging first, prod after staging acceptance). Temporary local state lives outside synced folders, moves to remote state and is confirmed by a no-change plan. Routine bootstrap privilege is then removed.
3. Apply the environment module; install the host adapter, delivery allowlist, firewall, logging and units, which wait closed until a desired state exists.
4. Add secret versions; commit their references.
5. Run `initialize` once on the blank disk with an operator-validated release and installation identity. Admission stays closed until qualification passes.

### 9.3 Lifecycle operations

The product lifecycle CLI returns JSON (`operation_id`, `operation`, `installation_id`, `status`, `reason_code`, `observed_schema_versions`, `evidence_refs`) and exit codes 0 success or no-op, 2 invalid identity or input, 3 incompatible release or schema, 4 admission or drain conflict, 5 failed verification, 6 operator recovery required.

| Operation | Contract |
|---|---|
| `inspect`, `check` | Read-only identity, schema and compatibility checks |
| `initialize` | Blank installation only, atomic; partial initialization needs recovery, never overwrite |
| `admission close/open` | Internal only; opening requires current lifecycle and attestation gates |
| `drain` | Stops new scientific, export, document and agent side-effect admissions; finishes bounded work; reports active and uncertain counts. Default timeout 120 s, after which admission stays closed; never force-kills or redispatches |
| `migrate` | Each owner's ordered migrations once under the exclusive lock, never at service startup; AiiDA through its supported commands |
| `start`, `stop` | Owned units only; never create missing data or reset |
| `qualify` | Exact host containment and contract checks in separate synthetic stores |

Start order: filesystem, network, Docker and firewall; installation and intent; secrets; modeling and app behind closed admission; worker qualification on the exact runtime; executor; admission.

### 9.4 Release application

1. Verify and download without touching the serving release.
2. Close admission; drain scientific, export, document and agent work and in-flight writes. Clients receive HTTP 503 with `Retry-After`; idempotency keys stay valid.
3. If schemas or persistent formats change, stop writers and take a coherent pre-change backup; if consistency cannot be shown, stay closed.
4. Run owner migrations with durable start, completion and checksum records.
5. Start modeling and app behind closed admission; verify mounts, origin, cookies, private authentication, schemas and contracts.
6. Qualify the exact worker, native bundle, launcher and policy in synthetic stores; bind the attestation to the intended runtime.
7. Start the executor, recheck readiness, record the applied generation, open admission.

### 9.5 Backup and recovery objectives

- Daily coordinated backup outside the preferred pilot work window, plus pre-migration backups, under the deployment lock and drain boundary.
- A set covers the application database (SQLite online backup API ([SQLite backup](https://www.sqlite.org/backup.html)) before PostgreSQL; a logical dump at the quiesce point after), modeling primary and required scratch stores, AiiDA database and complete repository taken together ([AiiDA storage](https://aiida.readthedocs.io/projects/aiida-core/en/stable/topics/storage.html)), retained exports, installation and deployment metadata, migration ledger, agent and document intents held in the application store, and edge TLS state if needed.
- Writers are quiesced; live database files are never copied raw. Disk snapshots taken without pausing the application are only crash-consistent ([snapshot best practices](https://docs.cloud.google.com/compute/docs/disks/snapshot-best-practices)) and are not the primary backup.
- Each set has a UUID and canonical manifest (environment, installation and store identities, time, release, config and schema versions, every file's size and hash, recovery tool version). Objects upload with create-only names; the manifest is written last after every object is verified; incomplete sets are not restorable. The write hold ends once the local snapshot is consistent.
- With Cloud SQL, automated backups and point-in-time recovery are a second layer for the database alone; a point-in-time restore always creates a new instance ([Cloud SQL PITR](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/pitr)) and does not by itself prove cross-store consistency.
- Backups hold private data; access is restricted. They never contain injected secrets or credentials. The writer cannot delete or overwrite; lifecycle deletion uses a separate reviewed identity.

| Objective | Proposal | Becomes a commitment when |
|---|---|---|
| RPO | ≤ 24 h | The product owner confirms for real pilot data and a timed drill meets it |
| RTO | ≤ 4 h | Same |
| Retention | 30 daily sets plus active migration recovery points | Data policy and cost confirmed |
| Availability | Host or zone outage stops the environment until restore | The product owner accepts for the pilot |

### 9.6 Restore and drill

1. Declare incident or drill, backup, expected loss window and target. Drills use synthetic records.
2. Provision an isolated recovery host from the same module with execution and admission disabled and no customer DNS. Verify the manifest and every hash.
3. Install the exact compatible release from retained artifacts; restore all stores as one set; fetch approved secret versions separately. Scientific identities are preserved; a new host identity forces requalification.
4. Verify database integrity, app-to-modeling revision references, application-to-AiiDA run associations, source and artifact hashes, results and exports. Reconcile dispatch states conservatively; never rerun uncertain jobs.
5. Run read-only, containment and synthetic checks in separate stores; record measured RPO and RTO.
6. Real recovery fences the old host and its dispatch first, then moves the static IP or DNS, verifies TLS and origin and reopens admission. A drill archives its evidence and removes only its own resources.

After a lost checkpoint or full restore, the host requires a trusted minimum sequence and refuses arbitrary archived manifests. Runbooks cover missing disk, failed secret fetch, revoked key, incompatible migration, stuck drain, corrupt or partial backup, full disk, compromised publisher or host, lost journal, host replacement, certificate renewal failure and lost production access, each with symptoms, read-only diagnosis, safe hold, owned commands, role, evidence and escalation.

## 10. Cloud-edition integrations

### 10.1 Managed-agent bridge

The cloud assistant is an OpenAI or Claude managed agent hosted by the provider; HYPRN MVP executes every tool call itself through its tool registry and in-process API.

- **Outbound only by default.** The custom-tool bridge inside `app` opens outbound HTTPS event streams to the provider. No new public ingress, OAuth server or tunnel; the provider holds no HYPRN MVP credential.
- **Egress allowlist.** Each provider API hostname is a reviewed addition to the `app` allowlist. Since VPC rules cannot tell containers apart, the default host control is an allowlisting forward proxy used only by `app`, with the VPC egress rule as outer bound (Q6). `modeling`, `execution` and `worker` never get provider egress.
- **No public tool endpoint by default.** `/mcp` is not exposed. The remote-MCP fallback, only for a provider that requires it, needs a reviewed public ingress or provider tunnel, short-lived audience-bound tokens and its own security tests (Q14).
- **Secrets and control.** Provider keys reach only the bridge as files. The agent kill switch (new sessions refused, pending proposals blocked, bridge stops answering) is in the operator runbook; per-session and per-user monthly spend ceilings are product-enforced and platform-monitored.
- **Retention and residency.** Transcripts are kept 90 days and provider sessions deleted at the same point. Provider retention, region and residency settings are confirmed before the pilot.
- **Maintenance.** Drain pauses new side-effect admissions; on resume the bridge reconciles saved intents instead of repeating effects.

### 10.2 Sign-in service (proposed)

At the identity milestone managed login replaces local passwords; HYPRN MVP keeps its own sessions, CSRF, organizations, workspaces and memberships. Proposed default (Q4): Keycloak (Apache-2.0) as the `identity` role on the environment host, behind the edge on its own hostname, using its Organizations feature for invitations and SSO. Its development database is not for production; it uses PostgreSQL ([Keycloak databases](https://www.keycloak.org/server/db)), here a separate database and role. The admin console is reachable only through IAP. It joins the backup set, egress policy (only configured upstream identity providers) and secret contract.

### 10.3 Document processing

Source documents stay stored and processed through AiiDA as the product specifies. Any external parser or retrieval provider is a separate reviewed egress and credential change; the parser runs without launcher or provider credentials.

## 11. Observability

- Structured logs (request and operation IDs, environment, component, release, outcome category) to Cloud Logging; metrics to Cloud Monitoring; no separate observability stack.
- Logs never contain passwords, session, CSRF or JWT tokens, secret values, provider prompts, candidate source, raw engineering payloads or private artifact bodies.
- Retention set explicitly: operational logs 30 days, audit logs per data policy. Data-access audit logs on for Secret Manager and the desired-state bucket.
- Four health meanings: liveness, application readiness (stores and schema), execution readiness (current attestation), deployment applied. Public health output is minimal.
- Host status (local JSON via the read-only CLI, also emitted to Logging): installation and host identity, boot ID, desired, applied and failed sequences, digests, component health, drift reasons, admission state, migration status, attestation expiry, backup age.

| Alert (named primary and backup owner) | Threshold |
|---|---|
| External HTTPS down | 3 consecutive failed one-minute uptime checks ([uptime checks](https://docs.cloud.google.com/monitoring/uptime-checks)) |
| Desired/applied mismatch, stale status | > 5 min outside maintenance |
| Invalid attestation, identity or mount drift | Close scientific admission immediately |
| Disk usage | Warn 70%, critical 85%, stop disk-growing admissions at 90% |
| Backup age | Warn 26 h, critical 48 h |
| Certificate | < 14 days or renewal error |
| Agent spend | Session at 80% of ceiling |
| Budget | 50/80/100% |
| Queue age, CPU, memory, failure categories, auth, provider and parser errors | Dashboard; thresholds from staging measurements |

## 12. Security verification

Before prod admission opens, these MUST pass against the real runtime identities:

- Staging principals denied prod resources and secrets; build identity denied secret payloads; modeling denied app-only secrets.
- Effective ingress limited to 80/443 and IAP-range 22 after Docker restart and reboot; egress limited per component.
- Metadata unreachable from every container on all IP families and paths.
- Malicious synthetic candidate cannot reach network, metadata, credentials, sockets, host or sibling paths; CPU, memory, PID, time, output and scratch limits and cleanup hold (worker: network none, read-only root, dropped capabilities, no-new-privileges, UID 65534).
- Missing or disabled secret blocks start; coordinated rotation works; stale mounts detected; reboot reloads secrets; no secret values in logs, inspection or rendered config.
- HTTPS-only origin, Secure and HttpOnly cookies, CSRF and exact-origin checks, CSP, bounded inputs, login rate limits; applicable ASVS Level 1 high controls and API authorization coverage.
- Same- and cross-organization negative tests at API, download, search, export, job, agent and provider-disclosure boundaries.

Stated limits: root, Docker administrators and the host loader are trusted and can reach environment secrets; containers share a kernel; one host is one failure and security domain per environment. Hostile code from untrusted tenants, or a customer need for separate tenant security domains, triggers a threat-model review and stronger isolation first.

## 13. Cost guardrails

- Monthly budget per project (REQUIRED amount) with alerts at 50/80/100%. Alert-only budgets do not cap spending ([budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets)), so bounds come from fixed VM sizes, quotas and product caps.
- Admission caps: 100 pending scientific jobs per environment, 10 per actor, one running at a time initially; rejections return HTTP 429 with `Retry-After` and create no runnable record.
- Agent spend caps per session and per user per month from provider-reported usage.
- No standing third environment; drill resources removed; bounded artifact, backup, log and export retention; labels on every resource for attribution.
- Monthly review of spend, deployment lead time, incidents and platform maintenance hours.

## 14. Capacity

The first hosted release is an invited pilot whose envelope is measured, not inherited. Registered users, concurrent sessions, API writes, running jobs and agent sessions are separate measures. Before opening, run a versioned load scenario sized to the declared cohort plus a login burst and a native job queue test. Proposed acceptance: non-scientific API p95 under 1 s, unexpected 5xx under 1%, no lost or duplicated accepted writes, no authorization leakage, bounded queues, at least 20% memory and disk headroom. Fix measured bottlenecks before changing topology.

## 15. Deferred, with triggers

| Deferred | Trigger |
|---|---|
| High availability, multi-zone, multi-region | A measured availability objective the single host cannot meet |
| Kubernetes, Argo CD | Several runtime targets or a customer Kubernetes estate; containment requalified |
| Cloud Run for the application | Stateless app after PostgreSQL, with execution moved out of the web tier; Cloud Run's ephemeral filesystem contract differs from the host ([container contract](https://docs.cloud.google.com/run/docs/container-contract)) |
| Separate execution host, remote execution | Capacity or isolation need; requires a reviewed remote contract preserving frozen inputs, idempotency and attestation. The stdio bridge is never networked |
| Modeling service on its own host | Product-owner or legal requirement; only the existing HTTP modeling contract crosses hosts |
| Customer-site execution, customer-hosted or disconnected editions | First customer requirement; Terraform does not make cloud services exist on a customer site |
| Fine-grained authorization store | Inherited permissions across organization, workspace, study and document |
| Artifact signing, attestations | Supply-chain policy, untrusted mirrors, offline distribution |
| Shared CI repository, portal, catalog service | Repeated duplication or questions the inventory page cannot answer |
| GPUs, MPI, license-server access for workers | A scoped runtime policy with new attestation; the networkless worker is never silently relaxed |

## 16. Open questions and recommended defaults

| # | Question | Default |
|---|---|---|
| Q1 | Region and residency | `europe-west1` / `europe-west1-b` for both environments |
| Q2 | Billing, organization, project names | Organization `hyprn.ai` and the company billing account exist; one folder per environment; projects `hyprn-staging`, `hyprn-prod` (suffix only if taken) |
| Q3 | Application PostgreSQL hosting | Cloud SQL, zonal, private IP, PITR on, logical dump in the coordinated set; alternative: PostgreSQL container on the data disk |
| Q4 | Sign-in service | Keycloak on the environment host from the identity milestone; alternative: a managed identity product |
| Q5 | Edge arrangement | Direct Caddy edge with static IP; alternative: a provider-operated tunnel. Qualify one, never both |
| Q6 | Agent egress enforcement | Host allowlisting forward proxy for `app`, VPC egress deny-all as outer bound |
| Q7 | Recovery objectives | RPO ≤ 24 h, RTO ≤ 4 h, 30 daily sets, confirmed after a timed drill |
| Q8 | Monthly budgets | REQUIRED amount; alerts 50/80/100% |
| Q9 | Staging schedule | Always on during active delivery; revisit off-hours stopping after pilot opening |
| Q10 | DNS authority | Cloud DNS zone managed by `hyprn-platform` if delegable; otherwise a documented external operator |
| Q11 | GitHub plan | One that enforces protections and environments on private repositories, before automated prod promotion |
| Q12 | Named operators | Platform owner plus one backup in `prod-operators` and `recovery-operators` |
| Q13 | AGPL obligations of the modeling service | Legal review before any commercial cloud launch; internal staging proceeds; a permissive replacement backend is scoped behind the Modeling Backend Contract in parallel |
| Q14 | Remote MCP ingress | Off; enable only for a provider that requires it, after review |
