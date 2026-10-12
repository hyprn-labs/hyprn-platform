# Constraints (from SPECs)

All entries from docs/specs/cloud-platform.md ("Cloud platform specification", status: current specification; MUST = acceptance requirement, Default = initial choice unless a concrete incompatibility is recorded in an ADR, REQUIRED input = value the platform owner supplies). Section numbers refer to that document. Drift between this SPEC and provisioned reality is logged in INGEST-CONFLICTS.md (INFO).

## Scope and non-goals
- source: docs/specs/cloud-platform.md (section 1)
- type: nfr
- content: In scope: two hosted environments `staging` and `prod`, each in its own Google Cloud project; one full-stack host per environment running the fixed workload (`app`, `modeling`, `execution`, `worker`) plus edge proxy and host reconciler; Terraform for infrastructure, reviewed Git and GitHub Actions for delivery, Secret Manager for runtime secrets; explicit product lifecycle on the host (initialize, check, admission, drain, migrate, start/stop, qualify, backup, restore), coordinated multi-store backup and timed restore drill; cloud-edition integrations (outbound access to managed-agent provider, sign-in service, application PostgreSQL). Non-goals: Kubernetes, Argo CD, Cloud Run, service mesh, message broker, developer portal, schema registry, generic workload framework; HA, multi-zone/multi-region serving, autoscaling; remote or customer-site scientific execution; migration of old local/dev run data (cloud stores start empty); a standing third cloud environment (development uses the local edition); product code in `hyprn-platform`; Google Cloud SDK calls inside product code.

## Product constraints the platform preserves
- source: docs/specs/cloud-platform.md (section 2)
- type: nfr
- content: One cohesive `app` owns API, authorization and records; all clients (UI, agents, MCP) use the HYPRN MVP API; the agent bridge runs inside `app`. `modeling` (patched WhatsOpt, GNU AGPL v3) has no public listener, no application or AiiDA store, no execution authority, no provider or cloud credentials; its source notices ship with every release; network separation is not a licensing conclusion and legal review gates commercial launch (Q13; `docs/legal/licensing.md` in hyprn-mvp). Preparation never executes candidate code; `worker` is networkless, credential-free and bounded; a changed host image, kernel, Docker, launcher or policy invalidates the attestation and requires requalification on the actual host. AiiDA owns scientific processes/artifacts, OpenMDAO numerics; no cloud resource per run; trusted `execution` host service owns AiiDA state and Docker launch authority. Exact pins; missing output is never zero; uncertain jobs never redispatched (drain, restore, reconciliation never reset, re-run or invent results). Local-first editions: `editions/local/` now, `editions/cloud/` later, chosen by the installation configuration's `edition` field; product code reads configuration and secret file paths, cloud retrieval lives in the platform host adapter. Studies archived, never deleted; complete backup sets; deletion-protected production data; no destructive maintenance without its own reviewed procedure.

## Environments and authority separation
- source: docs/specs/cloud-platform.md (section 3)
- type: nfr
- content: Environments `local` (developer machine, never copied to cloud), `staging` (project `hyprn-staging-<suffix>` in the SPEC text; synthetic data only; qualification of exactly the release later promoted), `prod` (project `hyprn-prod-<suffix>` in the SPEC text; invited pilot then hosted product; pilot and customer data). Staging and prod never share a project, host, disk, database, bucket, secret, service account, Terraform state or scientific identity; "staging cannot touch prod" is an IAM property tested with negative checks. Each environment has its own Terraform root and state bucket; Terraform workspaces are not an access boundary. Production data is never restored into staging; restore drills use a temporary isolated host.

## Repository ownership
- source: docs/specs/cloud-platform.md (section 4.1)
- type: protocol
- content: `hyprn-mvp` owns application, UI, integration (AiiDA bridge, launcher, worker), modeling patches and notices, contracts, product Compose topology, lifecycle CLI, image build contexts, locks, editions, product ADRs; it does not own cloud resources and identities, environment bindings, or which release runs where. `hyprn-platform` owns Terraform (bootstrap, staging, prod), cloud and CI identities, repository governance, the deployment schema set, naming rules, host adapter (renderer, reconciler, secret loader, systemd units, firewall), environment bindings and desired releases, runbooks, inventory, platform ADRs; it does not own scientific and API contracts, database schemas, images. Each effective field has one owner; Terraform owns cloud resources, the reconciler owns the rendered runtime on the host; neither rewrites the other. Each repository keeps MADR decisions under `docs/adr/`.

## Workload contract hyprn-workload/v1
- source: docs/specs/cloud-platform.md (section 4.2)
- type: schema
- content: Schema set in `hyprn-platform/contracts/v1/`; product CI pins it by platform commit and file hashes. Declares `product: hyprn-mvp` and exactly four components. `app`: OCI image, data role application, secret aliases `modeling-auth` (later only reviewed agent, identity and database aliases), application behind the edge. `modeling` (implementation `whatsopt`): OCI image, data role modeling, aliases `modeling-auth`, `modeling-rails`, private, no public port. `execution`: native bundle installed on the host, data role execution, no secrets, trusted host service with Docker authority. `worker`: OCI image, ephemeral, no secrets ever, restricted scientific job. Platform-owned infrastructure roles: `edge` (TLS proxy), `reconciler` (host adapter and secret loader), and from the identity milestone `identity`.

## Workload contract validation
- source: docs/specs/cloud-platform.md (section 4.2)
- type: schema
- content: Safe parsing, then schema and semantic checks. Rejects unknown fields, duplicate keys, executable YAML tags, unpinned images, unsupported versions, secret aliases without bindings, cross-environment references and any widening of secrets, mounts, capabilities or network. Allowed sets change only through platform review. Product Compose owns commands, ports and internal topology; the platform renderer supplies images, roots, UIDs, resource profiles, secret mounts and exposure from one validated binding and checks effective output against policy. Rendered preview never shows secret values. Golden fixtures prove stable rendering; negative fixtures prove unsafe input fails.

## Release descriptor v1
- source: docs/specs/cloud-platform.md (section 4.3)
- type: schema
- content: A release is the complete compatible artifact set built once from one product commit. Descriptor v1 is canonical JSON containing: schema, product, full source commit and source-inventory hash; workload contract digest and product contract versions; targets (`linux/amd64` mandatory); OCI digests for `app`, `modeling`, `worker`, native bundle hash and size, UI asset manifest hash; build inputs (toolchain, base images, upstream sources, patches, locks); per-owner migrations (ordered IDs and checksums, readable range, writable version, rollback compatibility, backup requirement); execution identities (worker, launcher, evaluator, policy, native hashes, attestation format); evidence digests (tests, provenance, SBOM, licence and source notices). Descriptor digest plus target identifies the release. Deployment input is always a digest, never a tag. Bundles are size- and hash-verified and rejected if they contain absolute paths or `..` segments, escaping links, device files, duplicates or unbounded expansion.

## Environment binding and desired state
- source: docs/specs/cloud-platform.md (section 4.4)
- type: schema
- content: `environments/<env>/runtime.yaml` holds physical bindings: project, zone, host identity, external origin, registry and bucket bindings, data-disk identity, resource profile, allowed secret aliases with numeric versions, observability and recovery settings; no passwords, no shell. `environments/<env>/desired.yaml` (`hyprn-desired/v1`) holds environment, monotonically increasing sequence, release digest, target, rendered-config digest, platform adapter version and digest, maintenance policy and qualification references. Every change, including config-only changes and rollbacks, takes a new sequence.

## Naming
- source: docs/specs/cloud-platform.md (section 4.5)
- type: protocol
- content: Company namespace `hyprn` for platform resources; each hosted product keeps its own codename (`hyprn-mvp` first); environments `local`, `staging`, `prod` only; never an architecture style, person or partner in durable identities. Physical names `hyprn-<env>-<role>[-<instance>]` (for example `hyprn-prod-host-01`, `hyprn-staging-backup`); purpose-named service accounts (`hyprn-prod-runtime`, `hyprn-prod-terraform`); secret alias `modeling-auth` maps to `hyprn-<env>-modeling-auth` at a pinned version. Labels `product`, `environment`, `component`, `owner`, `managed_by`. Helpers validate each resource type's name rules; globally unique project and bucket suffixes are explicit bindings; names never grant authority, encode tenancy or contain personal data; renames use state move or import. Product name in prose is HYPRN MVP; technical identifiers use `hyprn-mvp` and the `HYPRN_MVP_` environment prefix.

## Projects, region, APIs
- source: docs/specs/cloud-platform.md (section 5.1)
- type: nfr
- content: One project per environment under the company billing account and organization or folder (REQUIRED input). Default region `europe-west1`, zone `europe-west1-b`, `linux/amd64` in both environments. Explicitly enabled APIs: Compute Engine, Artifact Registry, Secret Manager, IAM, IAM Credentials, Security Token Service, Resource Manager, Service Usage, Cloud Storage, Logging, Monitoring, IAP, OS Login; Cloud SQL Admin and Service Networking from the PostgreSQL milestone; Cloud DNS and Billing Budgets only where Terraform manages those resources. Google-managed encryption at rest; no application signing key initially.

## Network
- source: docs/specs/cloud-platform.md (section 5.2)
- type: nfr
- content: One custom VPC and subnet per environment; no default network. Ingress: TCP 80/443 to the host's static IP; TCP 22 only from IAP range `35.235.240.0/20`; application, modeling, databases, metrics and Docker API have no public listener. Egress enforced twice: VPC deny-all egress with explicit allows for Google APIs and approved endpoints, plus host rules per container network; `worker` uses Docker network `none`; `modeling` reaches only `app`; `app` reaches `modeling`, the database and an allowlist of named endpoints; each new endpoint is a reviewed platform change. Host pins one firewall backend, enforces rules on the forwarding path and verifies effective rules after Docker restart and reboot (Docker diverts published-port traffic before ordinary host firewall chains). Metadata MUST be denied to every container (`169.254.169.254`, `metadata.google.internal`, IPv6 address where enabled, alternate paths), verified by tests; only trusted host services use the VM identity.

## Host
- source: docs/specs/cloud-platform.md (section 5.3)
- type: nfr
- content: One VM per environment. Initial profiles: staging `e2-standard-4` (4 vCPU, 16 GiB), prod `e2-standard-8` (8 vCPU, 32 GiB), 30 GiB boot disk, no GPU; starting measurements, not capacity claims. Debian 12 pinned image; Python 3.12 comes from a pinned, hashed distribution inside the native bundle, never from the OS. Bootstrap through pinned cloud-init or a reviewed image (not the deprecated container startup agent); installs platform prerequisites only. Docker Compose runs `edge`, `app`, `modeling` (later `identity`); systemd runs trusted host services; containers use `restart: no`; systemd restarts only validated units with bounded backoff. Admin SSH only through OS Login and IAP; project-wide SSH keys blocked. Prod VM deletion protection on. Host layout: `/etc/hyprn/` (root-owned config, delivery allowlist, host identity), `/opt/hyprn/releases/<digest>/`, `/opt/hyprn/platform/<version>/`, `/srv/hyprn/<env>/` (persistent disk: identity.json, application/, modeling/, execution/, edge/, deployment/, backup-staging/), `/run/hyprn/` (tmpfs locks and per-component secret files).

## Persistent data disk
- source: docs/specs/cloud-platform.md (section 5.4)
- type: nfr
- content: Separate balanced persistent disk holds all mutable data: 100 GiB staging, 200 GiB prod initially, with per-area quotas. Auto-delete disabled; Terraform `prevent_destroy` on prod (does not survive deleting the resource block, so destructive diffs are also caught in plan review and IAM). `identity.json`, written once at initialization, records disk UUID, environment, project, installation ID, store IDs and AiiDA profile and repository identities; missing mount, changed identity or unexpected pre-existing directory refuses startup; only `initialize` may format, and only the exact Terraform-created blank device. One writer at a time: host replacement fences the old executor, moves the disk to exactly one new host and verifies identity before requalification. A zonal disk is not regional availability.

## Buckets and registry
- source: docs/specs/cloud-platform.md (section 5.5)
- type: nfr
- content: All buckets enforce public access prevention and uniform bucket-level access. Per environment: `hyprn-<env>-tfstate` (writer environment Terraform identity; versioning on; GCS backend locking), `hyprn-<env>-artifacts` (writer build for staging or promoter for prod; reader runtime; active release plus two rollback-compatible releases, 30-day floor), `hyprn-<env>-desired` (writer environment publisher only; reader runtime read-only; create-once history plus `current.json`), `hyprn-<env>-backup` (writer runtime create-only; reader recovery operator; 30 daily complete sets plus migration recovery points). Soft delete (7 days default, up to 90) stays on for desired-state and backup buckets. Retention locks never applied irreversibly without owner authorization. One Artifact Registry Docker repository per environment, IAM at repository scope; prod keeps its own copies.

## Application database
- source: docs/specs/cloud-platform.md (section 5.6)
- type: schema
- content: Application moves from SQLite to PostgreSQL at the identity milestone, before confidential multi-organization use, for database-enforced row policies beneath application authorization. Modeling and AiiDA keep their own stores. Default (Q3): Cloud SQL for PostgreSQL, one zonal instance per environment, private IP via private services access, automated backups and PITR on; separate databases for `app` and `identity`; separate request, migration, backup and operator roles; policy-bypassing roles audited. Before that milestone staging may run the SQLite checkpoint for synthetic engineering only; the external pilot uses PostgreSQL; no permanent dual-engine target.

## DNS and TLS
- source: docs/specs/cloud-platform.md (section 5.7)
- type: nfr
- content: Hostnames under a company-owned domain (REQUIRED input); zone managed by Terraform or a documented external operator. TLS terminates at `edge` (default pinned Caddy, minimal audited configuration, automatic renewal, HTTPS redirect, bounded request size, proxy to `app:8000`), certificate state on the data disk. Edge strips client-supplied forwarding headers; the application trusts them only from the edge.

## People and access groups
- source: docs/specs/cloud-platform.md (section 6.1)
- type: nfr
- content: Named accounts with MFA, group-based access; company directory owns membership (one writer per membership); product users are application records, never GCP principals or Terraform resources. Groups: `engineering-viewers` (selected viewing; denied secret payloads, IAM, writes, prod SSH), `staging-operators` (staging OS Login via IAP and operations; denied any prod access), `prod-operators` (named prod OS Admin Login via IAP; denied routine organization Owner, shared credentials), `recovery-operators` (backup read, isolated restore, cutover; denied implicitly opening restored execution), break-glass (named, audited; denied use without a later Git reconciliation record). A named platform owner and backup (REQUIRED input) can each operate, revoke access and recover both environments.

## CI identity through OIDC and Workload Identity Federation
- source: docs/specs/cloud-platform.md (section 6.2)
- type: protocol
- content: GitHub Actions gets short-lived Google credentials through WIF; no service-account keys exist. One pool and provider per environment project. Attribute conditions use numeric `repository_owner_id` and `repository_id` claims plus `ref`, `event_name`, `environment` and `job_workflow_ref` as each identity requires. Only specific trusted jobs get `id-token: write`; pull-request jobs are read-only and credential-free; `pull_request_target` never runs untrusted code; untrusted caches never feed publication; credentialed jobs consume hash-verified outputs of the selected trusted build; actions pinned to full commit SHAs. Machine identities: `product-build` (push staging images and bundles after trusted tests; denied prod, secret payloads, desired state, IAM), `staging-publisher` (write staging desired state; denied secret payloads, prod, Terraform), `prod-promoter` (read approved staging artifacts, write prod artifacts and desired state; denied secret payloads, product source, IAM), `terraform-<env>` (declared resources in own project, IAM only where required; denied other environment, secret values), `ci-verifier` (read status logs, external HTTPS smoke; no writes). Terraform identities and host root are privileged trust boundaries; the permission matrix is tested, not inferred from missing bindings.

## Runtime identity
- source: docs/specs/cloud-platform.md (section 6.3)
- type: nfr
- content: VM runs as `hyprn-<env>-runtime` with metadata credentials, no key file; IAM, not OAuth scopes, carries authorization. Allowed: read own registry, artifacts and desired state; access only its named secrets; write logs and metrics; create backup objects. Denied: desired-state writes, IAM, backup deletion, the other environment. Only trusted host services use the VM identity; containers get no distinct cloud identities and are denied metadata; no per-container cloud isolation claim.

## Agents (platform authority)
- source: docs/specs/cloud-platform.md (section 6.4)
- type: nfr
- content: Engineering agents use the same CLI and short-lived identities as engineers: read-only inspect and validate, plan and render showing concrete changes, explicit apply bound to a reviewed plan or artifact; no agent-only privileged path. The in-app assistant is an application principal acting for a user and has no platform, cloud or host authority.

## Secret aliases
- source: docs/specs/cloud-platform.md (section 7)
- type: schema
- content: `modeling-auth`: consumers `app` (including its dispatcher) and `modeling`, distinct value per environment. `modeling-rails`: `modeling` only. `agent-provider-<provider>`: `app` agent bridge only (agent milestone). `identity-*`, `db-app-*`: `identity`, `app` sign-in client and database roles (identity milestone).

## Secret handling rules
- source: docs/specs/cloud-platform.md (section 7)
- type: protocol
- content: Pinned numeric versions over `latest`. (1) Terraform creates secret resources and per-secret IAM only; values added by an authorized CLI from generated material or protected input stream, never argv, echo, logs, Git or state; version pinning is loader policy. (2) Loader runs under the deployment lock, validates environment and alias-to-consumer mapping, fetches with the VM identity, writes `/run/hyprn/secrets/<component>/` files on verified tmpfs with exclusive no-follow creation and the consumer's real UID; env vars may carry a path, never a value; core dumps disabled for secret-bearing processes. (3) Missing, disabled or wrong-environment secret fails a new start; transient Secret Manager outage does not restart healthy services; no fallback to another environment or unapproved version. (4) `execution` and `worker` get no application secrets; `edge` holds only TLS state. (5) Rotation: new version, reviewed binding change, reconciliation; `app` and `modeling` drained and recreated together; old version stays enabled for the declared rollback window then disabled; incident revocation is an explicit operator procedure followed by Git reconciliation and invalidates rollback releases needing the revoked version. (6) Injected secret files never backed up; local setup generates local-only credentials; no developer command downloads cloud secrets.

## Delivery flow
- source: docs/specs/cloud-platform.md (section 8.1)
- type: protocol
- content: product PR -> credential-free checks -> merge -> trusted build and tests on main -> release descriptor and artifacts in staging stores -> staging desired-state PR -> protected merge -> publisher writes manifest -> host applies -> staging qualification record -> prod promotion PR (same digest) -> protected merge -> promoter copies identical artifacts to prod -> publisher writes manifest -> host applies -> prod verification -> deliberate admission opening. Build once; prod never rebuilds or retags different content. Release PRs opened manually at first.

## Review gates and fast feedback
- source: docs/specs/cloud-platform.md (section 8.2)
- type: nfr
- content: `main` and production paths require checks, a reviewer other than the author, CODEOWNERS for infrastructure, IAM, host adapter, workflows and prod desired state, stale-approval dismissal, no force push, restricted bypass. If the GitHub plan cannot enforce these on private repositories, automated prod promotion stays blocked (Q11). Reviewed change-impact map selects checks (UI-only, application/auth/store, modeling/native/worker/lock/policy, platform-only); a trusted aggregate job confirms every required check ran; skipped never counts as passed. Same scripts run locally and in CI; caches keyed by lock, target and toolchain and isolated from publication.

## Terraform plan and apply
- source: docs/specs/cloud-platform.md (section 8.3)
- type: protocol
- content: (1) On PR: format, validate, static policy checks, no credentials. (2) After code review a credentialed job saves a binary plan with commit and state identifiers under restricted retention; plans run only on reviewed code. (3) Plan reviewed, especially destroy/replace on stateful resources. (4) Apply uses exactly that unexpired plan under the environment identity and state lock; changed code or state invalidates it. (5) Scheduled drift detection produces a report and proposed plan, never automatic destructive repair. Provider versions constrained, lock file committed.

## Desired-state transport and trust
- source: docs/specs/cloud-platform.md (section 8.4)
- type: protocol
- content: Host reads desired state over authenticated HTTPS with its VM identity from a fixed private GCS location set at bootstrap. GCS holds create-once `history/<sequence>-<sha>.json` (does-not-exist precondition) and `current.json` (generation-match precondition); publication serialized per environment, rereads Git intent, a late job cannot overwrite a newer sequence, conflict aborts and re-evaluates; bytes read at the generation whose metadata was checked. Manifest (<= 1 MiB, canonical JSON, strict schema) carries environment, project number, installation identity, sequence, release digest, platform commit, config digest, target, artifact inventory, secret references, compatibility requirements, issue time; host rejects lower sequences and an equal sequence with different bytes. Trust boundary: TLS and IAM authenticate the channel, hashes bind content; anyone able to write desired state and supply allowed artifacts is a deployment authority; initial controls: protected workflows, bucket-scoped IAM, data-access audit logs, environment separation, periodic trusted comparison of GCS desired bytes with protected Git intent alerting on mismatch. Independent signing (Cloud KMS) deferred.

## Promotion, release selection, rollback
- source: docs/specs/cloud-platform.md (section 8.5)
- type: protocol
- content: Promotion verifies staging qualification binds the exact release digest, target, policy and configuration; the qualification record (commits, digests, tests, host identity, attestation, migration and backup IDs, external smoke, approval) is protected from build or PR mutation. Release selection is a reviewed edit of `desired.yaml`. Rollback is a new sequence selecting earlier artifacts compatible with the current stores' schemas, contracts, secrets and host policy; an incompatible rollback stays in maintenance or read-only mode and proceeds by forward repair; automated rollback never restores an old database over newer writes.

## Host services and reconciler
- source: docs/specs/cloud-platform.md (section 9.1)
- type: protocol
- content: Units `hyprn-bootstrap-check`, `hyprn-runtime` (Compose), `hyprn-execution` (foreground executor), `hyprn-reconcile` service and timer, `hyprn-backup` service and timer. Reconcile every 60 s with jitter and bounded timeouts, never in parallel; timers and human commands share `/run/hyprn/deployment.lock`; lock order: deployment/backup, admission/drain, component locks. Each pass validates the manifest, compares actual state, prestages verified artifacts and secrets, applies lifecycle only on real change, persists the outcome atomically, publishes sanitized status. Checkpoints `verified`, `prestaged`, `draining`, `quiesced`, `backed_up`, `migrating`, `starting`, `qualifying`, `applied`; only transient fetch failures before mutation retry automatically; unexpected store, mount or security drift closes admission and alerts. Adapter bounded: one installation per host, fixed components, one serial lifecycle, no plugins, hooks or programmable manifests; multi-host coordination means adopting an established tool.

## Bootstrap and first install
- source: docs/specs/cloud-platform.md (section 9.2)
- type: protocol
- content: (1) Validate inputs and caller authority; preflight report without printing credentials. (2) Named bootstrap administrator creates project, APIs, state bucket, IAM and federation (staging first, prod after staging acceptance); temporary local state outside synced folders moves to remote state and is confirmed by a no-change plan; routine bootstrap privilege then removed. (3) Apply environment module; install host adapter, delivery allowlist, firewall, logging and units, which wait closed until a desired state exists. (4) Add secret versions; commit references. (5) Run `initialize` once on the blank disk with an operator-validated release and installation identity; admission stays closed until qualification passes.

## Lifecycle CLI contract
- source: docs/specs/cloud-platform.md (section 9.3)
- type: api-contract
- content: Product lifecycle CLI returns JSON (`operation_id`, `operation`, `installation_id`, `status`, `reason_code`, `observed_schema_versions`, `evidence_refs`); exit codes 0 success or no-op, 2 invalid identity or input, 3 incompatible release or schema, 4 admission or drain conflict, 5 failed verification, 6 operator recovery required. Operations: `inspect`/`check` (read-only); `initialize` (blank installation only, atomic, never overwrite); `admission close/open` (internal only, opening requires current lifecycle and attestation gates); `drain` (stops new scientific, export, document and agent side-effect admissions, default timeout 120 s then admission stays closed, never force-kills or redispatches); `migrate` (each owner's ordered migrations once under exclusive lock, never at service startup); `start`/`stop` (owned units only, never create missing data or reset); `qualify` (exact host containment and contract checks in separate synthetic stores). Start order: filesystem, network, Docker and firewall; installation and intent; secrets; modeling and app behind closed admission; worker qualification on the exact runtime; executor; admission.

## Release application sequence
- source: docs/specs/cloud-platform.md (section 9.4)
- type: protocol
- content: (1) Verify and download without touching the serving release. (2) Close admission; drain scientific, export, document and agent work and in-flight writes; clients get HTTP 503 with `Retry-After`; idempotency keys stay valid. (3) If schemas or persistent formats change, stop writers and take a coherent pre-change backup; if consistency cannot be shown, stay closed. (4) Run owner migrations with durable start, completion and checksum records. (5) Start modeling and app behind closed admission; verify mounts, origin, cookies, private authentication, schemas, contracts. (6) Qualify exact worker, native bundle, launcher and policy in synthetic stores; bind attestation to intended runtime. (7) Start executor, recheck readiness, record applied generation, open admission.

## Backup and recovery objectives
- source: docs/specs/cloud-platform.md (section 9.5)
- type: nfr
- content: Daily coordinated backup outside the preferred pilot work window plus pre-migration backups, under the deployment lock and drain boundary. A set covers application database (SQLite online backup API, then PostgreSQL logical dump at quiesce), modeling primary and required scratch stores, AiiDA database and complete repository taken together, retained exports, installation and deployment metadata, migration ledger, agent and document intents, edge TLS state if needed. Writers quiesced; live database files never copied raw; disk snapshots without pausing the application are crash-consistent only and not the primary backup. Each set has a UUID and canonical manifest (environment, installation and store identities, time, release, config and schema versions, every file's size and hash, recovery tool version); create-only uploads; manifest written last; incomplete sets not restorable. Cloud SQL PITR is a second layer for the database alone and always creates a new instance. Backups never contain injected secrets or credentials; writer cannot delete or overwrite. Proposed objectives (become commitments when stated conditions met): RPO <= 24 h, RTO <= 4 h, retention 30 daily sets plus active migration recovery points, availability: host or zone outage stops the environment until restore.

## Restore and drill
- source: docs/specs/cloud-platform.md (section 9.6)
- type: protocol
- content: (1) Declare incident or drill, backup, expected loss window and target; drills use synthetic records. (2) Provision isolated recovery host from the same module with execution and admission disabled and no customer DNS; verify manifest and every hash. (3) Install exact compatible release from retained artifacts; restore all stores as one set; fetch approved secret versions separately; new host identity forces requalification. (4) Verify database integrity, app-to-modeling revision references, application-to-AiiDA run associations, source and artifact hashes, results, exports; reconcile dispatch states conservatively, never rerun uncertain jobs. (5) Run read-only, containment and synthetic checks in separate stores; record measured RPO and RTO. (6) Real recovery fences the old host and its dispatch first, then moves static IP or DNS, verifies TLS and origin, reopens admission; a drill archives evidence and removes only its own resources. After a lost checkpoint or full restore the host requires a trusted minimum sequence. Runbooks required for: missing disk, failed secret fetch, revoked key, incompatible migration, stuck drain, corrupt or partial backup, full disk, compromised publisher or host, lost journal, host replacement, certificate renewal failure, lost production access.

## Managed-agent bridge
- source: docs/specs/cloud-platform.md (section 10.1)
- type: protocol
- content: Cloud assistant is an OpenAI or Claude managed agent hosted by the provider; HYPRN MVP executes every tool call itself. Outbound only by default: the custom-tool bridge inside `app` opens outbound HTTPS event streams; no new public ingress, OAuth server or tunnel; provider holds no HYPRN MVP credential. Each provider API hostname is a reviewed addition to the `app` allowlist; default host control is an allowlisting forward proxy used only by `app` with the VPC egress rule as outer bound (Q6); `modeling`, `execution`, `worker` never get provider egress. `/mcp` not exposed by default; remote-MCP fallback needs reviewed public ingress or provider tunnel, short-lived audience-bound tokens and its own security tests (Q14). Provider keys reach only the bridge as files. Agent kill switch in the operator runbook; per-session and per-user monthly spend ceilings product-enforced and platform-monitored. Transcripts kept 90 days and provider sessions deleted at the same point; provider retention, region and residency confirmed before the pilot. Drain pauses new side-effect admissions; on resume the bridge reconciles saved intents.

## Sign-in service (proposed)
- source: docs/specs/cloud-platform.md (section 10.2)
- type: protocol
- content: Status proposed (Q4). At the identity milestone managed login replaces local passwords; HYPRN MVP keeps its own sessions, CSRF, organizations, workspaces and memberships. Proposed default: Keycloak (Apache-2.0) as `identity` role on the environment host behind the edge on its own hostname, using its Organizations feature; production uses PostgreSQL (separate database and role), not the development database; admin console reachable only through IAP; joins the backup set, egress policy (only configured upstream identity providers) and secret contract. Alternative: a managed identity product.

## Document processing
- source: docs/specs/cloud-platform.md (section 10.3)
- type: protocol
- content: Source documents stay stored and processed through AiiDA. Any external parser or retrieval provider is a separate reviewed egress and credential change; the parser runs without launcher or provider credentials.

## Observability and alerting
- source: docs/specs/cloud-platform.md (section 11)
- type: nfr
- content: Structured logs (request and operation IDs, environment, component, release, outcome category) to Cloud Logging; metrics to Cloud Monitoring; no separate observability stack. Logs never contain passwords, session, CSRF or JWT tokens, secret values, provider prompts, candidate source, raw engineering payloads or private artifact bodies. Retention explicit: operational logs 30 days, audit logs per data policy; data-access audit logs on for Secret Manager and the desired-state bucket. Four health meanings: liveness, application readiness, execution readiness (current attestation), deployment applied; public health output minimal. Host status via read-only CLI (also to Logging). Alerts (named primary and backup owner): external HTTPS down = 3 consecutive failed one-minute uptime checks; desired/applied mismatch or stale status > 5 min outside maintenance; invalid attestation, identity or mount drift closes scientific admission immediately; disk usage warn 70 %, critical 85 %, stop disk-growing admissions at 90 %; backup age warn 26 h, critical 48 h; certificate < 14 days or renewal error; agent spend session at 80 % of ceiling; budget 50/80/100 %; queue age, CPU, memory, failure categories, auth, provider and parser errors on dashboard with thresholds from staging measurements.

## Security verification before prod admission
- source: docs/specs/cloud-platform.md (section 12)
- type: nfr
- content: These MUST pass against the real runtime identities before prod admission opens: staging principals denied prod resources and secrets, build identity denied secret payloads, modeling denied app-only secrets; effective ingress limited to 80/443 and IAP-range 22 after Docker restart and reboot, egress limited per component; metadata unreachable from every container on all IP families and paths; malicious synthetic candidate cannot reach network, metadata, credentials, sockets, host or sibling paths, with CPU, memory, PID, time, output and scratch limits and cleanup holding (worker: network none, read-only root, dropped capabilities, no-new-privileges, UID 65534); missing or disabled secret blocks start, coordinated rotation works, stale mounts detected, reboot reloads secrets, no secret values in logs, inspection or rendered config; HTTPS-only origin, Secure and HttpOnly cookies, CSRF and exact-origin checks, CSP, bounded inputs, login rate limits, applicable ASVS Level 1 high controls and API authorization coverage; same- and cross-organization negative tests at API, download, search, export, job, agent and provider-disclosure boundaries. Stated limits: root, Docker administrators and the host loader are trusted; containers share a kernel; one host is one failure and security domain per environment; hostile code from untrusted tenants triggers threat-model review first.

## Cost guardrails
- source: docs/specs/cloud-platform.md (section 13)
- type: nfr
- content: Monthly budget per project (REQUIRED amount) with alerts at 50/80/100 %; alert-only budgets do not cap spending, so bounds come from fixed VM sizes, quotas and product caps. Admission caps: 100 pending scientific jobs per environment, 10 per actor, one running at a time initially; rejections return HTTP 429 with `Retry-After` and create no runnable record. Agent spend caps per session and per user per month. No standing third environment; drill resources removed; bounded artifact, backup, log and export retention; labels on every resource; monthly review of spend, deployment lead time, incidents and platform maintenance hours.

## Capacity
- source: docs/specs/cloud-platform.md (section 14)
- type: nfr
- content: First hosted release is an invited pilot whose envelope is measured, not inherited; registered users, concurrent sessions, API writes, running jobs and agent sessions are separate measures. Before opening, run a versioned load scenario sized to the declared cohort plus a login burst and a native job queue test. Proposed acceptance: non-scientific API p95 under 1 s, unexpected 5xx under 1 %, no lost or duplicated accepted writes, no authorization leakage, bounded queues, at least 20 % memory and disk headroom. Fix measured bottlenecks before changing topology.

## Deferred items and triggers
- source: docs/specs/cloud-platform.md (section 15)
- type: nfr
- content: High availability, multi-zone, multi-region (trigger: measured availability objective the single host cannot meet); Kubernetes, Argo CD (several runtime targets or customer Kubernetes estate; containment requalified); Cloud Run for the application (stateless app after PostgreSQL, execution moved out of web tier); separate execution host or remote execution (capacity or isolation need; reviewed remote contract; stdio bridge never networked); modeling service on its own host (product-owner or legal requirement); customer-site execution and customer-hosted or disconnected editions (first customer requirement); fine-grained authorization store; artifact signing and attestations (supply-chain policy, untrusted mirrors, offline distribution); shared CI repository, portal, catalog service; GPUs, MPI, license-server access for workers (scoped runtime policy with new attestation; the networkless worker never silently relaxed).

## Open questions and recommended defaults (Q1-Q14)
- source: docs/specs/cloud-platform.md (section 16)
- type: nfr
- content: Q1 region and residency: `europe-west1` / `europe-west1-b` for both environments. Q2 billing, organization, project suffixes: company organization with a `hyprn` folder; `hyprn-staging-<suffix>`, `hyprn-prod-<suffix>`. Q3 application PostgreSQL: Cloud SQL, zonal, private IP, PITR on, logical dump in the coordinated set; alternative PostgreSQL container on the data disk. Q4 sign-in: Keycloak on the environment host from the identity milestone; alternative managed identity product. Q5 edge: direct Caddy edge with static IP; alternative provider-operated tunnel; qualify one, never both. Q6 agent egress: host allowlisting forward proxy for `app`, VPC egress deny-all as outer bound. Q7 recovery objectives: RPO <= 24 h, RTO <= 4 h, 30 daily sets, confirmed after a timed drill. Q8 monthly budgets: REQUIRED amount; alerts 50/80/100 %. Q9 staging schedule: always on during active delivery; revisit off-hours stopping after pilot opening. Q10 DNS authority: Cloud DNS zone managed by `hyprn-platform` if delegable, otherwise a documented external operator. Q11 GitHub plan: one that enforces protections and environments on private repositories, before automated prod promotion. Q12 named operators: platform owner plus one backup in `prod-operators` and `recovery-operators`. Q13 AGPL obligations of the modeling service: legal review before any commercial cloud launch; internal staging proceeds; permissive replacement backend scoped in parallel. Q14 remote MCP ingress: off; enable only for a provider that requires it, after review.
