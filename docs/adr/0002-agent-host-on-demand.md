---
status: accepted
date: 2026-10-12
decision-makers: Owner
---

# ADR-0002: Agent host on demand, woken from Slack

## Context and Problem Statement

[ADR-0001](0001-agent-fleet.md) sized the agent host as an always-on `e2-standard-4`. The owner needs roughly the power of a current laptop for builds and tests, but only while agents work, with a disk that keeps worktrees, sign-ins and sessions. A stopped VM costs only its disk, but while stopped no agent session is connected to Slack, and Slack does not queue events for a disconnected Socket Mode app.

## Decision Drivers

- Build and test throughput when in use; minimal cost when idle.
- Persistent disk across stops.
- Agents stay steerable from Slack, including waking the host.
- No public ingress (cloud-platform specification; ADR-0001 section 6).

## Considered Options

- **H1** always-on `e2-standard-4` (ADR-0001).
- **H2** larger host on demand, started manually, stopped when idle.
- **H3** H2 plus a small always-on wake service on Slack Socket Mode.
- **H4** H2 plus a public HTTPS endpoint (serverless) for a Slack wake command.

## Decision Outcome

Chosen: **H3**. This supersedes the machine size and always-on operation in ADR-0001 section 4; everything else there stands.

- Host `hyprn-agents-host-01`: `t2d-standard-8` (8 physical cores, 32 GB), same 100 GB balanced disk, pinned Debian 12, no public IP.
- The host stops itself after 30 minutes with no agent work and no SSH session (guest shutdown; no cloud permission needed). On boot, each agent's session resumes under systemd.
- Wake service `hyprn-agents-wake-01`: `e2-micro`, always on, no public IP, outbound Socket Mode only. It connects to an agent's Slack app only while the host is stopped, so it never takes events from a running agent. On a message from the allowlisted sender it replies that the agent is waking, starts the host and disconnects. Code in [`agents/wake/`](../../agents/wake/README.md).
- The wake identity `hyprn-agents-wake` holds a custom role with `compute.instances.get`, `start` and `stop`, granted on the host instance only, plus log and metric writing; its Slack tokens come from Secret Manager per secret.
- The host can also be started with `gcloud compute instances start` or the Cloud console app.

Prices from the Cloud Billing catalog on 2026-10-12, europe-west1, EUR: `t2d-standard-8` about 0.33 per hour; `e2-micro` about 6 per month; 100 GB balanced disk about 9 per month. At 8 hours a day on 22 days, about 75–80 per month in total, within the 100 EUR budget.

### Consequences

- Good: about 2.5 times the build throughput of H1 at lower monthly cost; disk and sessions persist.
- Good: still outbound only; the wake identity cannot touch anything but the host's power state.
- Bad: about a minute from the first Slack message to the agent's reply when the host is stopped (estimate, to be measured).
- Bad: one more small always-on VM and a small service to maintain.
- Neutral: the machine type is one variable; changing it needs a stop and a reviewed plan, not a new disk.

### Confirmation

- A message from the allowlisted sender to a stopped agent starts the host, and the agent answers it; a message from anyone else does not.
- While the host runs, the wake service holds no Slack connection.
- The wake identity is refused any action other than get, start and stop on the host.
- The host stops after the idle period and keeps its disk contents.

## Pros and Cons of the Options

- **H1** Good: always reachable. Bad: smaller and costs more per month.
- **H2** Good: cheapest. Bad: the owner must start the host before talking to an agent.
- **H4** Good: no always-on VM. Bad: adds a public endpoint, against the outbound-only rule.
