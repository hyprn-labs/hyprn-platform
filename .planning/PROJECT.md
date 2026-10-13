# hyprn-platform

## What This Is

hyprn-platform is HYPRN's cloud platform repository: Terraform, cloud identities, governance, runbooks and the agent fleet. Products such as HYPRN MVP live in their own repositories (`hyprn-mvp`). Today the live part of the platform is the engineering agent Ada, steered from Slack, delivering draft pull requests on GitHub. The target is a fleet of engineering and operations agents described in `docs/specs/agent-fleet.md`.

## Core Value

Agents do HYPRN's engineering and operations work — on request and on their own triggers — safely, with costs known, and they get better from feedback; adding an agent is one command.

## Milestones

Target: `docs/specs/agent-fleet.md`; decisions in ADR-0001 to ADR-0006 (ADR-0006 proposed). Phases and requirement IDs: `ROADMAP.md`, `REQUIREMENTS.md`.

- **M1 — Safe engineering agent** (Phases 1–2): enforced policy, egress observation, alerts, account safeguards, proven safety checks; Slack-to-draft-PR from clean worktrees; herdr as cockpit and host runtime; Ada telemetry.
- **M2 — Boole, the ops agent, with a learning meeting loop** (Phases 3–5): the second agent, on open models at Fireworks with an API key; gateway, controller, loop registry, credential broker, approvals that wait, budgets, kill switch; Granola → Notion → loop → Slack; GitHub Team plan ruleset; feedback, evals and improvement pull requests.
- **M3 — Scale the fleet** (Phases 6–7): `agents/fleet.yaml`, `fleet add` and `remove` for both kinds of agent, Workspace users per agent, egress allowlist enforced, full acceptance run.

**Success metric:** Ada ships draft pull requests from Slack tasks; Boole's meeting loop handles at least 10 real meetings in two weeks within 30 USD a month and has merged one evidence-backed improvement; a test agent of each kind is onboarded and offboarded with `fleet` within 15 minutes and about 8 human actions (Claude seat steps excepted); `tests/agents/run.sh` passes in full.

## Requirements

### Validated

- Google Cloud organization and bootstrap applied: folder `agents`, projects `hyprn-bootstrap` and `hyprn-agents`, remote state, 14 organization policies, budget of 100 EUR with alerts at 50, 80 and 100 %, admin group holding the cloud admin roles, domain-wide grants removed (2026-10-12).
- Agent infrastructure from `infra/agents/`: custom network, Cloud NAT, host `hyprn-agents-host-01` (`t2d-standard-8`, on demand), wake VM `hyprn-agents-wake-01` (`e2-micro`), Secret Manager secrets; plan shows no changes.
- Host provisioning: one Linux user per agent, rootless Docker, metadata server unreachable for agent users, root-owned secret loader, idle stop after 30 minutes, persistent tmux session under systemd. Host checks: 20 pass.
- Ada signed in with a Claude Team seat; role instructions in `agents/roles/`.
- Slack control: own channel server, plugin `slack@hyprn-agents` from the root-owned local marketplace, secrets in Secret Manager, sender allowlist; organization settings `channelsEnabled`, `allowedChannelPlugins` and `disableBypassPermissionsMode` set.
- Wake from Slack: a message to a stopped host reaches Ada 50 s after the start request.
- GitHub (ADR-0005): App `ada-agent-hyprn` installed on all `hyprn-labs` repositories; a root broker mints one-hour installation tokens; Ada commits as `ada-agent-hyprn[bot]`. Repository `hyprn-labs/hyprn-platform` (private).

### Active

Requirement IDs live in `.planning/REQUIREMENTS.md`, grouped by the spec sections they deliver.

- [ ] M1: policy, egress observation, detection, safeguards, safety checks (POL, EGR-01, DET, SEC, ACC-01..06, ACC-08); engineering workflow (GH, EFF, COK, OBS).
- [ ] M2: control plane (CP, RT, OPS-01, COST, ACC-09); Boole and the meeting loop (OPS-02, LOOP, ACC-07); learning (GHE-01, GHE-03, OPS-03, LRN).
- [ ] M3: fleet as code (FLT); hardening and acceptance (EGR-02, ACC-10).

### Out of Scope

- Staging and prod environments, deployment contract, host reconciler, product delivery pipeline — specified in `docs/specs/cloud-platform.md`; they follow the product's local edition.
- Further engineering agents on Claude seats — they wait for Anthropic's answer on agent seats; API-key agents such as Boole are not gated by it.
- Automating Claude seat invitations — the Team plan has no member API.
- Agents moving money or signing — never delegated.
- Product-side support for per-worktree port, Compose project and database overrides — product work in `hyprn-mvp`.
- Signed commits — not required for now.
- Product code in this repository — it belongs in `hyprn-mvp`.

## Context

- Two Claude Team seats cover the platform owner and Ada; extra usage is off so seat-limit hits are visible.
- The agent host runs on demand (ADR-0002), about 75–80 EUR per month at 8 hours a day on 22 days, inside the 100 EUR budget. M2 adds the gateway, Cloud SQL, Workspace licences and host wake-ups for runs; the owner sets a revised budget in Phase 3 (COST-01).
- The GitHub organization `hyprn-labs` is on the Free plan: no ruleset on private repositories. Until the Team plan arrives in Phase 5, only Ada, whose Claude Code deny rules block merging and pushing to `main`, holds write access.
- The Slack channel plugin is our own audited server (ADR-0003).
- `docs/specs/cloud-platform.md` defines staging and prod; none of it is provisioned. Its rule that agents get no privileged path and that `hyprn-agents` is tooling, not an environment, applies here.
- Residual risk accepted: the channel server runs as the agent user, so a compromised agent could alter its installed copy or use its own bot token; the allowlist protects the session from other people's messages and the Linux user boundary limits reach.

## Constraints

- **Authority**: Never apply infrastructure changes or create cloud resources without the platform owner's explicit authorization for that exact plan; plans are reviewed before apply.
- **Secrets**: No credentials, Terraform state or plan files, secret tfvars or service-account keys in Git; secret values move only through standard input or the password manager, never argv, chat or shell history.
- **Separation**: `hyprn-agents` principals hold no role outside the project, and no staging or prod principal holds a role inside it; no production credentials on the agent host.
- **Control surface**: The Claude admin console is the enforcing source of agent policy; changes are reviewed in `agents/policy/` first, applied by the Team Owner, and recorded in `runbooks/agents/claude.md`.
- **Network**: Outbound-only connections for agents, the host and the controller; the gateway has internal ingress only; any public endpoint needs its own ADR.
- **Cost**: Monthly budget on `hyprn-agents` with alerts at 50, 80 and 100 %; one gateway budget per loop.
- **Licensing**: Seats only for human-directed sessions of their own agent; API keys for autonomous loops; Claude subscriptions only in Anthropic's own applications.
- **Identity**: Every agent display name ends with "(AI agent)"; cloud resources stay role-named; identities follow `conventions/README.md`.
- **Writing**: Plain, assertive English; the platform owner is referred to as "the platform owner".

## Key Decisions

Decisions below are locked unless marked proposed. Do not plan work that reverses them.

<decisions>

### ADR-0001: Agent fleet on Claude Team seats in a separate project (as amended by ADR-0002, ADR-0003, ADR-0005 and, once accepted, ADR-0006)

- **Licensing:** Engineering agents use one Claude Team seat each and the unmodified Claude Code CLI. No OpenAI seats for agents. Third-party harnesses use API keys only. Roles come from `agents/roles/`. Further Claude-seat agents wait for Anthropic's answer on agent seats.
- **Identities:** Every agent display name ends with "(AI agent)". Per agent: Workspace user in the agents domain (ADR-0006; Ada still a group until Phase 6), Slack app on Socket Mode, GitHub App, Linux user on the host.
- **Project `hyprn-agents`:** Own project and folder, same organization and billing account as staging and prod; engineering tooling, not an environment; no service-account keys; Terraform in `infra/agents/`.
- **Agent host:** Debian 12 Shielded VM, no public IP, SSH only through IAP with OS Login; one Linux user per agent with private home, no sudo, rootless Docker; metadata server unreachable for agents; root-owned secret loader; one task = one branch `agent/<name>/<slug>` = one worktree = one draft pull request; no production credentials. Session runtime moves from tmux to herdr (ADR-0006).
- **Slack control:** Engineering agents run a persistent Claude Code session with our Slack channel plugin; sender allowlist is the platform owner only, also for approvals; permission rules and sandbox always on; bypass mode disabled.

### ADR-0002: Agent host on demand, woken from Slack

- Host `t2d-standard-8`, stops after 30 minutes without work or SSH; sessions resume on boot.
- Wake service on `hyprn-agents-wake-01` connects to an agent's Slack app only while the host is stopped and starts it on the allowlisted sender's message; its identity can only get, start and stop the host.

### ADR-0003: Our own Slack channel server for agents

- `agents/marketplace/plugins/slack/server.py` is the plugin; the community candidates failed the audit.

### ADR-0005: Agent GitHub access through a GitHub App with one-hour tokens (supersedes ADR-0004)

- One GitHub App per agent with Contents and Pull requests, no webhook; Ada's App on all repositories. A root broker mints one-hour installation tokens from the App key in Secret Manager. Agents never merge or deploy.

### ADR-0006 (proposed): Agent-first operating model

- Seats for human-directed work, API keys for autonomous loops; two kinds of agent (engineering on seats, operations on API keys); registry of agents and loops as code; thin control plane on the always-on VM with run state in the gateway's Cloud SQL; LiteLLM gateway on Cloud Run; polling before webhooks; autonomy levels A0–A3 earned from evals; herdr as host runtime and cockpit; operations agents get repository write access only behind the Team plan ruleset.

</decisions>

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| One Claude Team seat per engineering agent, unmodified Claude Code | Licensing clarity; roles come from instructions | Further seat agents wait for Anthropic's answer |
| Separate project `hyprn-agents`, no role outside it | Agents hold no path to staging or prod | Proven by ACC-04 in Phase 1 |
| Host on demand with always-on wake service | Larger host at about 75–80 EUR per month | Good: wake verified at 50 s |
| Own Slack channel server with root-written sender allowlist | Community candidates failed the audit | Good: in service (ADR-0003) |
| GitHub App per agent with one-hour tokens | No long-lived token, seat or second factor; works on the Free plan | Good: host checks pass (ADR-0005) |
| Deny rules on merge and push to `main` until the ruleset | Free plan cannot protect private repositories | Phase 1; ruleset in Phase 5 |
| Second agent on API keys and open models (Boole) | Tests the whole loop stack without a second seat | M2 (ADR-0006, proposed) |
| Telemetry and gateway cost instead of a measured week | Continuous data, reviewed monthly | Phases 2–3 |

---
*Last updated: 2026-10-13 after the document review*
