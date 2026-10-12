---
status: accepted
date: 2026-10-12
decision-makers: Owner
---

# ADR-0004: Agent GitHub access through a machine account until the GitHub App

## Context and Problem Statement

[ADR-0001](0001-agent-fleet.md) section 5 gives each agent its own GitHub App with one-hour installation tokens. Ada needs to push branches and open draft pull requests now. A dedicated GitHub machine account for Ada, with a fine-grained personal access token, is available immediately; the App needs its private key, a token helper and an organization ruleset.

## Decision Drivers

- Ada opens draft pull requests in `hyprn-labs` repositories without delay.
- Ada acts under its own identity, never the owner's.
- Least privilege and a short credential lifetime.

## Considered Options

- **M1** machine account per agent with a fine-grained token, until the App exists.
- **M2** wait for the GitHub App.
- **M3** a token from the owner's account.

## Decision Outcome

Chosen: **M1**, as an interim step; ADR-0001 section 5 remains the target.

- Ada's GitHub account is a machine account owned by the platform owner and a member of `hyprn-labs`; its login is listed in `agents/host/agents.txt`. Display name "Ada (AI agent)".
- Fine-grained token: resource owner `hyprn-labs`; selected repositories only; Contents read/write, Pull requests read/write, Metadata read; no Workflows, Administration or Secrets; expiry 90 days or less.
- The token lives in the company password manager and in Secret Manager as `agent-ada-github-token`, readable by the host identity only. The root loader writes it to tmpfs for `ada` only; Git uses it through `/usr/local/libexec/hyprn-git-credential`, `gh` through `GH_TOKEN`.
- Commits carry `Ada (AI agent)` and the account's GitHub no-reply address.
- Agents still never merge or deploy. Until the organization's plan enforces a ruleset on `main` for private repositories, Claude Code permission rules deny merging and pushing to `main`; the ruleset becomes the enforcing control once available.

### Consequences

- Good: Ada works on GitHub today under its own identity.
- Bad: a long-lived token (up to 90 days) instead of one-hour tokens; rotation is a manual step recorded in the runbook.
- Bad: the machine account occupies a paid seat once the organization is on a paid plan.
- Neutral: replacing it by the GitHub App changes only the secret and the credential helper.

### Confirmation

- Ada pushes an `agent/ada/*` branch and opens a draft pull request that GitHub attributes to Ada's account.
- The token file on the host is mode 0400, owned by `ada`; no other agent can read it.
- A merge attempt by Ada is refused by Claude Code permission rules, and by the ruleset once enabled.
