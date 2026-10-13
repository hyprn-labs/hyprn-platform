---
status: proposed
date: 2026-10-13
decision-makers: Owner
---

# ADR-0006: Agent-first operating model — loops, runtimes and the fleet control plane

## Context and Problem Statement

HYPRN scales with agents before it hires: engineering and operations work is done by agents under human direction, and the first hires integrate and extend the fleet's playbook rather than do the work by hand. ADR-0001 to ADR-0005 built one engineering agent steered from Slack. The company now needs work that runs without a person starting it — on a schedule or when something happens — across engineering and operations, on Claude Team seats, API keys and open models alike.

Tools in use: GitHub, Slack, Google Workspace, Granola (used by people in meetings; notes flow to Notion), Notion, Claude, OpenAI, Fireworks. Next: finance and banking, e-signature.

What architecture lets agents do that work safely and cheaply, keeps the know-how in one reviewable place, and lets a new person extend it?

## Decision Drivers

- Every piece of recurring work becomes a loop that runs without the owner starting it, with the owner deciding only where judgment or risk requires.
- Provider-agnostic: an agent runs on a seat or an API key, on Claude, OpenAI or open models, without redesign.
- Each provider's terms are respected: subscription seats only for the uses they are sold for.
- No path from agents to staging or prod credentials (ADR-0001); least privilege per agent and per loop.
- Cost per loop is known and capped.
- The playbook is code: reviewable, versioned, transferable to a new hire.
- Buy hosted pieces where they fit; build only the thin layer that ties them together.

## First principles

The company runs as five loops:

| Loop | Purpose | Human role |
|---|---|---|
| **Work** | Do the work: engineering (task → branch → draft pull request → merge) and operations (meeting → notes → actions, digests, triage) | Sets goals; approves risky actions |
| **Coordination** | Shared state: what is planned, in progress, blocked, done; hand-offs between agents and people | Prioritizes |
| **Control** | What may happen without a human: approvals, autonomy levels, budgets, kill switch | Approves, promotes or revokes autonomy |
| **Learning** | Turn outcomes into better loops: evals, feedback, failures | Reviews proposed changes |
| **Governance** | Identities, onboarding and offboarding, security, cost, audit | Owns policy |

Design rules, from the sources below:

1. Loops are deterministic workflows with agent steps only where judgment is needed.
2. Every loop has an explicit trigger — schedule, event or human — and all triggers enter through one queue.
3. Trigger payloads are untrusted data; the reviewed loop definition carries authority, never the event.
4. Autonomy is set per action by risk (reversibility, external visibility, money) and earned from eval evidence.
5. Human approval is a tool call that can wait for hours and resume, never a blocked process.
6. Business state lives in systems of record that agents query; agents keep no hidden memory between runs.
7. Know-how lives in versioned skills and prompts on top of existing harnesses; we do not build a harness.
8. Small, focused agents with their own context; several agents only for parallel, high-value work.
9. Every loop ships with evals; a green run is not proof the work was done.
10. All metered model traffic goes through one gateway with per-loop keys, budgets and attribution.
11. Least privilege per loop: its own identity, scoped tools, network allowlist from the first run, and a ruleset on `main` (GitHub Team plan) as the hard backstop.

## Considered Options

- **O1** Buy end to end: hosted agents (Claude Tag, Managed Agents, routines, Copilot, Devin) wired by each vendor's own triggers.
- **O2** Build our own agent framework and harness.
- **O3** A thin control plane of our own over official harnesses and hosted runtimes, with agents, loops and skills declared as code.

## Decision Outcome

Chosen: **O3**. The target is described in the [agent fleet specification](../specs/agent-fleet.md); its sections carry the detail.

- **Seats for human-directed work, API keys for loops** (spec §1, §3). A seat never runs an autonomous loop; seats run only their own agent's sessions; Claude subscriptions only in Anthropic's own applications.
- **Two kinds of agent** (spec §2): engineering agents on Claude seats (Ada); operations agents on API keys through the gateway, open models at Fireworks first (Boole). Each agent has one identity per system, with a Google Workspace user `<name>@agents.hyprn.ai`.
- **Registry as playbook** (spec §5, §12): `agents/fleet.yaml` declares agents; `agents/loops/<name>.yaml` declares loops with their skills and prompts. Every change is a pull request. Onboarding and offboarding are generated from the registry; human actions are limited to the approvals vendors require.
- **Control plane** (spec §5): the always-on VM becomes the fleet controller — queue, dispatcher, run state in the gateway's Cloud SQL, approvals that wait, budgets, kill switch, run log. A run runner on the agent host executes operations runs in fresh rootless containers.
- **Triggers** (spec §5): schedules, polling (first: the Notion meetings database every 5 minutes), Slack and people. A webhook receiver comes only when polling is not enough, under its own ADR.
- **Model gateway** (spec §6): LiteLLM on Cloud Run, internal ingress only, Cloud SQL; one key and budget per loop; Fireworks, Anthropic and OpenAI behind it.
- **Tools and credentials** (spec §7): least-privilege grants per agent, a credential broker per run; finance read-only and e-signature prepare-only, permanently; people's own accounts (Granola) never used by agents.
- **Autonomy levels A0–A3 and learning** (spec §9, §10): levels per action; promotion by reviewed change meeting a declared rule; feedback from Slack becomes eval cases; improvements arrive as pull requests that pass the evals.
- **Session runtime and cockpit** (spec §4, §11): herdr runs engineering agents' sessions on the host and is the owner's cockpit on the laptop over IAP SSH.
- **`main` protection** (spec §13): the GitHub Team plan's ruleset protects `main` in every repository from the first milestone; Claude Code deny rules remain a second layer for engineering agents.

### Amends

- **ADR-0001 section 2 (identities):** an agent's email identity is a Google Workspace user, not a Google group.
- **ADR-0001 section 4 (agent host):** herdr replaces the tmux wrapper as the session runtime; operations runs execute in rootless containers under the agent's Linux user.
- **ADR-0001 section 7 (measurement):** the measured first week is replaced by continuous telemetry and gateway cost, reviewed monthly; no follow-up decision record.
- **ADR-0001 section 1 (licensing):** "a second agent waits for Anthropic's answer" applies to agents on Claude seats only; API-key agents are not gated by it.
- **ADR-0005:** an operations agent's App is installed only on the repositories its loops change, and only once a ruleset protects `main`.

### Build or buy

| Component | Choice |
|---|---|
| Harnesses | Buy: Claude Code, Agent SDK, Codex, OpenCode |
| Hosted runtimes | In reserve: Claude Code cloud sessions, Claude Tag, Managed Agents |
| Model gateway | Adopt: LiteLLM on Cloud Run with Cloud SQL |
| Queue, scheduler, database | Managed Google Cloud services |
| Connectors | Vendor apps and MCP servers |
| Session runtime and cockpit | Adopt: herdr, tmux as fallback |
| Registry, dispatcher, run runner, approvals, credential broker, eval runner | Build, thin |

### First loops

- **Operations (Boole):** meeting note lands in Notion → decisions and actions extracted, Notion updates proposed, summary in Slack. Starts at A1 for Notion writes; target A2 once its promotion rule is met.
- **Engineering (Ada):** task in Slack → draft pull request (human-directed, on its seat).
- Next, when needed: weekly operating digest (A3); failed CI on `main` diagnosed (A0); finance reconciliation and payment proposals (A0).

### Consequences

- Good: one model for every kind of work; adding a loop is a reviewed file, not new infrastructure.
- Good: provider choice is a binding; cost per loop is visible and capped.
- Good: a new hire learns the company by reading the playbook and extends it the same way.
- Bad: the control plane, gateway and database are ours to run; they must stay small.
- Bad: a Workspace licence per agent; the GitHub Team plan from the first milestone.
- Neutral: hosted runtimes can take over parts of the control plane as they mature, because loops are declared independently of where they run.

### Confirmation

- A loop runs end to end on an API key through the gateway, with cost per run recorded and a budget that stops it.
- A run at A1 waits hours for an approval in Slack and resumes on the answer.
- The same loop runs on an open model and on Claude by changing its binding only.
- Removing a loop or an agent revokes its credentials and stops its triggers.

## Pros and Cons of the Options

- **O1** Good: least to operate. Bad: per-vendor silos; actions appear as individual owners (routines); usage billing for everything; no shared state, approvals or evals across vendors.
- **O2** Good: full control. Bad: rebuilds what harnesses already do well.
- **O3** Good: each vendor where it is strongest, company logic in one place. Bad: a small control plane to maintain.

## More Information

Sources, checked 2026-10-13:

- Y Combinator: "Inside YC's AI Playbook" and "Tokenmaxxing" (Lightcone, May 2026) — https://www.ycombinator.com/library ; Requests for Startups — https://www.ycombinator.com/rfs
- Anthropic: Building effective agents — https://www.anthropic.com/engineering/building-effective-agents ; multi-agent research system — https://www.anthropic.com/engineering/multi-agent-research-system ; context engineering — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ; evals for agents — https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents ; measuring agent autonomy — https://www.anthropic.com/research/measuring-agent-autonomy
- Claude Code: Agent SDK approvals — https://code.claude.com/docs/en/agent-sdk/user-input ; routines — https://code.claude.com/docs/en/routines ; LLM gateways — https://code.claude.com/docs/en/llm-gateway ; legal and compliance — https://code.claude.com/docs/en/legal-and-compliance
- Claude Managed Agents — https://platform.claude.com/docs/en/managed-agents/overview
- OpenAI: A practical guide to building agents — https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- 12-factor agents — https://github.com/humanlayer/12-factor-agents
- Levels of autonomy for AI agents — https://arxiv.org/abs/2506.12469
- Fireworks Anthropic compatibility — https://docs.fireworks.ai/tools-sdks/anthropic-compatibility ; LiteLLM proxy — https://docs.litellm.ai/docs/proxy/users

Open questions before the dependent work:

- Finance, banking and e-signature providers, and the read-only access each offers (before those tools join a loop).
- How meeting notes reach Notion from Granola (before Boole's meeting loop).
