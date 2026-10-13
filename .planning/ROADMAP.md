# Roadmap: hyprn-platform

## Overview

Three milestones, each ending with something that works, in the owner's value order. **M1** makes the engineering agent Ada safe and efficient, and proves its safety. **M2** ships the second agent, Boole — an operations agent on open models with an API key — and with it the control plane, triggers, tools and learning, proven on one real loop: meeting notes into actions that improve from the owner's feedback. **M3** turns what the two agents proved into one command for adding more. Target: [`docs/specs/agent-fleet.md`](../docs/specs/agent-fleet.md). Requirement IDs: [`REQUIREMENTS.md`](REQUIREMENTS.md).

Each phase adds its checks to `tests/agents/run.sh` (ACC-08), so every later phase starts from a passing run.

## Milestones

- **M1 — Safe engineering agent** (Phases 1–2)
- **M2 — Boole, the ops agent, with a learning meeting loop** (Phases 3–5)
- **M3 — Scale the fleet** (Phases 6–7)

## Phases

- [ ] **Phase 1: Security baseline** - GitHub ruleset on `main`, enforced Claude Code policy, egress observation, alerts, account safeguards, and the first proven checks
- [ ] **Phase 2: Engineering workflow** - Slack-to-draft-PR, worktree per task, toolchains and caches, herdr as cockpit and host runtime, telemetry
- [ ] **Phase 3: Control plane core** - Gateway, controller, loop registry, credential broker, run runner, approvals, budgets, kill switch; Boole's runtime identities
- [ ] **Phase 4: Boole and the meeting loop** - Granola → Notion → loop → Slack with approved writes; isolation between Ada and Boole
- [ ] **Phase 5: Learning** - Boole's App, feedback, evals, scoped improvement pull requests, first promotion
- [ ] **Phase 6: Fleet as code and onboarding** - `fleet.yaml`, `fleet add` and `remove` for both kinds, Workspace users
- [ ] **Phase 7: Hardening and acceptance** - Egress allowlist enforced, full acceptance run

## Phase Details

### Phase 1: Security baseline  (M1)
**Goal**: `main` is protected by GitHub, Ada runs under enforced policy, outbound traffic is visible, misuse of secrets or IAM raises an alert, and the safety controls are proven by one command.
**Depends on**: Nothing
**Requirements**: GHE-01, GHE-03, POL-01, POL-02, POL-03, POL-04, EGR-01, DET-01, DET-02, SEC-01, SEC-02, DOC-01, ACC-01, ACC-02, ACC-03, ACC-04, ACC-05, ACC-06, ACC-08
**Owner actions**: upgrade `hyprn-labs` to the GitHub Team plan; apply the policy in the Claude admin console; create the break-glass admin; require two-factor authentication in `hyprn-labs`.
**Success Criteria**:
  1. The ruleset protects `main` in every repository; GitHub refuses a merge or push to `main` by Ada's App.
  2. The admin console policy matches `agents/policy/managed-settings.json`; routine worktree work runs without prompts.
  3. Approvals from Slack work and only the owner's count; other senders are ignored; merge, push to `main`, force push and bypass mode are refused.
  4. The egress proxy logs each agent's destinations; a direct outbound connection is dropped.
  5. A test secret read by an unexpected principal and a test IAM change each produce an email alert to `gcp-admins`.
  6. `tests/agents/run.sh` passes and writes a dated record.
**Plans**: TBD

### Phase 2: Engineering workflow  (M1)
**Goal**: Ada turns Slack tasks into draft pull requests from clean worktrees, and the owner sees every session in one cockpit.
**Depends on**: Phase 1
**Requirements**: GH-01, GH-02, GH-03, EFF-01, EFF-02, COK-01, COK-02, OBS-01
**Success Criteria**:
  1. A Slack task yields a draft pull request by `ada-agent-hyprn[bot]`; Ada does not merge it.
  2. Two worktrees run side by side; merged or closed work leaves nothing behind.
  3. A fresh worktree runs the product's tests without installing toolchains.
  4. herdr on the laptop shows the owner's local sessions and Ada's host sessions side by side; Ada's sessions run under herdr and come back after a reboot.
  5. Ada's daily usage report is posted to Slack.
**Plans**: TBD

### Phase 3: Control plane core  (M2)
**Goal**: Autonomous runs have a safe, metered path end to end, ready for Boole's first loop.
**Depends on**: Phase 2; ADR-0006 accepted.
**Requirements**: CP-01, CP-02, CP-03, CP-04, CP-05, CP-06, RT-01, EGR-03, OPS-01, COST-01, ACC-09
**Owner actions**: open a Fireworks account and key; link the Anthropic Console organization to the Team plan (API credits) and create its key; create an OpenAI API key; create Boole's Slack app; set the revised budget.
**Success Criteria**:
  1. A test loop declared in `agents/loops/` runs on an open model at Fireworks, through the gateway, in a fresh container under `boole` with only its declared credentials, and reaches only the destinations on its loop's allowlist; its cost is logged.
  2. A run waits hours for an approval to Boole's Slack bot and resumes; a run over budget is refused; the kill switch stops a run within a minute.
  3. Switching the test loop to Claude changes its binding only.
  4. The controller and gateway checks pass and are part of `tests/agents/run.sh`.
**Plans**: TBD

### Phase 4: Boole and the meeting loop  (M2)
**Goal**: Each meeting becomes decisions, actions and Notion updates without the owner starting anything.
**Depends on**: Phase 3; how Granola notes reach Notion is settled.
**Requirements**: OPS-02, LOOP-01, LOOP-02, LOOP-03, ACC-07
**Owner actions**: create Boole's Workspace user; create the Notion integration and share the meetings database.
**Success Criteria**:
  1. Boole's grants match its declaration in `agents/loops/` and Terraform.
  2. A new meeting page triggers a run within 5 minutes; the owner approves Notion updates in Slack.
  3. At least 10 real meetings in two weeks, within 30 USD a month.
  4. Ada and Boole cannot reach each other's homes, secrets, containers, tokens or bots.
**Plans**: TBD

### Phase 5: Learning  (M2)
**Goal**: The meeting loop gets better from the owner's feedback, with every change tested and merged by the owner.
**Depends on**: Phase 4
**Requirements**: OPS-03, LRN-01, LRN-02, LRN-03, LRN-04, LRN-05
**Owner actions**: choose where agent-improvable prompts and skills live (folders here or a separate playbook repository, spec §10); create Boole's GitHub App; name the paths each improving agent may change.
**Success Criteria**:
  1. A pull request by an improving agent that changes a file outside its declared paths fails the required scope check and cannot be merged.
  2. Feedback is stored with each run; the eval set holds at least 20 real cases.
  3. An improvement pull request by `boole-agent-hyprn[bot]` passes the evals and is merged by the owner.
  4. The loop reaches its promotion rule and moves to A2 by a reviewed change.
**Plans**: TBD

### Phase 6: Fleet as code and onboarding  (M3)
**Goal**: Adding or removing an engineering or operations agent is one command.
**Depends on**: Phase 5
**Requirements**: FLT-01, FLT-02, FLT-03, FLT-04, FLT-05, FLT-06, FLT-07, FLT-08
**Owner actions**: assign the Workspace user-management admin role to the automation service account; the vendor approvals during the test onboardings.
**Success Criteria**:
  1. `agents/fleet.yaml` is the only declaration of agents; `agents.txt` and `wake.json` are gone.
  2. A test agent of each kind is onboarded and offboarded within 15 minutes and about 8 human actions (the engineering test stops before the Claude seat invitation).
  3. Ada runs as a Workspace user; the onboarding runbook stands on its own.
**Plans**: TBD

### Phase 7: Hardening and acceptance  (M3)
**Goal**: The fleet runs with egress enforced and every control proven in one final run.
**Depends on**: Phase 6
**Requirements**: EGR-02, ACC-10
**Success Criteria**:
  1. The egress allowlist is enforced without breaking Ada's or Boole's work.
  2. The full `tests/agents/run.sh` passes and its dated record is kept.
**Plans**: TBD

## Progress

| Phase | Milestone | Status |
|-------|-----------|--------|
| 1. Security baseline | M1 | Not started |
| 2. Engineering workflow | M1 | Not started |
| 3. Control plane core | M2 | Not started |
| 4. Boole and the meeting loop | M2 | Not started |
| 5. Learning | M2 | Not started |
| 6. Fleet as code and onboarding | M3 | Not started |
| 7. Hardening and acceptance | M3 | Not started |

## Deferred

Further Claude-seat agents, GitHub Issues intake, Slack plan, finance and e-signature tools, webhook receiver, staging and prod — with their triggers in [`REQUIREMENTS.md`](REQUIREMENTS.md).
