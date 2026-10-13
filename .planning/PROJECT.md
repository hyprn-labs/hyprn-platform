# hyprn-platform

## What This Is

hyprn-platform is the company's cloud platform repository: Terraform, cloud identities, governance, runbooks and operations for HYPRN products. It holds no product code; products such as HYPRN MVP live in their own repositories (for example `hyprn-mvp`). Today the live part of the platform is the agent fleet: Ada, a background coding agent that the platform owner instructs from Slack and that delivers draft pull requests on GitHub.

## Core Value

The platform owner gives Ada a task in Slack and receives a reviewable draft pull request, and no path exists from the agent fleet to staging or prod credentials.

## Current Milestone: Agent fleet operational

**Goal:** Ada works from Slack, opens draft pull requests on GitHub, runs under enforced Claude Code policy, and the first-week usage measurement drives the seat decision.

**Success metric:** The platform owner gives Ada a task in Slack and receives a reviewable draft pull request by `ada-agent-hyprn[bot]`, with no path from the agent fleet to staging or prod credentials, and with a recorded seat decision after one measured week.

**Target work:**
- Claude Code policy, sandbox and egress allowlist enforced for agents, with deny rules for merge and push to `main`.
- The Slack-to-draft-pull-request path proven end to end, with the worktree helper.
- Acceptance and isolation checks run as repeatable tests and recorded.
- One measured week with Ada and a recorded seat decision.

## Requirements

### Validated

- Google Cloud organization setup and bootstrap applied: folder `agents`, projects `hyprn-bootstrap` and `hyprn-agents`, remote state, 14 organization policies, budget of 100 EUR with alerts at 50, 80 and 100 %, admin group holding the cloud admin roles, domain-wide grants removed (2026-10-12).
- Agent infrastructure applied from `infra/agents/`: custom network without a default network, Cloud NAT, host `hyprn-agents-host-01` (`t2d-standard-8`), wake VM `hyprn-agents-wake-01` (`e2-micro`), Secret Manager secrets; plan shows no changes.
- Host provisioning: one Linux user per agent, rootless Docker, metadata server unreachable for agent users, root-owned secret loader, idle auto-stop after 30 minutes, persistent tmux session under systemd that survives reboot. Host checks: 18 pass.
- Ada signed in with a Claude Team seat; role instructions in `agents/roles/`.
- Slack control: own channel server in `agents/marketplace/plugins/slack/`, plugin `slack@hyprn-agents` installed from the root-owned local marketplace, secrets in Secret Manager, sender allowlist, organization settings `channelsEnabled`, `allowedChannelPlugins` and `disableBypassPermissionsMode` set.
- Wake from Slack verified: a message to a stopped host reaches Ada 50 s after the start request.
- GitHub access (ADR-0005): GitHub App `ada-agent-hyprn` on `hyprn-platform` and `hyprn-mvp`; a root broker mints one-hour installation tokens from the App key in Secret Manager; Ada commits as `ada-agent-hyprn[bot]`. Repository published to GitHub as `hyprn-labs/hyprn-platform` (private).

### Active

Requirement IDs and acceptance wording live in `.planning/REQUIREMENTS.md`. Summary:

- [ ] Enforced agent policy: permission rules, sandbox, egress allowlist, `strictKnownMarketplaces`, deny rules for merge and push to `main`, break-glass admin, organization 2FA, ADR-0003.
- [ ] GitHub workflow: Slack task to draft pull request by `ada-agent-hyprn[bot]`, worktree helper, removal of the interim machine account.
- [ ] Acceptance: permission relay, other-sender rejection, merge and push refusal, isolation and no-production-credentials checks as repeatable tests.
- [ ] Measurement: OpenTelemetry export, one week of daily reports, seat decision recorded in an ADR.

### Out of Scope

- Staging and prod environments, deployment contract, host reconciler, product delivery pipeline — they follow the product's local edition and are specified in `docs/specs/cloud-platform.md`.
- Agent #2 — gated on Anthropic's human answer on agent seats (ADR-0001 section 1).
- GitHub Team plan, ruleset on `main` and CODEOWNERS — a paid-plan and owner decision; tracked as deferred requirements. Until then, Claude Code deny rules are the control.
- Product-side support for per-worktree port, Compose project and database overrides — product work in `hyprn-mvp`.
- Signed commits — not required for now (ADR-0001 section 5).
- Product code in this repository — it belongs in `hyprn-mvp`.

## Context

- Two Claude Team seats cover the platform owner and Ada; extra usage is off at first so seat-limit hits are visible.
- The agent host runs on demand (ADR-0002) and costs about 75-80 EUR per month at 8 hours a day on 22 days, inside the 100 EUR budget.
- The GitHub organization `hyprn-labs` is on the Free plan: no ruleset or branch protection on private repositories, and the organization-wide 2FA requirement is not enabled. Ada's App can write to `hyprn-platform` and `hyprn-mvp`, so until a ruleset exists the only control against pushing to `main` is Claude Code policy.
- The Slack channel plugin is our own audited server, not a vendored community plugin. Both community candidates were rejected in the audit (ADR-0003).
- The platform specification (`docs/specs/cloud-platform.md`) defines the staging and prod build-out; none of it is provisioned. Its rule that agents get no privileged path and that `hyprn-agents` is engineering tooling, not an environment, applies here.
- Residual risk accepted: the channel server runs as the agent user, so a compromised agent could alter its installed copy or use its own bot token; the allowlist protects the session from other people's messages and the Linux user boundary limits reach.

## Constraints

- **Authority**: Never apply infrastructure changes or create cloud resources without the platform owner's explicit authorization for that exact plan; plans are reviewed before apply; staging and prod have separate authority.
- **Secrets**: No credentials, Terraform state or plan files, secret tfvars or downloaded service-account keys in Git; secret values move only through standard input or the password manager, never argv, chat or shell history.
- **Separation**: `hyprn-agents` principals hold no role outside the project, and no staging or prod principal holds a role inside it; no production credentials on the agent host.
- **Control surface**: The Claude admin console is the enforcing source of agent policy; changes are reviewed in `agents/policy/` first, applied by the Team Owner, and recorded in `runbooks/agents/`.
- **Network**: Outbound-only agent connections; no public endpoint for the host or the wake service.
- **Cost**: Monthly budget of 100 EUR on `hyprn-agents`, alerts at 50, 80 and 100 %; extra usage on Claude seats off at first.
- **Identity**: Every agent display name ends with "(AI agent)"; cloud resources stay role-named.
- **Writing**: Plain, assertive English; the platform owner is referred to as "the platform owner".

## Key Decisions

Decisions below are locked. Do not plan work that reverses them.

<decisions>

### ADR-0001: Agent fleet on Claude Team seats in a separate project (as amended by ADR-0002, ADR-0003 and ADR-0005)

- **Licensing (L1):** One Claude Team seat per agent, unmodified Claude Code CLI signed in with that seat. No OpenAI seats for agents. Third-party harnesses use API keys only. A seat is an identity plus quota, not a role; roles come from `agents/roles/`. The platform owner is Team Owner and holds a seat. A second agent is added only after Anthropic's human answer confirms seat assignment to an agent identity.
- **Identities:** Every agent display name ends with "(AI agent)". Per agent: email in the agents domain, Claude Team seat, Slack app on Socket Mode, GitHub identity, one Linux user on the host.
- **Project `hyprn-agents`:** Own project in its own folder, same organization and billing account as staging and prod. Engineering tooling, not an environment. No service-account keys. Budget 100 EUR with alerts at 50, 80, 100 %. Terraform in `infra/agents/`.
- **Agent host:** One Debian 12 Shielded VM `hyprn-agents-host-01`, 100 GB balanced disk, no public IP, SSH only through IAP with OS Login. One Linux user per agent, private home, no sudo, rootless Docker. Agent users cannot reach the metadata server. A root-owned helper fetches secrets and writes them readable only by that agent. One persistent session per agent in tmux under systemd. One task = one branch `agent/<name>/<slug>` = one worktree = one draft pull request. No production credentials on the host.
- **GitHub:** Target state is one GitHub App per agent with one-hour installation tokens, a `main` ruleset requiring pull request and human code-owner approval, no force push, no bypass. Agents never merge or deploy.
- **Slack control (S1):** One persistent Claude Code session per agent with a Slack channel plugin. Team Owner sets organization-wide: `channelsEnabled`, `allowedChannelPlugins`, `strictKnownMarketplaces`, `disableBypassPermissionsMode`. Sender allowlist is the platform owner's Slack user ID only, also for permission replies. Permission rules and sandbox always on; risky actions relayed to Slack; skip-all-permissions mode disabled.
- **Measurement:** First week with the first agent: OpenTelemetry export to a collector on the host, Team admin analytics, daily log of seat-limit hits. The platform owner then decides, with no preset thresholds, Standard versus Premium seats, seats versus API keys, and when to add the next agent; recorded in a follow-up ADR.
- **Confirmation checks:** No `hyprn-agents` principal role outside the project; agent user cannot reach metadata, another agent's home or another agent's Docker; skip-all-permissions refused; non-allowlisted Slack sender ignored and non-allowlisted approval rejected; agent cannot merge a pull request or push to `main`; no user credentials, key files or staging/prod roles on the host.

### ADR-0002: Agent host on demand, woken from Slack (supersedes ADR-0001 section 4 machine size and always-on operation only)

- Host is `t2d-standard-8` (8 physical cores, 32 GB), same disk, no public IP, and stops itself after 30 minutes with no agent work and no SSH session. Each agent's session resumes under systemd on boot.
- Wake service `hyprn-agents-wake-01` (`e2-micro`, always on, no public IP, outbound Socket Mode only) connects to an agent's Slack app only while the host is stopped. On a message from the allowlisted sender it replies that the agent is waking, starts the host and disconnects.
- Wake identity `hyprn-agents-wake` holds a custom role limited to get, start and stop on the host instance, plus log and metric writing.
- Confirmation: allowlisted sender wakes the host and the agent answers, others do not; wake service holds no Slack connection while the host runs; wake identity is refused any other action; the host keeps its disk across stops.

### ADR-0005: Agent GitHub access through a GitHub App with one-hour tokens (supersedes ADR-0004, completes ADR-0001 section 5)

- One GitHub App per agent, installed on selected `hyprn-labs` repositories; Contents and Pull requests read/write, Metadata read, no webhook.
- The App key is in the password manager and in Secret Manager (`<name>-agent-github-app-key`, host only). A root broker signs a JWT in memory and mints a one-hour installation token every 30 minutes and on each secret reload; Git and `gh` read the current token.
- Agents never merge or deploy. Until a ruleset protects `main`, Claude Code permission rules deny merging and pushing to `main`.

### ADR-0003: Our own Slack channel server for agents (supersedes the plugin choice in ADR-0001 section 6)

- The audit rejected both community candidates; `agents/marketplace/plugins/slack/server.py` is the plugin in service. The security requirements of ADR-0001 section 6 stand unchanged.

</decisions>

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| One Claude Team seat per agent, unmodified Claude Code | Licensing clarity; roles come from instructions, not seats | Pending: Anthropic answer gates agent #2 |
| Separate project `hyprn-agents`, no role outside it | Agents hold no path to staging or prod | Pending: acceptance check in Phase 3 |
| Host on demand with always-on wake service | Larger host at about 75-80 EUR per month instead of always-on cost | Good: wake verified at 50 s |
| Own Slack channel server with root-written sender allowlist | Community candidates failed the audit | Good: deployed and working; recorded in ADR-0003 |
| GitHub App per agent with one-hour tokens (ADR-0005), superseding the interim machine account (ADR-0004) | No long-lived token, seat, email or second factor; Apps work on the Free plan | Good: host checks pass; draft-pull-request test in Phase 2 |
| Claude Code deny rules on merge and push to `main` until a ruleset exists | Free plan cannot enforce rules on private repositories | Pending: Phase 1 |
| No preset thresholds for the seat decision | Measure first, then decide | Pending: Phase 4 |

---
*Last updated: 2026-10-12 after ingest and roadmap creation for milestone "Agent fleet operational"*
