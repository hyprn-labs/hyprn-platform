# Ingest synthesis (MODE: new)

Entry point for `gsd-roadmapper`. Repository: hyprn-platform (cloud platform infrastructure and operations; no product code). Conflicts report: `.planning/INGEST-CONFLICTS.md`.

## Documents consumed (9)
- ADR: 2 (docs/adr/0001-agent-fleet.md, docs/adr/0002-agent-host-on-demand.md); both locked; ADR-0002 (manifest precedence 0) outranks ADR-0001 (precedence 1) and supersedes only its section 4 machine size and always-on operation.
- SPEC: 1 (docs/specs/cloud-platform.md)
- PRD: 0
- DOC: 6 (docs/plans/agent-fleet.md, runbooks/agents/gcp.md, runbooks/agents/host.md, runbooks/agents/slack.md, agents/marketplace/README.md, README.md)
- UNKNOWN or low confidence: 0

## Intel files
- `decisions.md`: 2 locked decisions (ADR-0001 with sections 1-7, ADR-0002).
- `requirements.md`: 0 requirements (no PRDs); explains where acceptance-style obligations live.
- `constraints.md`: 42 constraints from the platform specification. By type: api-contract 1 (lifecycle CLI contract), schema 6 (workload contract, contract validation, release descriptor, environment binding and desired state, application database, secret aliases), protocol 15, nfr 20.
- `context.md`: 8 topic entries plus 2 reference index pages: repository overview, plan A-E tasks with status from runbook evidence, three runbooks (records treated as validated state, not requirements), marketplace audit.

## Current state (evidence-based, from runbook records and orchestrator facts)
- Done: Google Cloud organization setup and bootstrap (`bootstrap/` applied, remote state, admin group, domain-wide grants removed); project `hyprn-agents`; `infra/agents/` applied (network, host `hyprn-agents-host-01` t2d-standard-8, wake VM `hyprn-agents-wake-01` e2-micro, secrets); host provisioning; Ada signed in with persistent session; Slack plugin, secrets, organization channel settings, wake from Slack (about 50 s).
- Open: C (GitHub: Team plan required, org is on Free; App, token helper, ruleset, acceptance); D3 remainder (Claude Code permission rules and sandbox for agents; `strictKnownMarketplaces` unverified); D5 remainder (permission relay test, rejection of other senders); E (first-week measurement); A5 isolation check and B6/B7 dedicated records not seen in ingested docs.
- Not started and outside the agent fleet: everything the SPEC defines for staging and prod (projects, hosts, buckets, reconciler, deployment contract, CI identities, delivery pipeline).

## Conflicts (see report)
- 0 blockers.
- 2 warnings needing user approval: cross-reference cycles treated as benign (deviation from the strict cycle rule); ADR-0001 "vendored community Slack plugin" wording versus the own server actually implemented.
- 7 info: ADR-0002 supersession of ADR-0001 section 4 (resolved by manifest precedence and ADR text); SPEC project naming drift; stale "nothing provisioned" and "skeleton" statements; plan A3/A6 and part C gate drift; strictKnownMarketplaces not evidenced; hyprn-agents versus SPEC environment model; GitHub Team plan prerequisite.
- 0 competing PRD variants.

## Pointers for the roadmapper
- Locked inputs: `decisions.md`. Do not plan work that reverses them; ADR-0001 section 1 gates agent #2 on Anthropic's human answer.
- Platform build-out scope and acceptance checks: `constraints.md` (sections 8-9 delivery and lifecycle, section 12 security verification, section 13 cost).
- Agent fleet remaining work and gates: `context.md`, topic "Plan: agent fleet (tasks and status)".
