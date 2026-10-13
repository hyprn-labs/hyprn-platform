# Agent fleet specification

Status: target. In service today: the engineering agent Ada (ADR-0001 to ADR-0005). Delivery order and current position: [`.planning/ROADMAP.md`](../../.planning/ROADMAP.md) — milestone **M1** safe engineering agent, **M2** operations agent Boole with a learning meeting loop, **M3** scaling the fleet. What exists now is described in each folder's README.

The agent fleet does HYPRN's engineering and operations work, on request and on its own triggers. This document is the single description of the target; decisions and trade-offs are in [ADR-0001](../adr/0001-agent-fleet.md) to [ADR-0006](../adr/0006-agent-first-operating-model.md).

**MUST** marks an acceptance requirement of the target. Other statements describe the design.

## 1. Operating model

- Recurring work is a **loop**: a trigger, a workflow with agent steps where judgment is needed, declared tools, an output and a human role (ADR-0006).
- **Human-directed** work — a person steering an agent from Slack or the cockpit — runs on subscription **seats**. **Autonomous** loops run on **API keys** through the model gateway. A seat MUST NOT run an autonomous loop.
- An agent's seat runs only that agent's sessions; people work on their own seats. Using agent seats as personal capacity waits for Anthropic's answer on agent seats.
- Agents propose; people decide what is irreversible. Code reaches `main` only through a person's merge. Agents MUST NOT move money or sign.
- The playbook — agents, loops, skills, policies — is code in this repository and changes by pull request.

## 2. Agents

| Kind | Does | Runtime | Agent |
|---|---|---|---|
| Engineering | Code changes as draft pull requests | Claude Code on a Claude Team seat, in herdr sessions under its Linux user | Ada |
| Operations | Loops over company knowledge and tools | A harness on an API key through the gateway, in a fresh rootless container per run under its Linux user; open models at Fireworks first | Boole |

Engineering agents work one task per branch `agent/<name>/<slug>`, in its own git worktree with its own port block, Docker Compose project and test database, and open a draft pull request from it. The worktree and local branch are removed once the pull request is merged or closed.

Each agent has one identity per system, named by [`conventions/`](../../conventions/README.md):

| System | Identity |
|---|---|
| Google Workspace | User `<name>@agents.hyprn.ai`; password and second factor in the company password manager. Ada's address is a Google group until its move to a user (M3) |
| Model access | A Claude Team seat (engineering) or a gateway key (operations) |
| Slack | Its own app and bot `<Name> (AI agent)`, Socket Mode |
| GitHub | Its own GitHub App `<name>-agent-hyprn` with one-hour tokens (ADR-0005); never a machine account. Engineering Apps are installed on all `hyprn-labs` repositories; an operations App only on the repositories its loops change (Boole: `hyprn-platform`) |
| Notion | Its own integration, limited to the pages it serves |
| Agent host | Its own Linux user with a private home and rootless Docker |

## 3. Runtimes

A runtime is a **harness × credential × model** binding declared per agent.

| Harness | Credential | Models | Used for |
|---|---|---|---|
| Claude Code | Claude Team seat | Claude | Human-directed engineering |
| Codex | ChatGPT Business seat of its named holder | OpenAI | The owner's own work |
| OpenCode or a workflow script | Fireworks or OpenAI API key through the gateway | Open models, OpenAI | Autonomous loops |
| Claude Agent SDK or Claude Code headless | Anthropic API key through the gateway | Claude | Autonomous loops needing Claude |

- Claude subscriptions are used only in Anthropic's own applications; third-party harnesses use API keys only.
- Claude Code is not pointed at non-Claude models.
- Changing an agent's model or provider MUST be a change of its binding only.
- In reserve, outside the fleet's core: Claude Code cloud sessions and Claude Tag for occasional work away from the host; they bill per use.

## 4. Compute

- **Agent host** `hyprn-agents-host-01` (ADR-0002), on demand: engineering sessions and operations runs. One Linux user per agent with a private home and rootless Docker. Provisioning installs the toolchains the product repositories pin; package and Docker caches persist per agent. Hosts are resized or added when telemetry shows the need.
- **Session runtime: herdr.** Each engineering agent's Claude Code sessions run in a herdr server under its Linux user, started by systemd and resumed after every boot; herdr reports each session as working, blocked, idle or done. It replaces the tmux wrapper.
  - A pinned herdr release, installed by provisioning with its checksum verified.
  - The Claude Code hooks herdr installs are allowed by the agent policy (section 13) and reviewed with it.
  - Agent-to-agent prompting stays off until Anthropic confirms how agent seats may be driven.
  - herdr is the session layer only: identities, secrets, Slack and isolation do not depend on it; tmux remains the fallback.
- **Run runner** on the host: pulls pending operations runs from the queue and executes each as the agent's Linux user in a fresh rootless container that holds only that run's credentials. Running containers count as activity for the host's idle stop.
- **Fleet controller** `hyprn-agents-wake-01`, always on: the wake service (ADR-0002) and the dispatcher. It starts the host when runs are pending; it never logs in to the host.
- Everything runs in project `hyprn-agents` (EU), with no access to staging or prod (ADR-0001).

## 5. Control plane

```text
 schedule ─┐                                            ┌─► engineering session (herdr, agent host)
 polling  ─┼─► queue ─► dispatcher ─► pending run ──────┤
 Slack    ─┘      │          │                          └─► run runner (host) ─► container ─► gateway ─► provider
                  │          ├─ loop registry: agents/loops/<name>.yaml
                  │          ├─ run state: runs, steps, pending approvals, idempotency keys
                  │          ├─ budgets per loop · kill switch per loop, agent and fleet
                  │          └─ run log and traces with cost per run
                  └─ every trigger is one envelope with an idempotency key; payloads are untrusted
```

- **Loop registry:** each loop is `agents/loops/<name>.yaml` — trigger, workflow steps, agent steps, declared tools, autonomy level per action, budget, eval set, promotion rule, owner — with its prompts and skills beside it. The dispatcher runs only registered loops.
- **Triggers:** schedules (Cloud Scheduler to the queue); polling by the controller (the Notion meetings database every 5 minutes); Slack; people. A webhook receiver is added only when polling is not enough, under its own ADR, as the fleet's only public endpoint.
- **Slack connections:** engineering agents keep their direct channel connection (ADR-0003) and the wake service (ADR-0002). The controller holds the Socket Mode connection of each operations agent's Slack app.
- **Run state:** a database of its own on the gateway's Cloud SQL instance.
- **Approvals:** an agent step asks for approval as a tool call; the run is parked, the agent's Slack bot asks the owner, the answer resumes it. A run MUST be able to wait for hours without holding compute.
- **Budgets:** each loop has a dollar budget per period, enforced by its gateway key; the dispatcher refuses runs over budget.
- **Kill switch:** per loop, per agent and fleet-wide; it MUST take effect within a minute.

## 6. Model gateway

- LiteLLM proxy on Cloud Run in `hyprn-agents`, internal ingress only, reachable from the host and the controller and not from the internet; Cloud SQL Postgres for keys, budgets and spend.
- One virtual key per loop; request and cost logs in Cloud Logging; attribution per run.
- Providers: Fireworks, the Anthropic API (the Team plan's API credits apply) and the OpenAI API. Provider keys live in Secret Manager, readable by the gateway only. Claude through Vertex AI in an EU region is an alternative for EU processing.
- Seat sessions do not pass through the gateway.

## 7. Tools and credentials

| Tool | Agent access | Credential |
|---|---|---|
| GitHub | The agent's App installation: contents and pull requests | One-hour installation tokens; engineering agents from the host's token broker (ADR-0005), operations runs from the credential broker |
| Slack | The agent's own bot | Bot and Socket Mode tokens in Secret Manager |
| Notion | Pages shared with the agent's integration | Integration token in Secret Manager |
| Google Workspace | The agent's own user | Refresh token from the agent's one-time consent to an internal OAuth client, one-hour access tokens; no domain-wide delegation |
| Granola | None: people use it; notes reach agents through Notion | — |
| Finance and banking | Read-only: statements, transactions, invoices | A read-only credential; nothing that can start, approve or release a payment |
| E-signature | Prepare documents and envelopes | No permission to sign or send for signature |

- **Credential broker:** gives each operations run only the credentials its loop declares — gateway key, Slack bot token, Notion token, GitHub installation token — short-lived where the tool allows, from Secret Manager.
- Content from documents, email, meeting notes and events is untrusted input; it never grants permissions or changes a loop.

## 8. State

| Domain | System of record |
|---|---|
| Code, pull requests, CI | GitHub |
| Knowledge, meeting notes, decisions | Notion |
| Work items | GitHub Issues with a Projects board; Linear when non-engineering work dominates |
| Conversations, approvals, feedback | Slack |
| Runs, approvals, budgets, feedback records | Control plane run state |

Agents keep no memory between runs other than these systems. Work items move through Ready (set by people), In progress, In review, Blocked and Done (set by people).

## 9. Autonomy levels

| Level | Behaviour | Applies to |
|---|---|---|
| A0 | Read and propose | Anything external; finance and e-signature permanently |
| A1 | Act after approval | Writes visible outside the company; irreversible changes; new loops that write |
| A2 | Act, then notify | Reversible internal writes |
| A3 | Act silently | Read-only digests and reports |

Each loop declares its level per action. A loop moves up one level only by a reviewed change to its definition, meeting the promotion rule the loop declares (default: eval pass rate of at least 90 % over its last 10 runs and fewer than one owner correction per run on average).

## 10. Learning

- Every loop has an eval set of at least 20 cases from real runs and a regression suite.
- Feedback in Slack — reactions, replies, approvals and refusals — is stored with its run and turned into eval cases.
- The eval runner runs on the host through the gateway and posts its result on the pull request it checks.
- An improvement run proposes changes to the loop's prompts and skills as a draft pull request; the change MUST pass the loop's eval set before the owner reviews it, and only the owner merges.
- Operations agents open pull requests only once a ruleset protects `main` (section 13).

## 11. Interfaces and telemetry

- **Slack:** talk to agents, approve, give feedback, read digests.
- **Laptop cockpit (herdr):** one window with every live session. Local panes run the owner's own work (Claude Code on the owner's seat, Codex on the ChatGPT seat). The agent host is added as a herdr machine over IAP SSH, so each engineering agent's sessions appear as panes the owner can watch or take over. One Claude Code configuration directory per seat; no session switches accounts.
- **Phone:** Slack for agents (one bot per agent, so several seats are steered without switching accounts); Remote Control for the owner's own sessions on the laptop or the host; the GitHub and Notion apps for review.
- **Telemetry:** seat sessions export usage (tokens, estimated cost, seat-limit hits) to a collector on the host; a daily report per agent is posted to Slack. Loop runs are costed by the gateway. The owner reviews seat tier and default model monthly from this data.

## 12. Fleet lifecycle

- `agents/fleet.yaml` declares every agent: name, kind, runtime binding, identities, grants. It replaces `agents/host/agents.txt` and `agents/wake/wake.json`; Terraform, provisioning, the controller and the checks read it. Loops are declared in `agents/loops/` (section 5).
- `agents/fleet add <name> --kind engineering|operations` creates the agent's identities and grants, loads secrets straight into Secret Manager, provisions its runtime and runs the checks. `remove` revokes and deletes them and prints what remains manual.
- Workspace users are created by a service account holding the Workspace user-management admin role, assigned in the Admin console; no domain-wide delegation.
- Human actions are limited to what vendors require (checked 2026-10-13):

| Vendor | Automated | Human actions |
|---|---|---|
| Google Workspace | User creation and settings | Enrol the user's second factor; give the one-time OAuth consent (only if the agent uses Google) |
| Claude Team (engineering agents) | Nothing: the Team plan has no member API | Invite with seat tier; first sign-in |
| Slack | App from manifest, icon, deletion | Create a configuration token; approve the install; create the Socket Mode token |
| GitHub | App from manifest, key straight into Secret Manager, installation lookup | Confirm creation; install |
| Notion | — | Create the integration; share the pages |
| Gateway | Virtual key and budget | None |

- An operations agent needs about 8 human actions; an engineering agent adds the two Claude seat actions.
- New tools join `fleet add` when a loop needs them.

## 13. Security invariants

- `hyprn-agents` MUST hold no staging or prod access; agents MUST hold no production credentials (ADR-0001).
- Organization policies from `bootstrap/` apply: no service-account keys, OS Login, Shielded VMs, no default network, private buckets, EU locations.
- One identity per agent per system; no shared or personal accounts.
- Secrets live in the company password manager and Secret Manager, never in Git; an agent MUST NOT read another agent's secrets.
- The Claude Code organization policy, reviewed in `agents/policy/managed-settings.json`, denies merging, pushing to `main` and force pushing, requires the sandbox, accepts only the `hyprn-agents` plugin marketplace, disables bypass mode and allows the pinned herdr hooks.
- `main` MUST be changed only by people. Until a ruleset protects it, Claude Code deny rules are the only control, so only engineering agents on Claude Code hold write access; operations agents receive write access only once the GitHub Team plan's ruleset is in place, and their Apps MUST NOT bypass it.
- All outbound traffic from agent users and their containers MUST pass the egress proxy; its allowlist is enforced from observed traffic.
- Alerts reach `gcp-admins` on unexpected secret access and on IAM changes.
- Acceptance and isolation checks run from one command after every host or project change.
