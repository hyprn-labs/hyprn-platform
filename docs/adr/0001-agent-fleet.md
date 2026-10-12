---
status: accepted
date: 2026-10-12
decision-makers: Owner
---

# ADR-0001: Agent fleet — background coding agents on Claude Team seats in a separate project

## Context and Problem Statement

HYPRN engineering wants background AI coding agents that behave like team members: they take tasks, work on a branch and open draft pull requests that humans review and merge. They are steered from Slack and should deliver the most tokens per dollar. The question is which licences and identities they use, where they run, how they are controlled, and how this fits the platform specification ([cloud-platform.md](../specs/cloud-platform.md)): section 3 rules out a standing third environment, and section 6.4 gives agents no privileged path.

## Decision Drivers

- Tokens per dollar.
- Agents work like team members: tasks in, draft pull requests out; humans review and merge; agents never merge or deploy.
- No route from an agent to staging or prod secrets, registries, Terraform state or deployments.
- Every seat, key and account is used within its vendor's terms.
- Reviewable manual setup first, Terraform once the setup is confirmed.
- Nothing secret in Git.

## Considered Options

- Licensing: **L1** one Claude Team seat per agent with API-key overflow; **L2** API keys only; **L3** OpenAI seats for agents.
- Placement: **P1** a dedicated Google Cloud project `hyprn-agents`; **P2** inside the staging project; **P3** engineers' laptops.
- GitHub identity: **G1** one GitHub App per agent; **G2** one machine user per agent.
- Slack control: **S1** Claude Code channels with an audited Slack channel plugin from our own marketplace; **S2** Anthropic's hosted Slack integration.

## Decision Outcome

Chosen: **L1, P1, G1, S1**.

### 1. Licensing

- The founders' own work runs on OpenAI (ChatGPT Business / Codex), one seat per named person. OpenAI's agreement provisions each account to a single end user and forbids shared credentials, so agents get no OpenAI seats.
- Each agent has its own Claude Team seat and uses only the unmodified Claude Code CLI, signed in with that seat through Anthropic's own sign-in. Third-party harnesses never use a subscription sign-in; they use API keys.
- A seat is an identity plus a usage quota, not a role. Roles come from instructions (`agents/roles/`) and can change.
- The platform owner is the Team Owner and also holds a seat; this covers the plan's two-seat minimum.
- Overflow: the Team plan's monthly API credits (pooled per seat, capped at 500 USD a month) through an API key for the Agent SDK or Managed Agents. They do not cover Claude Code. Optional low-cost tier for low-stakes tasks: open-weight models through an API key.
- Extra usage is not enabled at first: an agent at its seat limit waits for the reset. This keeps the first measurement clean.
- Compliance status: Anthropic support's assistant indicated that subscription sign-in fits ordinary Claude Code use for one's own development, and passed the request for a formal answer to its human team. The setup as described there has one operator, the platform owner, driving the agent. A second agent is added only after a human answer confirms seat assignment to an agent identity, and any change to who drives agents is checked against that answer first.

### 2. Identities per agent

| Where | Identity |
|---|---|
| Email | `<name>@agents.hyprn.ai`, a Google Group on the secondary domain; members are the founders; conversations visible to members only |
| Claude | Team seat invited with email-code sign-in; `agents.hyprn.ai` is an allowed domain; operated from a dedicated browser profile |
| Slack | One app per agent, `<Name> (AI agent)`, Socket Mode (outbound only), icon the agent's initial on brand orange |
| GitHub | One GitHub App per agent, `hyprn-<name>`, committing as `hyprn-<name>[bot]` (App names are unique across GitHub) |
| Host | One Linux user `<name>` on the agent host |

Every display name ends with "(AI agent)". Agent first names are allowed in these per-agent identities only. This is a deliberate exception to the naming rule in [`conventions/`](../../conventions/README.md): an agent name is a persona, not a person. Cloud resources stay role-named (`hyprn-agents-host-01`, `hyprn-agents-host`).

### 3. Project `hyprn-agents`

- Its own project `hyprn-agents` (a random suffix only if the ID is taken) in its own folder, under the same organization and billing account as staging and prod.
- It is engineering tooling, not an environment in the sense of specification section 3: no product workload, no product data, no deployment authority. The "no standing third environment" rule is unaffected.
- Its principals hold no role outside the project, and no staging or prod principal holds a role inside it. Grants at organization or folder level flow down, so isolation is checked with an organization-wide IAM search and re-checked when staging and prod are created.
- Default service accounts get no automatic Editor role, service-account keys are not created, and a monthly budget of 100 EUR alerts at 50, 80 and 100 %.
- Set up manually with reviewed `gcloud` steps recorded in [`runbooks/agents/`](../../runbooks/agents/README.md), then codified in [`infra/agents/`](../../infra/agents/README.md) with its own state and imported.

### 4. Agent host

Machine size and always-on operation superseded by [ADR-0002](0002-agent-host-on-demand.md): `t2d-standard-8` on demand, woken from Slack.

- One VM `hyprn-agents-host-01`: `e2-standard-4`, 100 GB balanced disk, Debian 12, Shielded VM, no public IP. SSH only through IAP with OS Login; project-wide SSH keys blocked; outbound through Cloud NAT. Resized from measured build and test load.
- One Linux user per agent with a private home and no sudo, and one rootless Docker per user. The Claude Code sandbox covers shell commands only (its file tools are outside it), so separate Linux users are the boundary between agents; the shared `docker` group would be root-equivalent.
- Agent users cannot reach the metadata server. A root-owned helper fetches each agent's secrets from Secret Manager with the VM identity and writes them readable only by that agent.
- Claude Code is signed in on the host with `/login` as each agent user; its credentials stay in that user's home.
- One persistent session per agent, in tmux under systemd.
- One task = one branch `agent/<name>/<slug>` = one git worktree = one draft pull request. Ports, Docker Compose project names and test databases are set per worktree through environment variables. The product's support for these overrides is product work, outside this decision.
- No production credentials on the host.

### 5. GitHub

- GitHub Team plan: draft pull requests, protected branches and enforced code owners on private repositories need it.
- Each agent App has Contents read/write, Pull requests read/write and Metadata read; no Workflows and no Administration permission; installed on selected repositories only. Its private key is held in the password manager and Secret Manager; the host mints one-hour installation tokens.
- Contents write also allows merging, so a ruleset on `main` is the control: pull request required, approval from code owners that are human teams only, stale approvals dismissed, no force push, no bypass for any App. Signed commits are not required for now.
- Agents can open pull requests only once the repositories they work on exist on GitHub.

### 6. Slack control

- Each agent runs one persistent Claude Code session with a Slack channel plugin (Claude Code channels, research preview).
- The Team Owner enables channels and sets the Claude Code policy once, organization-wide, in the admin console: `channelsEnabled`, `allowedChannelPlugins` (our marketplace and plugin), `strictKnownMarketplaces` and `disableBypassPermissionsMode`. A reviewed copy lives in [`agents/policy/`](../../agents/policy/README.md).
- The community Slack plugin is audited and vendored into [`agents/marketplace/`](../../agents/marketplace/README.md) with its licence and upstream commit.
- Sender allowlist: the platform owner's Slack user ID only. Other senders' messages are dropped before they reach the session. The same allowlist applies to permission replies. Agents are invited only to their working channels.
- Permission rules and the sandbox are always on; risky actions are relayed to Slack for approval; skip-all-permissions mode is disabled.

### 7. Measurement

During the first week with the first agent: per-agent token and cost metrics from Claude Code's OpenTelemetry export to a collector on the host, the Team admin analytics and spend report, and a daily log of seat-limit hits. The owner then decides on the data, with no preset thresholds, between Standard and Premium seats, seats and API keys, and when to add the next agent. That decision is recorded in a follow-up ADR.

### Consequences

- Good: agents hold no staging or prod authority by construction; each agent's actions are attributable to its own identities; the seat model gives predictable cost.
- Good: every privileged step is a reviewed manual step now and Terraform later.
- Bad: at a seat limit an agent pauses until the reset.
- Bad: channels are a research preview and may change; we maintain the vendored plugin ourselves.
- Bad: one host is one failure domain for all agents; the host can be rebuilt from this repository plus the secret store.
- Neutral: GitHub work waits until the repositories are published.

### Confirmation

Checks in [`tests/agents/`](../../tests/agents/README.md), run before an agent starts work and after each change to the host or the project:

- `hyprn-agents` principals hold no role outside the project (organization-wide IAM search).
- An agent user cannot reach the metadata server, read another agent's home, or use another agent's Docker.
- `--dangerously-skip-permissions` is refused.
- A non-allowlisted Slack sender is ignored, and a non-allowlisted approval is rejected.
- An agent App cannot merge a pull request or push to `main`.
- No user credentials, key files or staging and prod roles are present on the host.

## Pros and Cons of the Options

- **L1** Good: subscription price per token; per-agent identity. Bad: seat limits; the formal answer on agent seats is still pending.
- **L2** Good: no seat question; pay per use. Bad: higher cost at sustained use.
- **L3** Bad: OpenAI seats are tied to one named person.
- **P1** Good: isolation from staging and prod is an IAM property. Bad: one more project to govern.
- **P2** Bad: puts agents inside a deployment authority boundary.
- **P3** Bad: not persistent; mixes agent and personal credentials.
- **G1** Good: short-lived tokens; no paid member seat; fine-grained permissions. Bad: App names must be unique across GitHub.
- **G2** Bad: GitHub's terms allow one free machine account per person; each member takes a paid seat; long-lived credentials.
- **S1** Good: runs on our host with our worktrees and tests; sender allowlist; permission relay. Bad: research preview; community plugin to maintain.
- **S2** Bad: runs in a vendor-hosted sandbox, not on our host.

## More Information

Vendor capabilities checked against official documentation on 2026-10-12:

| Fact | Status | Source |
|---|---|---|
| Channels: Owner enables them on Team; custom plugins need `allowedChannelPlugins`; senders are allowlisted; development flag is interactive only | Checked | [Channels](https://code.claude.com/docs/en/channels), [reference](https://code.claude.com/docs/en/channels-reference) |
| Permission relay to the channel from Claude Code 2.1.234; anyone who can reply can approve | Checked | [Channels reference](https://code.claude.com/docs/en/channels-reference) |
| Marketplace plugin sources can be pinned to a full commit SHA; `strictKnownMarketplaces`, `enabledPlugins` | Checked | [Marketplaces](https://code.claude.com/docs/en/plugins/marketplace-reference), [plugins for organizations](https://code.claude.com/docs/en/plugins/org) |
| Sandbox covers shell commands only; `disableBypassPermissionsMode` | Checked | [Sandboxing](https://code.claude.com/docs/en/sandboxing), [permissions](https://code.claude.com/docs/en/permissions) |
| Subscription sign-in is for ordinary Claude Code use; Agent SDK products should use API keys | Checked; applicability to agent seats pending Anthropic's answer | [Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance) |
| Team API credits: 20/100 USD per Standard/Premium seat, pooled, capped at 500 USD, not for Claude Code | Checked | [API credits for subscribers](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers) |
| Team plan: two-seat minimum; Claude Code included in every seat | Checked | [Team plan](https://support.claude.com/en/articles/9266767-what-is-the-team-plan) |
| OpenTelemetry token and cost metrics; whether cost equals API price for subscribers | Metrics checked; cost meaning assumed | [Monitoring](https://code.claude.com/docs/en/monitoring-usage) |
| GitHub Apps: one-hour tokens; names unique; Contents write allows merge | Checked | [Installation tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app), [permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps) |
| Protections, rulesets and code owners on private repositories need a paid plan | Checked | [Rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) |
| Whether another App's approval counts toward required reviews | Assumed possible; code owners are human teams only | — |
| IAP TCP forwarding from `35.235.240.0/20`; OS Login; Cloud NAT for no-public-IP VMs | Checked | [IAP TCP forwarding](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding), [Cloud NAT](https://docs.cloud.google.com/nat/docs/overview) |
| Default service accounts may get Editor unless the organization policy prevents it | Checked | [Service account types](https://docs.cloud.google.com/iam/docs/service-account-types) |
| Slack Socket Mode needs no public URL; Slack Free allows 10 apps | Checked | [Socket Mode](https://docs.slack.dev/apis/events-api/using-socket-mode), [Free plan limits](https://slack.com/help/articles/27204752526611-Feature-limitations-on-the-free-version-of-Slack) |

The ordered tasks are in [`docs/plans/agent-fleet.md`](../plans/agent-fleet.md).
