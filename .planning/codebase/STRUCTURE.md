---
last_mapped_commit: a393bda2510b521148d626a02e4a5aef58dae1d6
last_mapped_at: 2026-10-13
---

# Codebase Structure

**Analysis Date:** 2026-10-13

## Directory Layout

```
hyprn-platform/
├── AGENTS.md               # Agent instructions (entry doc for agents)
├── README.md               # Platform overview + layout table
├── bootstrap/              # Org baseline Terraform root (LIVE)
├── infra/
│   ├── agents/             # Agent fleet infra Terraform root (LIVE)
│   ├── modules/
│   │   ├── environment/    # One-environment module (STUB: README only)
│   │   └── host/           # Full-stack host module (STUB: README only)
│   └── environments/
│       ├── staging/        # Staging root (STUB: README only)
│       └── prod/           # Prod root (STUB: README only)
├── contracts/
│   └── v1/                 # Deployment schemas + fixtures (STUB: README only)
├── environments/
│   ├── staging/            # Staging runtime.yaml + desired.yaml (STUB: README only)
│   └── prod/               # Prod runtime.yaml + desired.yaml (STUB: README only)
├── host/                   # Product-host reconciler/adapter (STUB: README only)
├── agents/
│   ├── host/               # Agent host provisioning (LIVE)
│   ├── wake/               # Wake service → future fleet controller (LIVE)
│   ├── marketplace/        # Claude Code plugin marketplace (LIVE: slack plugin)
│   ├── roles/              # Per-agent role instructions (LIVE: ada.md, codd.md)
│   ├── policy/             # Reviewed agent policy copies (LIVE stubs)
│   └── measurement/        # Seat-session telemetry (STUB: README only)
├── governance/             # Groups, IAM, repo protections, WIF (STUB: README only)
├── policies/               # Rendered-config policy checks (STUB: README only)
├── conventions/            # Naming + ownership rules (LIVE doc)
├── catalog/                # Environment/component inventory (STUB: README only)
├── tests/
│   └── agents/             # Host checks (LIVE: host-checks.sh)
├── runbooks/
│   └── agents/             # Ops procedures: gcp, host, slack, github, opencode
├── docs/
│   ├── specs/              # cloud-platform.md, agent-fleet.md (LIVE specs)
│   └── adr/                # MADR records 0001–0006 (LIVE)
└── .planning/              # GSD planning state (not committed as platform code)
```

LIVE = contains implementation beyond a README. STUB = README describing
specified-but-unbuilt content; the README is the current contract.

## Directory Purposes

**`bootstrap/`:**
- Purpose: Company-level Google Cloud baseline every other root builds on.
- Contains: Terraform `.tf` files, `.terraform.lock.hcl`, `terraform.tfvars` (identifiers only), README with run sequence and hand-created prerequisites.
- Key files: `bootstrap/bootstrap_project.tf`, `bootstrap/agents.tf`, `bootstrap/org_policies.tf`, `bootstrap/variables.tf`, `bootstrap/versions.tf`, `bootstrap/outputs.tf`, `bootstrap/providers.tf`, `bootstrap/README.md`

**`infra/agents/`:**
- Purpose: The `hyprn-agents` project's network, VMs, identities, and secret containers.
- Contains: Terraform root (`.tf` files + lock file) and README with the apply sequence and state location.
- Key files: `infra/agents/host.tf`, `infra/agents/wake.tf`, `infra/agents/network.tf`, `infra/agents/iam.tf`, `infra/agents/secrets.tf`, `infra/agents/variables.tf`, `infra/agents/outputs.tf`, `infra/agents/providers.tf`, `infra/agents/versions.tf`

**`infra/modules/environment/`, `infra/modules/host/`:**
- Purpose: Reusable modules for one environment and one full-stack host (specified in `docs/specs/cloud-platform.md` section 5; not yet written).
- Contains: README only. Future home of `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`.
- Key files: `infra/modules/environment/README.md`, `infra/modules/host/README.md`

**`infra/environments/staging/`, `infra/environments/prod/`:**
- Purpose: Per-environment roots instantiating both modules, each with its own backend, state, and authority.
- Contains: README only. Future home of root `.tf` files pinning module sources and environment inputs.
- Key files: `infra/environments/staging/README.md`, `infra/environments/prod/README.md`

**`contracts/v1/`:**
- Purpose: Versioned deployment schema set (workload, runtime binding, desired state) with golden and negative fixtures.
- Contains: README only today. Future home of schema files plus `golden/` and `negative/` fixture directories.
- Key files: `contracts/v1/README.md`

**`environments/staging/`, `environments/prod/`:**
- Purpose: Per-environment bindings and desired release: `runtime.yaml` (physical bindings) and `desired.yaml` (`hyprn-desired/v1`).
- Contains: README only today. Future home of `runtime.yaml` and `desired.yaml`.
- Key files: `environments/staging/README.md`, `environments/prod/README.md`

**`host/`:**
- Purpose: Product-host adapter: renderer, reconciler, secret loader, systemd units, firewall templates (specified in `docs/specs/cloud-platform.md` section 9).
- Contains: README only today. Future home of renderer/reconciler code, unit files, firewall templates.
- Key files: `host/README.md`

**`agents/host/`:**
- Purpose: Provisioning for `hyprn-agents-host-01`: packages, per-agent users, rootless Docker, token broker, sessions, egress, idle-stop.
- Contains: `provision.sh`, `apply.sh`, `agents.txt`, `files/` (systemd units, scripts, wrappers, nftables rules, OpenCode config).
- Key files: `agents/host/provision.sh`, `agents/host/apply.sh`, `agents/host/agents.txt`, `agents/host/README.md`, `agents/host/files/egress.nft`, `agents/host/files/hyprn-agent-github-token`, `agents/host/files/hyprn-agent-secrets`, `agents/host/files/bin/opencode-task`

**`agents/wake/`:**
- Purpose: Wake service on `hyprn-agents-wake-01`; grows into the fleet controller (queue, dispatcher, approvals, budgets).
- Contains: Python service, JSON config, systemd unit, provisioning scripts.
- Key files: `agents/wake/wake.py`, `agents/wake/wake.json`, `agents/wake/hyprn-agents-wake.service`, `agents/wake/provision.sh`, `agents/wake/apply.sh`, `agents/wake/README.md`

**`agents/marketplace/`:**
- Purpose: Claude Code plugin marketplace `hyprn-agents`, installed root-owned at `/opt/hyprn-agents/marketplace` on the host.
- Contains: `.claude-plugin/marketplace.json`, `plugins/slack/` (plugin.json, `.mcp.json`, `server.py`, `slack-app-manifest.yaml`, README with audit record).
- Key files: `agents/marketplace/.claude-plugin/marketplace.json`, `agents/marketplace/plugins/slack/server.py`, `agents/marketplace/plugins/slack/slack-app-manifest.yaml`, `agents/marketplace/README.md`

**`agents/roles/`, `agents/policy/`, `agents/measurement/`:**
- Purpose: Per-agent role instructions installed as `CLAUDE.md`/`AGENTS.md`; reviewed copies of org-wide agent policy; seat-session usage telemetry.
- Contains: `ada.md`, `codd.md`, README indexes; `policy/` holds `managed-settings.json` and `egress-allowlist.txt` references.
- Key files: `agents/roles/ada.md`, `agents/roles/codd.md`, `agents/roles/README.md`, `agents/policy/README.md`, `agents/measurement/README.md`

**`governance/`:**
- Purpose: Groups and IAM bindings, GitHub protections (rulesets, checks, CODEOWNERS), WIF conditions (specified in `docs/specs/cloud-platform.md` sections 6, 8.2).
- Contains: README only today.
- Key files: `governance/README.md`

**`policies/`:**
- Purpose: Policy checks on rendered configuration (worker isolation, no foreign stores, pinned images, resource limits, no cross-env resources).
- Contains: README only today.
- Key files: `policies/README.md`

**`conventions/`:**
- Purpose: Naming and ownership rules plus the agent-identity table (personas only in per-agent identities, never in cloud resources).
- Contains: Single README; no code.
- Key files: `conventions/README.md`

**`catalog/`:**
- Purpose: Inventory of environments, components, agents, and owners.
- Contains: README only today.
- Key files: `catalog/README.md`

**`tests/`, `tests/agents/`:**
- Purpose: Schema/render/policy/IAM/lifecycle tests (specified) and the live post-provisioning host checks.
- Contains: README indexes; `tests/agents/host-checks.sh` (runnable as root on the host).
- Key files: `tests/README.md`, `tests/agents/README.md`, `tests/agents/host-checks.sh`

**`runbooks/`, `runbooks/agents/`:**
- Purpose: Operating procedures, each ending with a record of what was done.
- Contains: `gcp.md`, `host.md`, `slack.md`, `github.md`, `opencode.md` plus README indexes.
- Key files: `runbooks/README.md`, `runbooks/agents/README.md`, `runbooks/agents/gcp.md`, `runbooks/agents/host.md`, `runbooks/agents/slack.md`, `runbooks/agents/github.md`, `runbooks/agents/opencode.md`

**`docs/specs/`, `docs/adr/`:**
- Purpose: Target specifications and MADR decision records; spanning product/platform decisions live in `hyprn-mvp` starting at its ADR-0001.
- Contains: `agent-fleet.md`, `cloud-platform.md`, ADR `0001`–`0006` plus README indexes.
- Key files: `docs/specs/agent-fleet.md`, `docs/specs/cloud-platform.md`, `docs/adr/0001-agent-fleet.md` through `docs/adr/0006-agent-first-operating-model.md`

## Key File Locations

**Entry Points:**
- `bootstrap/*.tf`: Organization baseline root; apply with `terraform plan -parallelism=1 -out=bootstrap.tfplan`.
- `infra/agents/*.tf`: Agent fleet infra root; state `gs://hyprn-agents-tfstate/agents/`.
- `agents/host/apply.sh`: Ships provisioning to the host over IAP and runs checks.
- `agents/wake/apply.sh`: Installs the wake service on the wake VM.
- `agents/wake/wake.py`: Wake-service main loop (poll + Socket Mode).
- `agents/marketplace/plugins/slack/server.py`: Slack channel MCP server.
- `tests/agents/host-checks.sh`: Post-provisioning assertions, run as root on the host.

**Configuration:**
- `bootstrap/terraform.tfvars`: Identifiers only (org, billing, project IDs, groups) — never secret values.
- `bootstrap/variables.tf`, `infra/agents/variables.tf`: Root inputs with defaults (`europe-west1`/`europe-west1-b`, machine types, image pin, agent lists).
- `bootstrap/versions.tf`, `infra/agents/versions.tf`, `*.lock.hcl`: Provider constraints and committed lock files.
- `agents/host/agents.txt`: Agent roster (name, UID 20000–20999, harness, GitHub App IDs, display name).
- `agents/wake/wake.json`: Project, zone, host, and agent names for the wake service.
- `agents/host/files/opencode.json`, `agents/host/files/egress.nft`: OpenCode managed config; nftables egress rules.

**Core Logic:**
- `agents/host/provision.sh`: Idempotent host convergence (packages, keys, users, units, marketplace).
- `agents/host/files/hyprn-agent-github-token`: GitHub App token broker (sign + mint hourly).
- `agents/host/files/hyprn-agent-secrets`: Root secret loader (Secret Manager → tmpfs).
- `agents/host/files/bin/opencode-task`: One worktree + branch per task launcher.
- `infra/agents/secrets.tf`: Per-agent secret containers (`<name>-agent-<purpose>`) with per-secret IAM.

**Testing:**
- `tests/agents/host-checks.sh`: Live host assertions (metadata denial, homes, Docker, harness, secrets, timers).
- `tests/README.md`, `tests/agents/README.md`: Specified test scopes (schema, render, policy, IAM, lifecycle).

## Naming Conventions

**Files:**
- Terraform: lowercase snake_case resource files by concern — `infra/agents/host.tf`, `infra/agents/network.tf`, `infra/agents/iam.tf`, `infra/agents/secrets.tf`, `infra/agents/wake.tf`, plus `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf` per root. Matches in `bootstrap/`.
- Provisioning: `provision.sh` (idempotent, runs as root on target) + `apply.sh` (runs from workstation, ships + invokes + checks) — same pair in `agents/host/` and `agents/wake/`.
- Systemd templated units use `@`: `agents/host/files/hyprn-agent@.service`, `agents/host/files/hyprn-agent-github-token@.service`, `agents/host/files/hyprn-agent-secrets@.service`.
- Specs lower-kebab: `docs/specs/agent-fleet.md`, `docs/specs/cloud-platform.md`; ADRs zero-padded: `docs/adr/0001-agent-fleet.md`.
- Runbooks lower-case by area: `runbooks/agents/gcp.md`, `runbooks/agents/slack.md`.
- Per-agent secret names: `<name>-agent-<purpose>` (e.g. `ada-agent-github-app-key`) — see `conventions/README.md` and `infra/agents/secrets.tf`.

**Directories:**
- Top level by architectural layer (`bootstrap/`, `infra/`, `contracts/`, `environments/`, `host/`, `agents/`, `governance/`, `policies/`, `tests/`, `runbooks/`, `docs/`, `conventions/`, `catalog/`).
- `infra/` splits into live roots (`infra/agents/`), reusable modules (`infra/modules/<name>/`), and per-environment roots (`infra/environments/<env>/`).
- Environment directories always named `staging` / `prod` (plus `local` for developer machines, never in this repo): `environments/<env>/`, `infra/environments/<env>/`.
- Plugin path fixed by marketplace layout: `agents/marketplace/plugins/<name>/` with `.claude-plugin/plugin.json` inside.

## Where to Add New Code

**New Terraform root (e.g. a new environment):**
- Primary code: `infra/environments/<env>/` — new directory with `main.tf` instantiating `infra/modules/environment` and `infra/modules/host`, plus `variables.tf`, `outputs.tf`, `versions.tf`, backend block, and README following `infra/environments/staging/README.md`.
- State: New versioned bucket with `prevent_destroy`, created by `bootstrap/`-style code or the environment module — never reuse another root's bucket.

**New Terraform module:**
- Implementation: `infra/modules/<name>/` — `main.tf`, `variables.tf`, `outputs.tf`, README citing the spec section it implements (follow `infra/modules/host/README.md`).

**New agent:**
- Roster: append to `agents/host/agents.txt` (name, UID, harness, App IDs).
- Role: new file `agents/roles/<name>.md` following `agents/roles/codd.md`.
- Infra: add name to `agents` / `slack_agents` in `infra/agents/variables.tf`; secrets materialize via `infra/agents/secrets.tf` `for_each`.
- Secrets: values added from the password manager per `runbooks/agents/slack.md`, never in code.

**New Slack/plugin capability:**
- Implementation: `agents/marketplace/plugins/slack/` — extend `server.py` (stdlib + `python3-websocket` only), update `slack-app-manifest.yaml` if scopes change, and append the audit reasoning to `agents/marketplace/README.md`.

**New host-provisioning behavior:**
- Scripts/units: `agents/host/files/` (root-owned install in `agents/host/provision.sh` `install_host_files()`), then assert it in `tests/agents/host-checks.sh`.
- Ship: always via `agents/host/apply.sh`, never by hand-editing the host.

**New wake/fleet-controller behavior:**
- Implementation: `agents/wake/wake.py` + `agents/wake/wake.json`; unit changes in `agents/wake/hyprn-agents-wake.service`; deploy via `agents/wake/apply.sh`.

**New contract schema version:**
- Implementation: `contracts/v1/` (today) — new version gets a sibling `contracts/v2/` directory with schemas plus `golden/` and `negative/` fixtures; product CI pins by commit + hashes.

**New policy check:**
- Implementation: `policies/` — add the check beside the README scope line (worker isolation, pins, ports, limits, no cross-env); add golden/negative fixtures under `tests/`.

**New test:**
- Host checks: extend `tests/agents/host-checks.sh` (runs as root after provisioning).
- Schema/render/policy/IAM/lifecycle: `tests/` following `tests/README.md` scope (golden proves stable rendering, unsafe fixtures must fail).

**New runbook / operation record:**
- Procedures: `runbooks/agents/<area>.md`; every manual operation appends its record to the same file per `runbooks/README.md`.

**New decision:**
- Records: `docs/adr/NNNN-<slug>.md` in MADR 4 format; accepted records are superseded by a new record, never edited (`docs/adr/README.md`).

## Special Directories

**`.planning/`:**
- Purpose: GSD planning state (`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `milestones/`, `codebase/`).
- Generated: Yes (by GSD commands).
- Committed: Planning files are committed on planning branches per repo workflow; never referenced by Terraform or provisioning.

**`agents/marketplace/.claude-plugin/`, `agents/marketplace/plugins/slack/.claude-plugin/`:**
- Purpose: Marketplace and plugin manifests consumed by Claude Code on the host.
- Generated: No (hand-authored JSON).
- Committed: Yes; shipped root-owned to `/opt/hyprn-agents/marketplace` by `agents/host/provision.sh`.

---

*Structure analysis: 2026-10-13*
