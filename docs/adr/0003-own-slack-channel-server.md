---
status: accepted
date: 2026-10-12
decision-makers: Owner
---

# ADR-0003: Our own Slack channel server for agents

## Context and Problem Statement

[ADR-0001](0001-agent-fleet.md) section 6 steers agents from Slack through Claude Code channels with "the community Slack plugin", audited and vendored into our marketplace. The audit set the bar: Socket Mode only, sender allowlist by Slack user ID including permission replies, tokens read from files, outbound traffic only to Slack, pinned dependencies, a licence allowing our use. Which plugin meets it?

## Decision Drivers

- Only the platform owner can instruct an agent or approve its actions; the agent cannot change that list.
- No dependency downloads at runtime; a code base small enough to audit line by line.
- Claude Code's own permission relay, not a parallel approval mechanism.

## Considered Options

- **P1** vendor `Reef-Digital/claude-code-slack` (Apache-2.0).
- **P2** vendor `Muneshige1567/claude-channel-slack`.
- **P3** write our own channel server.

## Decision Outcome

Chosen: **P3**. This supersedes the "community plugin, vendored" wording of ADR-0001 section 6; the rest of that section stands.

- [`agents/marketplace/plugins/slack/server.py`](../../agents/marketplace/plugins/slack/server.py): MCP over stdio, about 300 lines of Python using the standard library and Debian's `python3-websocket`.
- Declares `claude/channel` and `claude/channel/permission`; answers with MCP revision `2025-06-18`, since channel servers are not registered under the 2026 revision.
- Delivers direct messages and mentions only from users in the root-written allowlist; permission verdicts only from the same users, for request IDs Claude Code issued.
- Tokens and allowlist come from root-written tmpfs files; the server writes only its own deduplication state and log.
- After each start it delivers recent direct messages not yet seen, so a message that woke the host is answered.

### Consequences

- Good: every line is ours to audit; nothing is fetched at runtime; the allowlist is outside the agent's reach.
- Good: one plugin serves every agent; the Slack app per agent carries the identity.
- Bad: we maintain it as Claude Code channels evolve (research preview).

### Confirmation

- A message from a user outside the allowlist produces no delivery and no reaction.
- A `yes <id>` from outside the allowlist does not approve.
- The host checks confirm the allowlist is root-owned and the tokens are readable by their agent only.

## Pros and Cons of the Options

- **P1** Good: features (files, reactions, history), tests. Bad: allowlist in an agent-writable file where an empty list means anyone; npm dependencies installed at every start with caret ranges; requires Bun; approvals through its own hooks.
- **P2** Bad: no licence.
- **P3** Good: meets every audit requirement by construction. Bad: maintenance is ours.
