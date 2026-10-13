---
last_mapped_commit: a393bda2510b521148d626a02e4a5aef58dae1d6
last_mapped_at: 2026-10-13
---

<!-- refreshed: 2026-10-13 -->
# Architecture

**Analysis Date:** 2026-10-13

## System Overview

`hyprn-platform` is a spec-driven infrastructure repository, not a running
application. Terraform owns cloud resources; a host adapter owns the rendered
runtime on each host; neither rewrites the other. Two specifications govern
everything: product hosting (`docs/specs/cloud-platform.md`) and the agent
fleet (`docs/specs/agent-fleet.md`).

```text
┌─────────────────────────────────────────────────────────────┐
│              Specifications & Decisions (intent)              │
│  `docs/specs/cloud-platform.md`  `docs/specs/agent-fleet.md` │
│  `docs/adr/`  `conventions/`  `catalog/`  `governance/`      │
├──────────────────┬──────────────────┬───────────────────────┤
│  Org baseline    │  Agent fleet     │  Product hosting      │
│  `bootstrap/`    │  `infra/agents/` │  `infra/modules/`     │
│                  │  `agents/`       │  `infra/environments/` │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Deployment contract (binding layer)              │
│  `contracts/v1/`  +  `environments/<env>/runtime.yaml`       │
│                   +  `environments/<env>/desired.yaml`       │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Runtime (rendered on hosts)                      │
│  `host/` (renderer, reconciler, secret loader, units)        │
│  `agents/host/` + `agents/wake/` (agent hosts, live today)   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Verification & operation                                     │
│  `policies/`  `tests/` (+ `tests/agents/`)  `runbooks/`      │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Org baseline | Bootstrap project, state buckets, org policies, `agents` folder/project/budget | `bootstrap/` |
| Agent fleet infra | VPC, NAT, IAP SSH, host + wake VMs, identities, per-agent secrets | `infra/agents/` |
| Agent provisioning | Host setup, per-agent users, rootless Docker, token broker, sessions, idle-stop | `agents/host/` |
| Wake service | Start stopped host from Slack; grows into fleet controller | `agents/wake/` |
| Slack channel | Agent-to-Slack MCP server over Socket Mode | `agents/marketplace/plugins/slack/server.py` |
| Environment modules | Reusable Terraform for one environment and one host | `infra/modules/environment/`, `infra/modules/host/` |
| Environment roots | Staging and prod instantiations, each with own state and authority | `infra/environments/staging/`, `infra/environments/prod/` |
| Deployment contract | Workload/runtime/desired-state schemas + golden and negative fixtures | `contracts/v1/` |
| Environment bindings | Physical bindings (`runtime.yaml`) and exact release (`desired.yaml`) per env | `environments/staging/`, `environments/prod/` |
| Host adapter | Renderer, reconciler, secret loader, systemd units, firewall templates | `host/` |
| Policy checks | Constraints on rendered configuration (worker isolation, pins, ports) | `policies/` |
| Tests | Schema, render, policy, IAM, lifecycle checks; live host checks | `tests/`, `tests/agents/host-checks.sh` |
| Runbooks | Operating procedures with a record of each run | `runbooks/`, `runbooks/agents/` |
| Governance | Groups, IAM bindings, repo protections, WIF conditions | `governance/` |
| Conventions | Naming and ownership rules for all durable identities | `conventions/` |
| Catalog | Inventory of environments, components, agents, owners | `catalog/` |
| Specs + ADRs | Target designs and accepted decisions (MADR) | `docs/specs/`, `docs/adr/` |

## Pattern Overview

**Overall:** Declarative infrastructure with a spec/contract boundary.

**Key Characteristics:**
- Terraform owns cloud resources; the host reconciler owns the rendered runtime; neither rewrites the other's artifacts (`README.md` ownership table).
- Each effective field has exactly one owner (product vs platform split, `docs/specs/cloud-platform.md` section 4.1).
- Every Terraform root has its own state, backend, and authority; staging and prod share nothing (`infra/environments/staging/README.md`, `infra/environments/prod/README.md`).
- Applies always use a reviewed binary plan; drift detection reports but never auto-repairs destructive change (`docs/specs/cloud-platform.md` section 8.3).
- Secrets are created as empty containers by Terraform; values enter only from the password manager via authorized CLI, never through Git or state (`infra/agents/secrets.tf`, `runbooks/agents/slack.md`).
- The agent fleet holds no authority in staging or prod (`docs/specs/agent-fleet.md`, `agents/README.md`).

## Layers

**Specs and decisions (intent):**
- Purpose: Declare what the platform must become and record why.
- Location: `docs/specs/`, `docs/adr/`, `conventions/`, `catalog/`, `governance/`
- Contains: Target specifications, MADR decision records, naming rules, inventory, IAM/repo-protection declarations.
- Depends on: Public cloud documentation cited inline; product repo ADRs for spanning decisions.
- Used by: Every Terraform root, the host adapter, provisioning, and reviewers judging whether a change matches intent.

**Organization baseline:**
- Purpose: Company-level guardrails everything else inherits.
- Location: `bootstrap/`
- Contains: `bootstrap_project.tf` (project + versioned tfstate bucket), `agents.tf` (agents folder, `hyprn-agents` project, tfstate bucket, billing budget), `org_policies.tf` (keyless, no default network, OS Login, Shielded VMs, private buckets, EU locations), `providers.tf`, `variables.tf`, `versions.tf`, `outputs.tf`.
- Depends on: Hand-created prerequisites in `bootstrap/README.md` (group `gcp-admins`, linked billing, enabled APIs, ADC credentials).
- Used by: `infra/agents/` (state lives in the agents project's bucket) and future `infra/environments/*` roots.

**Infrastructure (Terraform network/compute/identity):**
- Purpose: Declare the VMs, networks, identities, and secret containers agents run on today; product environments tomorrow.
- Location: `infra/agents/`, `infra/modules/environment/`, `infra/modules/host/`, `infra/environments/staging/`, `infra/environments/prod/`
- Contains: `infra/agents/*.tf` (`host.tf`, `wake.tf`, `network.tf`, `iam.tf`, `secrets.tf`); module and environment roots are README stubs plus future `.tf`.
- Depends on: `bootstrap/` outputs (project, folder, org policies).
- Used by: `agents/host/` and `agents/wake/` provisioning, which assume the VMs, VPC, NAT, and identities exist.

**Deployment contract (binding layer):**
- Purpose: Versioned schemas plus per-environment bindings that connect a product release to cloud resources without letting product PRs gain privilege.
- Location: `contracts/v1/`, `environments/staging/`, `environments/prod/`
- Contains: Workload, runtime-binding, and desired-state schemas with golden/negative fixtures; `runtime.yaml` (physical bindings, secret aliases with numeric versions); `desired.yaml` (sequence, release digest, config digest).
- Depends on: `docs/specs/cloud-platform.md` sections 4.2–4.4 for validation rules (pinned digests, no unknown fields, no cross-env references).
- Used by: `host/` renderer (supplies images, roots, UIDs, secret mounts from one validated binding) and `policies/` checks.

**Runtime (host adapter and agent hosts):**
- Purpose: Render validated intent into running services and keep them reconciled.
- Location: `host/`, `agents/host/`, `agents/wake/`, `agents/marketplace/`
- Contains: Product-host reconciler/renderer/secret-loader/units (spec target, `host/README.md`); agent-host provisioning scripts, systemd units, nftables egress, token broker, tmux/herdr sessions; wake-service Python; Slack MCP server.
- Depends on: Infrastructure layer (VMs, identities) and contract layer (validated intent); secrets from Secret Manager at runtime.
- Used by: `tests/agents/host-checks.sh` verification and `runbooks/agents/` operations.

**Verification and operation:**
- Purpose: Prove the platform behaves and record how it is operated.
- Location: `policies/`, `tests/`, `tests/agents/`, `runbooks/`
- Contains: Rendered-config policy checks; schema/render/policy/IAM/lifecycle tests; `host-checks.sh` post-provisioning checks; per-area runbooks ending with a run record.
- Depends on: All layers above (they check artifacts the other layers produce).
- Used by: Reviewers (CI gates) and operators (manual procedures).

## Data Flow

### Primary Request Path

Product delivery today is specified but not yet implemented (hosts, modules,
and contracts are stubs); the live path is the agent fleet:

1. Operator messages agent in Slack — Socket Mode event (`agents/marketplace/plugins/slack/server.py:1`, `agents/wake/wake.py:1`).
2. Wake service checks host status every 15 s; if stopped and sender is allowlisted, it replies "waking", starts the host via the Compute API, and disconnects (`agents/wake/wake.py:29`, `agents/wake/README.md`).
3. Agent session (tmux today, herdr in M1) under the agent's Linux user receives the event; secrets and allowlist come from root-written tmpfs (`agents/host/files/hyprn-agent-secrets`, `agents/host/files/hyprn-agent-session`).
4. Agent works one task per branch `agent/<name>/<slug>` in its own worktree, launched by `agents/host/files/bin/opencode-task`, following `agents/roles/<name>.md`.
5. Agent authenticates to GitHub with a one-hour installation token from the root token broker (`agents/host/files/hyprn-agent-github-token`, `agents/host/files/hyprn-git-credential`, `agents/host/files/bin/gh`) and opens a draft PR; a person merges.

### Target Product-Delivery Flow (per `docs/specs/cloud-platform.md` section 8)

1. Product PR → credential-free checks → merge → trusted build; release descriptor and artifacts land in staging stores.
2. Staging desired-state PR → protected merge → publisher writes `history/<sequence>-<sha>.json` + `current.json` to the `hyprn-<env>-desired` bucket with generation-match preconditions.
3. Host reconciler (`host/`) polls every 60 s under `/run/hyprn/deployment.lock`: validate manifest → compare actual state → prestage verified artifacts/secrets → drain → migrate → start behind closed admission → qualify → open admission.
4. Staging qualification record binds exact digest/target/policy/config; prod promotion copies identical artifacts (never rebuilds) and repeats the reconcile.
5. Rollback is a new `desired.yaml` sequence selecting an earlier compatible release; incompatible rollbacks stay in maintenance mode.

**State Management:**
- Cloud truth lives in Terraform state: `gs://hyprn-bootstrap-tfstate/bootstrap/`, `gs://hyprn-agents-tfstate/agents/`, one bucket per future environment root. All buckets versioned with `prevent_destroy`.
- Deployment truth lives in Git intent (`environments/*/desired.yaml`) mirrored to GCS (`current.json` + create-once history); the host rejects lower or conflicting sequences.
- Runtime truth lives on hosts: `/etc/hyprn/`, `/opt/hyprn/releases/<digest>/`, `/srv/hyprn/<env>/` (data disk), `/run/hyprn/` (tmpfs locks/secrets) — per `docs/specs/cloud-platform.md` section 5.3.
- Agent truth lives in GitHub (code/PRs), Notion (knowledge), Slack (approvals), and the future control-plane run-state DB (`docs/specs/agent-fleet.md` sections 5, 8).

## Key Abstractions

**Terraform root (one state, one authority):**
- Purpose: The unit of blast-radius isolation; staging can never touch prod by IAM construction.
- Examples: `bootstrap/`, `infra/agents/`, `infra/environments/staging/`, `infra/environments/prod/`
- Pattern: Each root has its own backend block, lock file, `variables.tf`/`versions.tf`, and a README with the exact `init / plan -out / apply <plan>` sequence.

**Terraform module (reusable environment/host shape):**
- Purpose: Single definition of an environment (project services, network, buckets, registry, secrets) and a host (VM, data disk, firewall) instantiated per environment.
- Examples: `infra/modules/environment/`, `infra/modules/host/`
- Pattern: Module directories with README describing the spec section they implement; roots in `infra/environments/*/` instantiate both.

**Contract schema (privilege boundary):**
- Purpose: Versioned JSON schemas that let product CI declare intent without gaining cloud privilege; unknown fields and unpinned images fail validation.
- Examples: `contracts/v1/`
- Pattern: Schema set + golden fixtures (stable rendering) + negative fixtures (unsafe input fails), pinned by product CI via platform commit and file hashes.

**Environment binding (physical + release intent):**
- Purpose: Split what the platform owns (bindings) from what the release selects (digest + sequence) so every change, including rollbacks, is a new monotonic sequence.
- Examples: `environments/staging/`, `environments/prod/`
- Pattern: `runtime.yaml` (project, zone, registry/bucket bindings, secret aliases at numeric versions) + `desired.yaml` (`hyprn-desired/v1`: sequence, release digest, config digest).

**Provisioning script (idempotent host convergence):**
- Purpose: Bring a VM from stock Debian to its declared role without Terraform re-apply; safe to re-run.
- Examples: `agents/host/provision.sh`, `agents/host/apply.sh`, `agents/wake/provision.sh`, `agents/wake/apply.sh`
- Pattern: `apply.sh` ships the directory over IAP from a workstation and runs `provision.sh` as root on the target, then runs checks (`tests/agents/host-checks.sh`).

**Root-owned loader (secret boundary):**
- Purpose: Move secrets from Secret Manager to tmpfs files owned by the exact consumer UID without the consumer ever reading Secret Manager directly.
- Examples: `agents/host/files/hyprn-agent-secrets`, `agents/host/files/hyprn-agent-secrets@.service`, `agents/host/files/hyprn-agent-github-token`
- Pattern: Systemd unit running as root fetches named versions, writes to `/run/hyprn-agents/` with exclusive no-follow creation; consumers mount/read files only.

**Slack channel server (inbound-only control):**
- Purpose: Give each agent a Slack presence with no public endpoint and no trust in message content.
- Examples: `agents/marketplace/plugins/slack/server.py`, `agents/marketplace/plugins/slack/slack-app-manifest.yaml`
- Pattern: Outbound WebSocket to Slack (Socket Mode); allowlist by Slack user ID from a root-written file; envelopes acked and deduped; permission replies restricted to `yes/no <id>` from allowlisted senders.

## Entry Points

**Terraform roots (`bootstrap/`, `infra/agents/`, `infra/environments/*/`):**
- Location: `bootstrap/*.tf`, `infra/agents/*.tf`
- Triggers: Operator running `terraform init`, `terraform plan -out=*.tfplan`, `terraform apply *.tfplan` with `GOOGLE_APPLICATION_CREDENTIALS` set.
- Responsibilities: Create/mutate cloud resources exactly as reviewed; bootstrap additionally adopts hand-created org resources via `import` blocks.

**Agent host provisioning (`agents/host/apply.sh` → `agents/host/provision.sh`):**
- Location: `agents/host/apply.sh`, `agents/host/provision.sh`
- Triggers: Operator after starting the host or changing `agents/host/`, `agents/roles/`, `agents/marketplace/`, or `tests/agents/`.
- Responsibilities: Install pinned toolchains (Docker, GitHub CLI, Claude Code, OpenCode with SHA checks), create per-agent users from `agents/host/agents.txt`, install units/egress/sessions, then run `tests/agents/host-checks.sh`.

**Wake service (`agents/wake/wake.py` + `agents/wake/hyprn-agents-wake.service`):**
- Location: `agents/wake/wake.py`, `agents/wake/wake.json`
- Triggers: Systemd on `hyprn-agents-wake-01` (always on); polls host status every 15 s and holds Socket Mode connections while the host is stopped.
- Responsibilities: Start the host on allowlisted DM/mention, then disconnect so the agent alone receives events; future fleet controller (queue, dispatcher, approvals, budgets).

**Slack channel server (`agents/marketplace/plugins/slack/server.py`):**
- Location: `agents/marketplace/plugins/slack/server.py`
- Triggers: Spawned by the agent harness over MCP stdio; connects outbound to Slack Socket Mode.
- Responsibilities: Deliver only allowlisted DMs/mentions into the session; relay permission requests and verdicts; never expose tokens.

**Host checks (`tests/agents/host-checks.sh`):**
- Location: `tests/agents/host-checks.sh`
- Triggers: End of every `agents/host/apply.sh` run, as root on the host.
- Responsibilities: Assert metadata unreachable for agents, private homes, rootless Docker only, correct harnesses per agent, secret file ownership, pinned OpenCode, idle-stop active, no key files.

**Future product-host reconciler (`host/`):**
- Location: `host/` (README + spec section 9 today; renderer, reconciler, units, firewall templates to come)
- Triggers: `hyprn-reconcile` timer every 60 s plus human commands sharing `/run/hyprn/deployment.lock`.
- Responsibilities: Validate manifest, prestage, lifecycle (`drain`/`migrate`/`start`/`qualify`), persist outcome, publish sanitized status.

## Architectural Constraints

- **Threading:** Reconciler is single-pass serial with jitter and bounded timeouts, never parallel (`docs/specs/cloud-platform.md` section 9.1). Wake service is one thread per Slack app plus a 15 s poll loop (`agents/wake/wake.py:29`). Slack server dedupes by event ID with catch-up delays (`agents/marketplace/plugins/slack/server.py:35`).
- **Global state:** Terraform state per root in versioned GCS buckets (single-writer via state lock); `current.json` generation-match serializes desired-state publication; host lock order is deployment/backup → admission/drain → component locks.
- **Circular imports:** None in Terraform (strict layering: `bootstrap/` → `infra/*` → `agents/*` provisioning → `host/` runtime). The wake VM never logs in to the host; the host never calls back to wake — events flow only via Slack/host-status polling.
- **No agent authority in product environments:** The fleet project has no IAM on staging/prod; CI identities are per-environment and read/write-scoped (`docs/specs/cloud-platform.md` section 6.2, `infra/agents/iam.tf` per-secret grants).
- **Secret values never in Git/state:** Terraform creates containers and IAM only; `terraform.tfvars` holds identifiers only (`bootstrap/README.md`); `tests/agents/host-checks.sh` asserts no key files.
- **Pinned everything:** Boot images by full image self-link (`infra/agents/variables.tf:49`), Claude Code/OpenCode by version + SHA (`agents/host/provision.sh:8`), signing keys by fingerprint with hard failure on mismatch.

## Anti-Patterns

### Unreviewed plan applied

**What happens:** Running `terraform apply` without a saved, reviewed binary plan, or applying a plan after code or state changed.
**Why it's wrong:** Terraform code is executable and destructive diffs (disk replacement, bucket removal) look like ordinary edits; `prevent_destroy` does not survive deleting the resource block.
**Do this instead:** Follow the per-root README sequence — `terraform plan -out=agents.tfplan` on reviewed code, review the plan (especially destroy/replace), then `terraform apply agents.tfplan` (`infra/agents/README.md`, `bootstrap/README.md`).

### Secret value through Terraform or Git

**What happens:** Putting a token, key, or password in a `.tf` file, `tfvars`, or a commit, or printing it in a preflight report or log.
**Why it's wrong:** Values would persist in state, history, and logs; the repo's outputs are committed and its logs go to Cloud Logging.
**Do this instead:** Create the container in `infra/agents/secrets.tf`, grant per-secret accessor to the host/wake identity only, and add the value from the password manager via authorized CLI (`runbooks/agents/slack.md`); validate by shape, never print.

### Product change gaining privilege by adding a field

**What happens:** A product PR adds a mount, capability, secret alias, or network egress to pass validation.
**Why it's wrong:** The contract is a privilege boundary, not a free-form config; silent widening breaks containment (networkless `worker`, metadata denial, secret-to-consumer mapping).
**Do this instead:** Validation rejects unknown fields and unapproved widening; allowed sets change only through platform review with golden + negative fixture updates (`contracts/v1/README.md`, `policies/README.md`).

### Reaching prod from staging identity (or vice versa)

**What happens:** Reusing a service account, bucket, secret, disk, or Terraform state across environments to "simplify" setup.
**Why it's wrong:** Environment separation is an IAM property proven by negative checks; sharing any of these collapses the boundary the pilot's security case rests on.
**Do this instead:** Keep per-environment projects, roots, states, disks, buckets, secrets, and identities (`infra/environments/staging/` vs `infra/environments/prod/`, `docs/specs/cloud-platform.md` section 3).

## Error Handling

**Strategy:** Fail closed and stay closed; only transient pre-mutation fetch failures retry. Unexpected store, mount, or security drift closes admission and alerts.

**Patterns:**
- Provisioning uses `set -euo pipefail` with hard exits on fingerprint/SHA mismatch (`agents/host/provision.sh:4`).
- Wake service logs to stderr and keeps polling; Slack envelopes are acked even when dropped so Slack stops redelivering (`agents/marketplace/plugins/slack/server.py`, `agents/wake/wake.py:32`).
- Target reconciler records checkpoints (`verified` → `applied`) with last-step and migration-begun flags; partial initialization requires recovery, never overwrite (`docs/specs/cloud-platform.md` sections 9.1–9.3).
- Lifecycle CLI returns structured JSON with exit codes 0/2/3/4/5/6 distinguishing success, bad input, incompatibility, admission conflict, failed verification, and operator-recovery-required.

## Cross-Cutting Concerns

**Logging:** Structured logs (request/operation IDs, environment, component, release, outcome) to Cloud Logging; metrics to Cloud Monitoring; no separate stack. Logs never contain secrets, tokens, prompts, or private payloads. Wake/Slack components log to stderr/journald without message content for dropped events.
**Validation:** Safe-parse then schema + semantic checks at every boundary: contract validation (unknown fields, pins, cross-env refs), manifest checks on the host, IAM negative tests, `host-checks.sh` post-provisioning assertions.
**Authentication:** Humans via groups + MFA + IAP/OS Login; CI via Workload Identity Federation with numeric `repository_id` claims; VMs via attached service accounts with per-secret IAM; agents via one-hour GitHub App tokens and Secret-Manager-backed Slack tokens; containers denied metadata entirely.

---

*Architecture analysis: 2026-10-13*
