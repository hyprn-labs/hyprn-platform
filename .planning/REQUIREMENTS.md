# Requirements: hyprn-platform

**Defined:** 2026-10-12 (revised 2026-10-13: security baseline, efficiency and onboarding automation)
**Milestone:** Agent fleet operational
**Core Value:** The platform owner gives an agent a task in Slack and receives a reviewable draft pull request; no path exists from the agent fleet to staging or prod credentials; adding an agent is one command with a handful of approvals.

Derived from ADR-0001 (as amended by ADR-0002, ADR-0003, ADR-0005), the agent fleet foundation plan (`milestones/agent-fleet-foundation/PLAN.md`) and the vendor capabilities checked on 2026-10-13. Each requirement is verifiable by the platform owner.

## v1 Requirements

### Agent policy (POL)

- [ ] **POL-01**: The Claude Code permission rules and sandbox settings for agents are reviewed in `agents/policy/`, applied organization-wide by the Team Owner in the admin console, and recorded in `runbooks/agents/`. Routine work runs without prompts; only risky actions are relayed to Slack for approval.
- [ ] **POL-02**: The Claude Code sandbox network allowlist for agent shell commands is reviewed in `agents/policy/`; a request to any other host fails inside the sandbox.
- [ ] **POL-03**: `strictKnownMarketplaces` is set organization-wide so only the `hyprn-agents` marketplace is accepted; an agent cannot add another marketplace.
- [ ] **POL-04**: Claude Code deny rules refuse merging pull requests, pushing to `main` and force pushing in every `hyprn-labs` repository. These rules are the enforcing control until a ruleset exists (ADR-0005).

### Egress control (EGR)

- [ ] **EGR-01**: Agent users and their containers reach the internet only through a filtering proxy on the host (DNS stays allowed); host rules make the proxy the only path. In observe mode it logs every destination per agent without blocking.
- [ ] **EGR-02**: After the measured week, the proxy enforces a domain allowlist reviewed in `agents/policy/` (GitHub, Anthropic, Slack, the product's package registries); a request to any other domain is refused and logged.

### Detection (DET)

- [ ] **DET-01**: An alert reaches `gcp-admins` when any principal other than the host or wake identity reads a secret in `hyprn-agents`, or when a secret is created, deleted or given a new reader.
- [ ] **DET-02**: An alert reaches `gcp-admins` on any IAM policy change in `hyprn-agents` or on its folder.

### Account safeguards (SEC, DOC)

- [ ] **SEC-01**: A break-glass super admin exists with an offline key, holds no standing Google Cloud role, and its use procedure is written in `runbooks/agents/gcp.md` without secrets.
- [ ] **SEC-02**: The `hyprn-labs` GitHub organization requires two-factor authentication for all members.
- [x] **DOC-01**: ADR-0003 is accepted and linked from `docs/adr/README.md`: our own Slack channel server is the plugin.

### GitHub workflow (GH)

- [ ] **GH-01**: From a Slack task given by the platform owner, Ada creates branch `agent/ada/<slug>`, pushes it and opens a draft pull request authored by `ada-agent-hyprn[bot]`. The description states what changed and how it was verified, and Ada does not merge it.
- [ ] **GH-02**: A worktree helper creates one worktree per task on branch `agent/<name>/<slug>` with its own port block, Compose project name and test database name as environment variables, and removes the worktree and local branch once the pull request is merged or closed. Two worktrees run side by side without collisions.
- [x] **GH-03**: The interim machine account is removed: token revoked, account removed from `hyprn-labs`, secret `ada-agent-github-token` deleted, recorded in `runbooks/agents/github.md`.

### Efficiency (EFF)

- [ ] **EFF-01**: Host provisioning installs the toolchains the product repositories pin (Python with uv, Node, and their exact versions), so an agent starts a task without installing tools.
- [ ] **EFF-02**: Package and Docker layer caches persist per agent across tasks and host stops; a second run of the product's test setup in a fresh worktree is measurably faster than the first.

### Fleet as code and onboarding (FLT)

- [ ] **FLT-01**: `agents/fleet.yaml` is the single source for the fleet (name, display name, role, seat tier, Linux UID, Slack app ID, GitHub App slug, App ID, installation ID, bot user ID). Terraform, host provisioning, the wake service and the host checks read it; `agents.txt` and `wake.json` are generated or removed.
- [ ] **FLT-02**: Each agent's Google group `<name>@agents.hyprn.ai` and its membership are Terraform resources; its posting and moderation settings (external senders such as Anthropic's sign-in mail accepted, conversations visible to members only, joining by invitation) are applied by script or recorded as a single manual step.
- [ ] **FLT-03**: The agent's Slack app is created from the reviewed manifest through the manifest API, with an icon generated from the agent's initial on brand orange; the install approval is captured locally and the bot token goes straight into Secret Manager; the Socket Mode token is the one documented manual step.
- [ ] **FLT-04**: The agent's GitHub App is created through the GitHub App manifest flow (one confirmation), its private key goes straight into Secret Manager without touching disk, and the installation and bot IDs are discovered by API after the owner installs it.
- [ ] **FLT-05**: The agent's Claude Code sign-in can come from a `claude setup-token` token stored in Secret Manager instead of an interactive login on the host, if channels work with it; otherwise the interactive login stays and the finding is recorded.
- [ ] **FLT-06**: `agents/fleet add <name>` runs the whole onboarding: fleet entry, Google group, Slack app, GitHub App, Terraform plan for the owner's go, provisioning, host checks and a Slack test message. A throwaway test agent is onboarded in 15 minutes or less with 8 human actions or fewer, the Claude seat steps excepted.
- [ ] **FLT-07**: `agents/fleet remove <name>` offboards an agent: GitHub App uninstalled, Slack app deleted, secrets and Google group removed through Terraform, Linux user removed with its home archived; the remaining manual steps (Claude seat, App registration deletion) are printed. The test agent from FLT-06 is offboarded this way.
- [ ] **FLT-08**: `runbooks/agents/onboarding.md` describes adding and removing an agent, the human actions and the one-time prerequisites (Slack configuration token, allowed email domain, channels setting).

### Acceptance and isolation (ACC)

- [ ] **ACC-01**: Permission relay works in Slack: a risky action produces a prompt in the platform owner's conversation; `yes <id>` from the platform owner lets it proceed and `no <id>` stops it.
- [ ] **ACC-02**: A message from a non-allowlisted Slack sender gets no reaction, does not wake a stopped host and never reaches the session; an approval from a non-allowlisted sender is rejected.
- [ ] **ACC-03**: An agent's attempts to merge a pull request or push to `main` are refused, and `--dangerously-skip-permissions` is refused.
- [ ] **ACC-04**: An isolation check searches IAM organization-wide and passes only if `hyprn-agents` principals hold roles inside `hyprn-agents` alone, no staging or prod principal holds a role inside it, and the host and wake identities hold exactly their declared roles.
- [ ] **ACC-05**: A no-production-credentials check passes only if the host holds no user cloud credentials, no key files, no staging or prod roles and no staging or prod secrets.
- [ ] **ACC-06**: The ADR-0002 confirmations are recorded: the wake identity is refused any action other than get, start and stop on the host; the wake service holds no Slack connection while the host runs; the host keeps its disk across an idle stop.
- [ ] **ACC-07**: With two agents on the host, neither can read the other's home, secrets, transcripts or Docker, nor use the other's GitHub App token or Slack app.
- [ ] **ACC-08**: One command runs every acceptance and isolation check and records the result in `runbooks/agents/`; it runs after each host or project change.

### Measurement (MEAS)

- [ ] **MEAS-01**: Claude Code OpenTelemetry export from the agent host reaches a collector on the host, and a daily report shows tokens, estimated API-equivalent cost, seat-limit hits, Slack approvals and time from task to pull request. The day-one report exists.
- [ ] **MEAS-02**: One week of real tasks given by the platform owner runs with extra usage off, with the Team admin analytics and spend report read daily; the proxy runs in observe mode the same week. Seven consecutive daily reports exist.
- [ ] **MEAS-03**: A weekly summary reports limit hits per day and window, API-equivalent cost against the seat price, approvals per task, queue wait, pull-request counts and the destinations seen by the proxy. The platform owner records the decisions on default model, Standard versus Premium seats, seats versus API keys, and when to add agent #2 in a follow-up ADR.

## Deferred Requirements (after this milestone)

### GitHub enforcement (GHE)

- **GHE-01**: GitHub Team plan, a human team for code owners, `CODEOWNERS` in each repository, and a ruleset on `main` requiring a pull request, human code-owner approval, stale-approval dismissal, no force push and no bypass. Trigger: the platform owner upgrades the organization plan (recommended: it is the only hard lock on `main`). POL-04 remains as defense in depth.
- [x] **GHE-02**: GitHub App per agent with one-hour tokens (ADR-0005). Done 2026-10-13.
- **GHE-03**: Acceptance for GHE-01: merge and push to `main` by an agent refused by GitHub; an agent's approval does not satisfy the rule.

### Fleet growth (FLEET)

- **FLEET-01**: Agent #2 onboarded with `agents/fleet add`. Trigger: Anthropic's human answer on agent seats and the MEAS-03 decision.
- **FLEET-02**: Overflow through API keys or an open-weight low-cost tier. Trigger: MEAS-03 finds seat limits binding.
- **FLEET-03**: A cockpit showing every agent's state across hosts (for example herdr) replaces per-agent tmux sessions. Trigger: two or more agents in daily use.
- **FLEET-04**: GitHub issues assigned to an agent as a second task intake beside Slack. Trigger: the platform owner wants asynchronous task queues.
- **FLEET-05**: Slack plan with no app limit. Trigger: the fleet approaches the Free plan's 10 apps.

### Platform build-out (PLAT)

- **PLAT-01**: Staging and prod projects, hosts, buckets, reconciler, deployment contract, CI identities and the product delivery pipeline as defined in `docs/specs/cloud-platform.md`. Trigger: the product's local edition is ready.
- **PLAT-02**: Re-run the ACC-04 isolation check when staging and prod are created.

## Out of Scope

| Item | Reason |
|------|--------|
| Staging and prod environments, deployment contract, host reconciler, delivery pipeline | Follow the product's local edition; specified in the platform specification |
| Automating Claude seat invitations | The Team plan has no member API (Enterprise and Console only) |
| Product support for per-worktree overrides | Product work in `hyprn-mvp` |
| Signed commits | Not required for now (ADR-0001 section 5) |
| Product code in this repository | Belongs in `hyprn-mvp` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| POL-01 | Phase 1 | Pending |
| POL-02 | Phase 1 | Pending |
| POL-03 | Phase 1 | Pending |
| POL-04 | Phase 1 | Pending |
| EGR-01 | Phase 1 | Pending |
| DET-01 | Phase 1 | Pending |
| DET-02 | Phase 1 | Pending |
| SEC-01 | Phase 1 | Pending |
| SEC-02 | Phase 1 | Pending |
| DOC-01 | Phase 1 | Complete |
| GH-01 | Phase 2 | Pending |
| GH-02 | Phase 2 | Pending |
| GH-03 | Phase 2 | Complete |
| EFF-01 | Phase 2 | Pending |
| EFF-02 | Phase 2 | Pending |
| FLT-01 | Phase 3 | Pending |
| FLT-02 | Phase 3 | Pending |
| FLT-03 | Phase 3 | Pending |
| FLT-04 | Phase 3 | Pending |
| FLT-05 | Phase 3 | Pending |
| FLT-06 | Phase 3 | Pending |
| FLT-07 | Phase 3 | Pending |
| FLT-08 | Phase 3 | Pending |
| ACC-01 | Phase 4 | Pending |
| ACC-02 | Phase 4 | Pending |
| ACC-03 | Phase 4 | Pending |
| ACC-04 | Phase 4 | Pending |
| ACC-05 | Phase 4 | Pending |
| ACC-06 | Phase 4 | Pending |
| ACC-07 | Phase 4 | Pending |
| ACC-08 | Phase 4 | Pending |
| MEAS-01 | Phase 5 | Pending |
| MEAS-02 | Phase 5 | Pending |
| MEAS-03 | Phase 5 | Pending |
| EGR-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-10-12*
*Last updated: 2026-10-13 after adopting the five-phase roadmap*
