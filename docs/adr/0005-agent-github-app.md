---
status: accepted
date: 2026-10-13
decision-makers: Owner
---

# ADR-0005: Agent GitHub access through a GitHub App with one-hour tokens

## Context and Problem Statement

[ADR-0004](0004-agent-github-machine-account.md) gave Ada a GitHub machine account with a fine-grained token valid up to 90 days, as an interim step towards the GitHub App of [ADR-0001](0001-agent-fleet.md) section 5. The machine account needs an email address, a paid seat on a paid plan, two-factor authentication once the organization requires it, and manual token rotation; a leaked token works for weeks. GitHub Apps work on every plan, including Free.

## Decision Drivers

- Short-lived credentials minted when needed; nothing long-lived in the agent's reach.
- An agent identity without a seat, an email address or a second factor.
- No manual token rotation.

## Considered Options

- **A1** keep the machine account and its fine-grained token (ADR-0004).
- **A2** one GitHub App per agent, with installation tokens minted on the host.

## Decision Outcome

Chosen: **A2**. This supersedes ADR-0004 and completes ADR-0001 section 5.

- One GitHub App per agent, owned by `hyprn-labs`, installed on selected repositories only; Contents and Pull requests read/write, Metadata read; no webhook. Ada's App is `ada-agent-hyprn`; its bot commits as `ada-agent-hyprn[bot]`. App and installation IDs are in `agents/host/agents.txt`.
- The App's private key lives in the company password manager and in Secret Manager as `<name>-agent-github-app-key`, readable by the host identity only.
- A root-only broker on the host signs a JWT with that key, held in memory only, and mints a one-hour installation token limited to those permissions. It runs every 30 minutes and on every secret reload, and writes the token to tmpfs, readable by the agent only. Git reads it through the credential helper; `gh` through a wrapper that always takes the current token.
- The agent never sees the private key; a leaked installation token expires within an hour.
- Agents still never merge or deploy. Until a ruleset protects `main`, Claude Code permission rules deny merging and pushing to `main`.

### Consequences

- Good: no long-lived token on the host; no seat, email, second factor or manual rotation for the agent's GitHub identity.
- Good: pull requests show as the App's bot, clearly an agent.
- Bad: the App's private key is long-lived; its rotation is a runbook step.
- Neutral: the machine account, its token and its secret are removed.

### Confirmation

- Host checks: the token is younger than 35 minutes, `gh` reaches the installation's repositories, and Git commits as the App's bot.
- A draft pull request opened by Ada shows the App's bot as author.
