---
status: proposed
date: 2026-10-13
decision-makers: Owner
---

# ADR-0007: Codd-pattern coding agents — GitHub App plus Linux user plus OpenCode, herdr-controlled

## Context and Problem Statement

ADR-0001 put one engineering agent (Ada) on a Claude Team seat, steered from Slack, with one identity per system (Workspace user, Slack app, GitHub App, Linux user). Building the platform that way is slow and seat-bound: long-running tasks share one host and one session model, and every future coding agent would need a Slack app, a Workspace user and a paid seat before doing anything useful.

Codd (built 2026-10-13, `runbooks/agents/opencode.md`) showed a cheaper shape: a GitHub App installed on one repository, a Linux user with a private home, OpenCode under a managed configuration, steered by the owner from the terminal, no Slack app, no Workspace user, no seat. The owner directs that later coding agents follow this setup on dedicated or shared VMs, controlled through herdr, giving compute split for long-running tasks.

All current development is rapid prototyping under the owner's personal accounts. Codd runs a free Muse Spark model on OpenCode Zen, whose price is Meta's training use of prompts and completions. The IP moves to the future company, at which point model bindings move to protective terms. Purchases (GitHub Team plan, revised budget, provider keys) arrive later; until then phases proceed on deny-rules and prototyping terms.

What shape do coding agents take, and on what terms, until the company exists?

## Decision Drivers

- Coding agents must start cheap: no Slack app, Workspace user or paid seat required before the first useful task.
- Long-running tasks need compute split: more agents on dedicated or shared VMs, each with its own context, all visible in one cockpit.
- Every agent keeps its own identity and reach enforced by GitHub and Linux: one App, one user, scoped repositories only.
- Free-tier training-use terms are acceptable for prototyping under personal accounts only; company work needs protective terms.
- No agent is retired for the company move: only its model binding changes, by configuration.
- Purchases arrive later and must not gate prototyping work that deny-rules and user boundaries already cover.

## Considered Options

- **O1** Every coding agent like Ada: Claude seat, Slack app, Workspace user, one identity per system.
- **O2** Codd pattern for coding agents: GitHub App plus Linux user plus OpenCode, herdr-controlled, on a dedicated or shared VM; free-tier models for prototyping, protective bindings after the company move.
- **O3** Wait for the gateway and run all coding agents as operations-style runs on API keys.

## Decision Outcome

Chosen: **O2**. The target is described in the [agent fleet specification](../specs/agent-fleet.md) §1–§3; its sections carry the detail.

- **Third binding for engineering work** (spec §2): alongside seat-steered Ada, coding agents run OpenCode on keyless free-tier models, in herdr-controlled sessions under their Linux user on a dedicated or shared VM. Codd is the first; later agents copy it.
- **Identities** (spec §2): a Codd-pattern agent holds only a GitHub App (scoped to the repositories it changes) and a host Linux user. No Slack app, no Workspace user.
- **Terms** (spec §1, §3): free-tier models with training-use terms are allowed for rapid prototyping under personal accounts, re-checked monthly against the Zen model list (CODD-03). On the company move the model binding changes to protective terms by configuration (CODD-03); the agent is not retired and its IP transfers with everything else.
- **Purchases later**: the GitHub Team plan, revised budget and provider keys arrive when the company needs them; until then deny-rules, managed OpenCode policy and Linux user boundaries are the controls (Phase 1 proves them for Codd too, CODD-01).
- **Fleet onboarding** (Phase 6, CODD-02): `fleet add` covers the Codd pattern, so a coding agent is onboarded by the same command, with compute split across VMs.

### Amends

- **ADR-0001 section 1 (licensing):** one Claude Team seat per engineering agent applies to Slack-steered agents (Ada). Codd-pattern coding agents run keyless free-tier models for prototyping, protective bindings after the company move.
- **ADR-0001 section 2 (identities):** every agent holds one identity per system it uses; Codd-pattern agents use GitHub and the host only — no Slack app, no Workspace user.
- **ADR-0005:** an engineering agent's App is installed only on the repositories it changes (Codd: `hyprn-platform` only), not by default on all repositories.
- **ADR-0006 decision outcome:** two kinds of agent become three bindings — seat-steered engineering (Ada), Codd-pattern engineering (Codd and later coding agents), operations on API keys (Boole).

### Consequences

- Good: new coding agents start with an App, a user and a config file; long tasks split across machines under one herdr cockpit.
- Good: no spend and no vendor waits before the company exists; the company move is a model swap, not a rebuild.
- Good: training-use exposure is bounded to prototyping repositories by App scope.
- Bad: free-tier models change often; the monthly terms check is a standing chore until the company move.
- Bad: without the Team plan there is still no ruleset on private repositories; deny-rules remain the only control.
- Neutral: Ada keeps its seat and Slack steering; the two engineering shapes coexist.

### Confirmation

- A second coding agent is onboarded from the Codd pattern and opens a draft pull request from its own branch.
- Codd's App sees `hyprn-platform` only; its Linux user cannot reach other agents' homes, tokens or processes.
- Switching Codd's model binding changes nothing else about the agent.
