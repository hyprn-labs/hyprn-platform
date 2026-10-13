# Roadmap: hyprn-platform

## Overview

Milestone "Agent fleet operational". Ada answers from Slack, wakes a stopped host and works on GitHub through its App. This milestone hardens the fleet before it grows, makes agents faster at real work, turns adding an agent into one command, proves the isolation between agents, and ends with a measured week that drives the seat and model decisions. Security comes before anything that adds agents; the onboarding kit comes before agent #2; cross-agent isolation needs two agents. Staging and prod, the deployment contract and the host reconciler are out of scope.

## Phases

- [ ] **Phase 1: Security baseline** - Enforced Claude Code policy, egress proxy in observe mode, alerts on secrets and IAM, account safeguards
- [ ] **Phase 2: Agent workflow and efficiency** - Worktree per task with clean-up, pre-installed toolchains and persistent caches, first Slack-to-draft-PR
- [ ] **Phase 3: Fleet as code and onboarding kit** - `agents/fleet.yaml` as single source; `agents/fleet add` and `remove` with a handful of human actions
- [ ] **Phase 4: Acceptance and isolation checks** - Every control proven by one repeatable command, including isolation between two agents
- [ ] **Phase 5: Measured week and decisions** - One measured week; egress allowlist enforced; seat, model and fleet-size decisions recorded

## Phase Details

### Phase 1: Security baseline
**Goal**: Agents run under enforced policy, their outbound traffic is visible, and misuse of secrets or IAM raises an alert.
**Depends on**: Nothing (first phase)
**Requirements**: POL-01, POL-02, POL-03, POL-04, EGR-01, DET-01, DET-02, SEC-01, SEC-02, DOC-01
**Success Criteria** (what must be TRUE):
  1. The admin console policy matches the reviewed `agents/policy/` copy; `runbooks/agents/` records when it was applied.
  2. In Ada's session, merge, push to `main` and force push are refused; adding another marketplace is refused; a sandboxed command to a host outside the sandbox allowlist fails; routine work in a worktree runs without approval prompts.
  3. The egress proxy logs each agent's destinations; a direct connection that bypasses it fails.
  4. A test read of an agent secret by an unexpected principal, and a test IAM change in `hyprn-agents`, each produce an alert to `gcp-admins`.
  5. The break-glass admin exists with an offline key and no standing role; `hyprn-labs` requires two-factor authentication.
**Plans**: TBD

### Phase 2: Agent workflow and efficiency
**Goal**: Agents spend their time on tasks: one clean worktree per task, tools and caches ready, and the Slack-to-draft-PR path proven.
**Depends on**: Phase 1
**Requirements**: GH-01, GH-02, GH-03, EFF-01, EFF-02
**Success Criteria** (what must be TRUE):
  1. A small task sent in Slack produces a draft pull request from `agent/ada/<slug>` by `ada-agent-hyprn[bot]` with a description of the change and its verification; Ada does not merge it.
  2. Two tasks run in two worktrees side by side, each with its own port block, Compose project and test database; merged or closed work leaves no worktree or local branch behind.
  3. A fresh worktree runs the product's test setup without installing toolchains, and a second run is measurably faster than the first.
**Plans**: TBD

### Phase 3: Fleet as code and onboarding kit
**Goal**: Adding or removing an agent is one command; the only human actions are the approvals vendors require.
**Depends on**: Phase 2
**Requirements**: FLT-01, FLT-02, FLT-03, FLT-04, FLT-05, FLT-06, FLT-07, FLT-08
**Success Criteria** (what must be TRUE):
  1. `agents/fleet.yaml` is the only place an agent is declared; Terraform, provisioning, the wake service and the checks read it.
  2. `agents/fleet add` onboards a throwaway test agent (Google group, Slack app, GitHub App, secrets, Linux user, session) in 15 minutes or less with 8 human actions or fewer, excluding the Claude seat steps, and the test agent answers a Slack message.
  3. `agents/fleet remove` offboards the test agent; nothing of it remains except what the printed manual steps name.
  4. Whether channels work with a `setup-token` sign-in is tested and recorded; the onboarding uses whichever works.
  5. `runbooks/agents/onboarding.md` lets the platform owner repeat it without this conversation.
**Plans**: TBD

### Phase 4: Acceptance and isolation checks
**Goal**: Every control that keeps agents contained is proven by one repeatable command.
**Depends on**: Phase 3
**Requirements**: ACC-01, ACC-02, ACC-03, ACC-04, ACC-05, ACC-06, ACC-07, ACC-08
**Success Criteria** (what must be TRUE):
  1. A risky action is approved or refused from Slack, and only the platform owner's reply counts; other senders never reach a session or wake the host.
  2. Merge, push to `main` and bypass mode are refused for every agent.
  3. With two agents, neither reaches the other's files, secrets, Docker, GitHub token or Slack app.
  4. The IAM, no-production-credentials and ADR-0002 checks pass; one command runs all checks and writes a dated record.
**Plans**: TBD

### Phase 5: Measured week and decisions
**Goal**: One measured week produces the evidence for the seat, model and fleet-size decisions, and the egress allowlist is enforced from observed traffic.
**Depends on**: Phase 4
**Requirements**: MEAS-01, MEAS-02, MEAS-03, EGR-02
**Success Criteria** (what must be TRUE):
  1. Seven consecutive daily reports exist from a week of real tasks with extra usage off.
  2. The weekly summary shows limit hits, API-equivalent cost against the seat price, approvals per task, time to pull request and the proxy's observed destinations.
  3. The proxy enforces the reviewed allowlist; a request to an unlisted domain is refused and logged, and agents still complete their tasks.
  4. A follow-up ADR records the decisions on default model, seat tier, seats versus API keys and when to add agent #2.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Security baseline | 0/0 | Not started | - |
| 2. Agent workflow and efficiency | 0/0 | Not started | - |
| 3. Fleet as code and onboarding kit | 0/0 | Not started | - |
| 4. Acceptance and isolation checks | 0/0 | Not started | - |
| 5. Measured week and decisions | 0/0 | Not started | - |

## Deferred Beyond This Milestone

- GitHub Team plan, `main` ruleset and `CODEOWNERS` (GHE-01, GHE-03): after the platform owner upgrades the plan; recommended as the only hard lock on `main`.
- Agent #2 (FLEET-01): onboarded with `agents/fleet add` after Anthropic's answer and the Phase 5 decision.
- API-key overflow (FLEET-02), agent cockpit such as herdr (FLEET-03), GitHub issues as task intake (FLEET-04), Slack plan beyond 10 apps (FLEET-05).
- Staging and prod build-out (PLAT-01, PLAT-02): after the product's local edition.
