# Requirements: hyprn-platform

**Defined:** 2026-10-12 (revised 2026-10-13: value-first milestones, review fixes)
**Core Value:** Agents do HYPRN's engineering and operations work — on request and on their own triggers — safely, with costs known, and they get better from feedback; adding an agent is one command.
**Target:** [`docs/specs/agent-fleet.md`](../docs/specs/agent-fleet.md); decisions in ADR-0001 to ADR-0006. Each group names the spec sections it delivers.

Terms: **A0–A3** are autonomy levels (spec §9); **M1–M3** are milestones (ROADMAP.md); Ada is the engineering agent, Boole the operations agent.

## v1 Requirements

### Repository protection (GHE) — spec §13

- [ ] **GHE-01**: `hyprn-labs` is on the GitHub Team plan with `CODEOWNERS` and a ruleset on `main` in each repository: pull request required, human code-owner approval, stale approvals dismissed, no force push, no bypass for any App.
- [ ] **GHE-03**: GitHub refuses a merge or push to `main` by any agent App, and an agent's approval does not satisfy the rule.

### Agent policy (POL) — spec §13

- [ ] **POL-01**: The Claude Code organization policy lives in `agents/policy/managed-settings.json` with explicit allow, ask and deny lists (routine work allowed, risky actions asked, merging and pushing to `main` denied) and the pinned herdr hooks allowed; the Team Owner applies it in the admin console and `runbooks/agents/claude.md` records each change.
- [ ] **POL-02**: The sandbox network allowlist for agent shell commands is part of that policy; a request to any other host fails inside the sandbox.
- [ ] **POL-03**: `strictKnownMarketplaces` accepts only the `hyprn-agents` marketplace.
- [ ] **POL-04**: Claude Code deny rules refuse merging pull requests, pushing to `main` and force pushing in every `hyprn-labs` repository.

### Egress control (EGR) — spec §13

- [ ] **EGR-01**: A filtering forward proxy (Squid) on the agent host is the only way out for agent users and their containers: host firewall rules by Linux user send their traffic to it and drop direct outbound connections; DNS stays allowed; each destination is logged per agent to Cloud Logging without blocking (observe mode).
- [ ] **EGR-02**: The proxy enforces a domain allowlist reviewed in `agents/policy/egress-allowlist.txt`, built from observed traffic; any other domain is refused and logged.
- [ ] **EGR-03**: Operations run containers are enforced from their first run: each reaches only the gateway and the hosts of its loop's declared tools, from an allowlist in the loop definition; any other destination is refused and logged.

### Detection and account safeguards (DET, SEC, DOC) — spec §13

- [ ] **DET-01**: Data Access audit logs are on for Secret Manager in `hyprn-agents`; a Cloud Monitoring alert emails `gcp-admins@hyprn.ai` when a secret is read by any principal other than `hyprn-agents-host` and `hyprn-agents-wake` (and the controller and gateway identities once they exist), or when a secret is created, deleted or given a new reader.
- [ ] **DET-02**: A Cloud Monitoring alert emails `gcp-admins@hyprn.ai` on any IAM policy change in `hyprn-agents`; folder-level changes on `agents` reach the same alert through a log sink into `hyprn-agents`. The group accepts mail from Google Cloud.
- [ ] **SEC-01**: A break-glass super admin exists with its own hardware security key and printed backup codes, both stored offline away from the owner's daily keys; it holds no standing Google Cloud role; `runbooks/agents/gcp.md` describes its use.
- [ ] **SEC-02**: `hyprn-labs` requires two-factor authentication for all members.
- [x] **DOC-01**: ADR-0003 records our own Slack channel server.

### Acceptance and isolation (ACC) — spec §13

- [ ] **ACC-01**: Permission relay works in Slack: a risky action in Ada's session asks the owner; `yes <id>` lets it proceed, `no <id>` stops it, and a reply from anyone else is rejected.
- [ ] **ACC-02**: Messages from non-allowlisted Slack senders get no reaction, never reach a session and do not wake the host.
- [ ] **ACC-03**: Merge, push to `main`, force push and bypass mode are refused in Ada's session.
- [ ] **ACC-04**: An organization-wide IAM search shows every `hyprn-agents` principal with exactly its declared roles and none outside the project.
- [ ] **ACC-05**: The host holds no user cloud credentials, no key files and no staging or prod roles or secrets.
- [ ] **ACC-06**: The wake identity is refused everything but get, start and stop on the host; the wake service holds no Slack connection while the host runs; the host keeps its disk across idle stops.
- [ ] **ACC-07**: Ada and Boole cannot reach each other's homes, secrets, containers, tokens or bots.
- [ ] **ACC-08**: One command (`tests/agents/run.sh`) runs every check delivered so far and writes a dated record to `runbooks/agents/`; each later phase adds its checks to it.
- [ ] **ACC-09**: The controller and gateway identities hold exactly their declared roles; the gateway is unreachable from the internet; a run's container holds only its loop's credentials.
- [ ] **ACC-10**: At the end of M3, the full check run passes with the egress allowlist enforced, and its dated record is kept.

### Engineering workflow (GH, EFF, COK, OBS) — spec §2, §4, §11

- [ ] **GH-01**: From a Slack task, Ada creates `agent/ada/<slug>`, pushes it and opens a draft pull request authored by `ada-agent-hyprn[bot]` that states what changed and how it was verified; Ada does not merge it.
- [ ] **GH-02**: A worktree helper creates one worktree per task with its own port block, Compose project and test database, and removes the worktree and local branch once the pull request is merged or closed.
- [x] **GH-03**: The interim machine account is removed and its secret deleted.
- [ ] **EFF-01**: Host provisioning installs the toolchains the product repositories pin, so a task starts without installing tools.
- [ ] **EFF-02**: Package and Docker layer caches persist per agent across tasks and host stops.
- [ ] **COK-01**: The owner's laptop runs herdr as the cockpit: local panes for the owner's seats (Claude Code, and Codex on the ChatGPT seat), one Claude Code configuration directory per seat, and the agent host added as a herdr machine over IAP SSH. Remote Control is enabled for the owner's own seat.
- [ ] **COK-02**: On the agent host, herdr replaces the tmux wrapper as each engineering agent's session runtime: pinned release with checksum, started by systemd under the agent's Linux user, resumed after boot, its hooks allowed by POL-01, agent-to-agent prompting off; Slack, the wake service and the checks keep working.
- [ ] **OBS-01**: Ada's Claude Code telemetry reaches a collector on the host; a daily report (tokens, estimated cost, seat-limit hits) is posted to Slack.

### Control plane (CP, RT, COST) — spec §4, §5, §6, §7

- [ ] **CP-01**: The model gateway (LiteLLM on Cloud Run, internal ingress, Cloud SQL) serves Fireworks, Anthropic and OpenAI to the host and the controller, with one virtual key and dollar budget per loop and cost logs per run.
- [ ] **CP-02**: The fleet controller runs a queue and dispatcher with run state (its own database on the gateway's Cloud SQL), idempotency keys and a run log; it starts the host when runs are pending.
- [ ] **CP-03**: A run can request approval as a tool call, be parked for hours without holding compute, and resume on the owner's answer to the agent's Slack bot; the controller holds the operations agents' Socket Mode connections.
- [ ] **CP-04**: Budgets stop runs over their limit; a kill switch per loop, per agent and fleet-wide takes effect within a minute.
- [ ] **CP-05**: Loops are declared in `agents/loops/<name>.yaml` (trigger, steps, agent steps, tools, autonomy per action, budget, eval set, promotion rule, owner); the dispatcher runs only registered loops.
- [ ] **CP-06**: A credential broker gives each run only the credentials its loop declares, short-lived where the tool allows, from Secret Manager.
- [ ] **RT-01**: A run runner on the host pulls pending runs and executes each as the agent's Linux user in a fresh rootless container behind the egress proxy, on an open model at Fireworks through the gateway; switching to Claude or OpenAI changes the binding only; running containers keep the host from idling off.
- [ ] **OPS-01**: Boole's runtime identities exist: Linux user `boole`, Slack app `Boole (AI agent)` with its tokens in Secret Manager, gateway key; declared in Terraform where the vendor allows.
- [ ] **COST-01**: The owner sets a revised monthly budget for `hyprn-agents` covering the gateway, Cloud SQL, Workspace licences and host wake-ups.

### Boole and the meeting loop (OPS, LOOP) — spec §2, §5, §7

- [ ] **OPS-02**: Boole's remaining identities exist: Workspace user `boole@agents.hyprn.ai` (created by hand, automated later by FLT-02) and a Notion integration limited to the meetings database, its token in Secret Manager.
- [ ] **LOOP-01**: Meeting notes reach the Notion meetings database from Granola; the controller polls it every 5 minutes and queues one run per new meeting page.
- [ ] **LOOP-02**: The meeting loop extracts decisions and actions, proposes Notion updates and posts a summary in Slack; Notion writes need the owner's approval (A1).
- [ ] **LOOP-03**: The loop handles at least 10 real meetings in two weeks within a budget of 30 USD a month, with cost per run visible.

### Learning (OPS, LRN) — spec §9, §10

- [ ] **OPS-03**: Boole's GitHub App `boole-agent-hyprn` is installed on `hyprn-platform` only, with contents and pull-request access; its tokens come from the credential broker.
- [ ] **LRN-01**: Reactions, replies and approval decisions in Slack are stored with their run as feedback.
- [ ] **LRN-02**: The meeting loop has an eval set of at least 20 cases from real runs and feedback, and a regression suite; the eval runner runs on the host through the gateway.
- [ ] **LRN-03**: An improvement run opens a draft pull request with prompt and skill changes; the eval runner posts its result on it; only passing changes reach the owner, who merges.
- [ ] **LRN-04**: The meeting loop moves from A1 to A2 by a reviewed change once its eval pass rate is at least 90 % over its last 10 runs and owner corrections average fewer than one per meeting.

### Fleet as code and onboarding (FLT) — spec §12

- [ ] **FLT-01**: `agents/fleet.yaml` declares every agent and replaces `agents/host/agents.txt` and `agents/wake/wake.json`; Terraform, provisioning, the controller and the checks read it.
- [ ] **FLT-02**: Workspace users `<name>@agents.hyprn.ai` are created and configured by a service account holding the Workspace user-management admin role; Ada's address moves from a group to a user.
- [ ] **FLT-03**: The agent's Slack app is created from the reviewed manifest with a generated icon; the bot token goes straight into Secret Manager; the Socket Mode token is a documented manual step.
- [ ] **FLT-04**: The agent's GitHub App is created through the manifest flow; its key goes straight into Secret Manager; installation and bot IDs are discovered by API.
- [ ] **FLT-05**: An engineering agent's Claude Code sign-in can come from a `setup-token` token in Secret Manager if channels work with it; otherwise the interactive sign-in stays and the finding is recorded.
- [ ] **FLT-06**: `agents/fleet add <name> --kind engineering|operations` onboards a test agent of each kind within 15 minutes and about 8 human actions; the engineering test stops before the Claude seat invitation.
- [ ] **FLT-07**: `agents/fleet remove <name>` offboards an agent and prints the remaining manual steps.
- [ ] **FLT-08**: `runbooks/agents/onboarding.md` describes adding and removing agents and the one-time prerequisites.

## Deferred Requirements

- [x] **GHE-02**: GitHub App per agent with one-hour tokens (ADR-0005).
- **FLEET-01**: Further engineering agents on Claude seats. Trigger: Anthropic's answer on agent seats.
- **FLEET-04**: GitHub Issues as a task intake beside Slack. Trigger: queued work across agents.
- **FLEET-05**: Slack plan without the 10-app limit. Trigger: the fleet nears 10 apps.
- **TOOL-01**: Finance and banking (read-only) and e-signature (prepare-only) in `fleet add`. Trigger: the first loop that needs them.
- **WEB-01**: Webhook receiver for event triggers, with its own ADR. Trigger: polling no longer enough.
- **PLAT-01**: Staging and prod build-out per `docs/specs/cloud-platform.md`. Trigger: the product's local edition.
- **PLAT-02**: Re-run ACC-04 when staging and prod exist.

## Out of Scope

| Item | Reason |
|------|--------|
| Automating Claude seat invitations | No member API on the Team plan |
| Agents moving money or signing | Never delegated (spec §1, §7) |
| Product code in this repository | Belongs in `hyprn-mvp` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| POL-01 | Phase 1 | Pending |
| POL-02 | Phase 1 | Pending |
| POL-03 | Phase 1 | Pending |
| POL-04 | Phase 1 | Pending |
| GHE-01 | Phase 1 | Pending |
| GHE-03 | Phase 1 | Pending |
| EGR-01 | Phase 1 | Pending |
| DET-01 | Phase 1 | Pending |
| DET-02 | Phase 1 | Pending |
| SEC-01 | Phase 1 | Pending |
| SEC-02 | Phase 1 | Pending |
| DOC-01 | Phase 1 | Complete |
| ACC-01 | Phase 1 | Pending |
| ACC-02 | Phase 1 | Pending |
| ACC-03 | Phase 1 | Pending |
| ACC-04 | Phase 1 | Pending |
| ACC-05 | Phase 1 | Pending |
| ACC-06 | Phase 1 | Pending |
| ACC-08 | Phase 1 | Pending |
| GH-01 | Phase 2 | Pending |
| GH-02 | Phase 2 | Pending |
| GH-03 | Phase 2 | Complete |
| EFF-01 | Phase 2 | Pending |
| EFF-02 | Phase 2 | Pending |
| COK-01 | Phase 2 | Pending |
| COK-02 | Phase 2 | Pending |
| OBS-01 | Phase 2 | Pending |
| ACC-09 | Phase 3 | Pending |
| CP-01 | Phase 3 | Pending |
| CP-02 | Phase 3 | Pending |
| CP-03 | Phase 3 | Pending |
| CP-04 | Phase 3 | Pending |
| CP-05 | Phase 3 | Pending |
| CP-06 | Phase 3 | Pending |
| RT-01 | Phase 3 | Pending |
| EGR-03 | Phase 3 | Pending |
| OPS-01 | Phase 3 | Pending |
| COST-01 | Phase 3 | Pending |
| ACC-07 | Phase 4 | Pending |
| OPS-02 | Phase 4 | Pending |
| LOOP-01 | Phase 4 | Pending |
| LOOP-02 | Phase 4 | Pending |
| LOOP-03 | Phase 4 | Pending |
| OPS-03 | Phase 5 | Pending |
| LRN-01 | Phase 5 | Pending |
| LRN-02 | Phase 5 | Pending |
| LRN-03 | Phase 5 | Pending |
| LRN-04 | Phase 5 | Pending |
| FLT-01 | Phase 6 | Pending |
| FLT-02 | Phase 6 | Pending |
| FLT-03 | Phase 6 | Pending |
| FLT-04 | Phase 6 | Pending |
| FLT-05 | Phase 6 | Pending |
| FLT-06 | Phase 6 | Pending |
| FLT-07 | Phase 6 | Pending |
| FLT-08 | Phase 6 | Pending |
| EGR-02 | Phase 7 | Pending |
| ACC-10 | Phase 7 | Pending |

**Coverage:** 58 v1 requirements, all mapped.

---
*Last updated: 2026-10-13 after the document review*
