# Roadmap: hyprn-platform

## Overview

Milestone "Agent fleet operational". The agent fleet is provisioned, Ada answers from Slack and wakes from a stopped host. What remains is finishing work: enforce the Claude Code policy that stands in for a GitHub ruleset, prove the Slack-to-draft-pull-request path, turn the isolation and acceptance checks into repeatable tests, and run one measured week that drives the seat decision. Staging and prod, the deployment contract, the host reconciler and agent #2 are out of scope.


## Phases

- [ ] **Phase 1: Enforced agent policy** - Claude Code permission rules, sandbox, egress allowlist and deny rules for merge and push to `main` are in force; account safeguards and ADR-0003 are done
- [ ] **Phase 2: GitHub draft-pull-request workflow** - A Slack task becomes a draft pull request by `ada-agent-hyprn` from its own worktree
- [ ] **Phase 3: Acceptance and isolation checks** - Permission relay, sender rejection, merge refusal and isolation checks pass as repeatable tests and are recorded
- [ ] **Phase 4: Measured week and seat decision** - One week of measured work with daily reports ends in a recorded seat decision

## Phase Details

### Phase 1: Enforced agent policy
**Goal**: Ada runs under reviewed Claude Code policy that the admin console enforces, and the account-level safeguards around the fleet are in place.
**Depends on**: Nothing (first phase)
**Requirements**: POL-01, POL-02, POL-03, POL-04, SEC-01, SEC-02, DOC-01
**Success Criteria** (what must be TRUE):
  1. The organization policy in the Claude admin console matches the reviewed copy in `agents/policy/` (permission rules, sandbox, egress allowlist, `strictKnownMarketplaces`, channels, bypass mode disabled), and `runbooks/agents/` records when and by whom it was applied.
  2. As Ada, a shell command to a host outside the egress allowlist fails, and adding a marketplace other than `hyprn-agents` is refused.
  3. In Ada's session, asking for a pull request merge, a push to `main` or a force push in `hyprn-platform` or `hyprn-mvp` is refused by permission rules.
  4. A break-glass super admin with an offline key exists and holds no standing role, and the `hyprn-labs` organization requires two-factor authentication for every member.
  5. ADR-0003 is accepted and linked from the ADR index, so the documented Slack plugin matches the deployed one.
**Plans**: TBD

### Phase 2: GitHub draft-pull-request workflow
**Goal**: The platform owner gives Ada a task in Slack and receives a reviewable draft pull request by `ada-agent-hyprn`.
**Depends on**: Phase 1
**Requirements**: GH-01, GH-02, GH-03
**Success Criteria** (what must be TRUE):
  1. After the platform owner sends a small task in Slack, a draft pull request appears on GitHub from branch `agent/ada/<slug>`, authored by `ada-agent-hyprn`, with a description of what changed and how it was verified.
  2. The pull request stays a draft and is not merged by Ada; its commits carry the "Ada (AI agent)" identity.
  3. Two tasks run in two worktrees on the host side by side, each with its own branch, port block, Compose project name and test database name.
  4. The former `agent-ada-*` secrets and the earlier tokens are deleted, and `runbooks/agents/github.md` shows the current token's expiry and the next rotation date.
**Plans**: TBD

### Phase 3: Acceptance and isolation checks
**Goal**: The controls that keep Ada contained are proven by repeatable tests, and no path from the agent fleet to staging or prod credentials exists.
**Depends on**: Phase 2
**Requirements**: ACC-01, ACC-02, ACC-03, ACC-04, ACC-05, ACC-06
**Success Criteria** (what must be TRUE):
  1. A risky action in Ada's session produces a prompt in Slack; the platform owner's `yes <id>` lets it proceed, `no <id>` stops it, and a reply from anyone else is rejected.
  2. A message from a non-allowlisted sender gets no reaction, does not start a stopped host and never reaches the session.
  3. Ada's attempts to merge a pull request or push to `main` are refused, and `--dangerously-skip-permissions` is refused.
  4. One run of the `tests/agents/` checks passes the organization-wide IAM search, the exact-roles check on the host identity, the no-production-credentials check and the ADR-0002 confirmations (wake identity limited to get, start and stop; no Slack connection held by the wake service while the host runs; disk kept across an idle stop).
  5. `runbooks/agents/` holds a dated record of the results and the command to re-run them after any host or project change.
**Plans**: TBD

### Phase 4: Measured week and seat decision
**Goal**: One measured week with Ada produces the evidence for the seat decision, and the platform owner records it.
**Depends on**: Phase 3
**Requirements**: MEAS-01, MEAS-02, MEAS-03
**Success Criteria** (what must be TRUE):
  1. A daily report from the host collector shows tokens, estimated API-equivalent cost and seat-limit hits; the day-one report exists.
  2. Seven consecutive daily reports exist from a week of real tasks given in Slack, with extra usage off and the Team admin analytics and spend report read each day.
  3. A weekly summary shows limit hits per day and window, API-equivalent cost against the seat price, queue wait and pull-request counts.
  4. A follow-up ADR records the platform owner's decision on Standard versus Premium seats, seats versus API keys, and when to add agent #2.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Enforced agent policy | 0/0 | Not started | - |
| 2. GitHub draft-pull-request workflow | 0/0 | Not started | - |
| 3. Acceptance and isolation checks | 0/0 | Not started | - |
| 4. Measured week and seat decision | 0/0 | Not started | - |

## Deferred Beyond This Milestone

- GitHub Team plan, `main` ruleset, `CODEOWNERS` and the GitHub App (GHE-01 to GHE-03): after the platform owner upgrades the organization plan.
- Agent #2 and API-key overflow (FLEET-01, FLEET-02): after Anthropic's human answer and the Phase 4 decision.
- Staging and prod build-out (PLAT-01, PLAT-02): after the product's local edition.
