# Requirements: hyprn-platform

**Defined:** 2026-10-12
**Milestone:** Agent fleet operational
**Core Value:** The platform owner gives Ada a task in Slack and receives a reviewable draft pull request, and no path exists from the agent fleet to staging or prod credentials.

No PRD exists for this milestone. These requirements are derived from the remaining open items of the agent fleet plan (`docs/plans/agent-fleet.md`), the locked ADRs (0001, 0002, 0004) and the milestone success metric. Each is verifiable by the platform owner.

## v1 Requirements

### Agent policy (POL)

- [ ] **POL-01**: The Claude Code permission rules and sandbox settings for agents are reviewed in `agents/policy/`, applied organization-wide by the Team Owner in the admin console, and recorded in `runbooks/agents/`. Risky actions are relayed to Slack for approval.
- [ ] **POL-02**: Agent shell commands can reach only an explicit egress allowlist reviewed in `agents/policy/`; a request to any other host fails.
- [ ] **POL-03**: `strictKnownMarketplaces` is set organization-wide so only the `hyprn-agents` marketplace is accepted; an agent cannot add another marketplace.
- [ ] **POL-04**: Claude Code deny rules refuse merging pull requests, pushing to `main` and force pushing in `hyprn-platform` and `hyprn-mvp`. These rules are the enforcing control until a ruleset exists (ADR-0004).

### Account safeguards (SEC, DOC)

- [ ] **SEC-01**: A break-glass super admin exists with an offline key, holds no standing Google Cloud role, and its use procedure is written in `runbooks/agents/gcp.md` without secrets.
- [ ] **SEC-02**: The `hyprn-labs` GitHub organization requires two-factor authentication for all members, including the machine account.
- [x] **DOC-01**: ADR-0003 is accepted and linked from `docs/adr/README.md`. It states that our own Slack channel server is the plugin and supersedes the "vendored community plugin" wording of ADR-0001 section 6. Plan task D1 and `agents/marketplace/README.md` match.

### GitHub workflow (GH)

- [ ] **GH-01**: From a Slack task given by the platform owner, Ada creates branch `agent/ada/<slug>`, pushes it and opens a draft pull request authored by `ada-agent-hyprn`. The description states what changed and how it was verified. Commits carry "Ada (AI agent)".
- [ ] **GH-02**: A worktree helper creates one worktree per task on branch `agent/<name>/<slug>` and sets its own port block, Compose project name and test database name as environment variables. Two worktrees run side by side without collisions.
- [ ] **GH-03**: The secrets with the former names (`agent-ada-*`) are deleted after the switch to `<name>-agent-<purpose>`, the earlier tokens are deleted in the agent account, and `runbooks/agents/github.md` records the token's expiry date and the next rotation date.

### Acceptance and isolation (ACC)

- [ ] **ACC-01**: Permission relay works in Slack: a risky action produces a prompt in the platform owner's conversation; `yes <id>` from the platform owner lets it proceed and `no <id>` stops it.
- [ ] **ACC-02**: A message from a non-allowlisted Slack sender gets no reaction, does not wake a stopped host and never reaches the session; an approval from a non-allowlisted sender is rejected.
- [ ] **ACC-03**: Ada's attempts to merge a pull request or push to `main` are refused, and `--dangerously-skip-permissions` is refused.
- [ ] **ACC-04**: An isolation check in `tests/agents/` searches IAM organization-wide and passes only if `hyprn-agents` principals hold roles inside `hyprn-agents` alone, no staging or prod principal holds a role inside it, and the host identity holds exactly log and metric writing plus `secretAccessor` on named secrets. The check can be re-run on demand and when staging and prod exist.
- [ ] **ACC-05**: A dedicated no-production-credentials check in `tests/agents/` passes only if the host holds no user cloud credentials, no key files, no staging or prod roles and no staging or prod secrets.
- [ ] **ACC-06**: The ADR-0002 confirmations are recorded with evidence: the wake identity is refused any action other than get, start and stop on the host; the wake service holds no Slack connection while the host runs; the host keeps its disk across an idle stop.

### Measurement (MEAS)

- [ ] **MEAS-01**: Claude Code OpenTelemetry export from the agent host reaches a collector on the host, and a daily report shows tokens, estimated API-equivalent cost and seat-limit hits. The day-one report exists.
- [ ] **MEAS-02**: One week of real tasks given by the platform owner runs with extra usage off, with the Team admin analytics and spend report read daily. Seven consecutive daily reports exist.
- [ ] **MEAS-03**: A weekly summary reports limit hits per day and window, API-equivalent cost against the seat price, queue wait and pull-request counts. The platform owner records the decision on Standard versus Premium seats, seats versus API keys, and when to add agent #2 in a follow-up ADR.

## Deferred Requirements (after this milestone)

### GitHub enforcement (GHE)

- **GHE-01**: GitHub Team plan active, a human team for code owners, `CODEOWNERS` in each working repository, and a ruleset on `main` requiring a pull request, human code-owner approval, stale-approval dismissal, no force push and no bypass. Trigger: the platform owner upgrades the organization plan. Claude Code deny rules (POL-04) remain as defense in depth.
- **GHE-02**: A GitHub App `hyprn-ada` replaces the machine account: Contents and Pull requests read/write, Metadata read, no Workflows or Administration, selected repositories, one-hour installation tokens from a token helper, commits as the App. Trigger: GHE-01 done (ADR-0001 section 5).
- **GHE-03**: Acceptance for GHE-01 and GHE-02: merge by the agent refused by GitHub, push to `main` refused by GitHub, approval by an agent identity does not satisfy the rule.

### Fleet growth (FLEET)

- **FLEET-01**: Agent #2 with its own identities and seat. Trigger: Anthropic's human answer on agent seats and the MEAS-03 decision.
- **FLEET-02**: Overflow through API keys or an open-weight low-cost tier. Trigger: MEAS-03 finds seat limits binding.

### Platform build-out (PLAT)

- **PLAT-01**: Staging and prod projects, hosts, buckets, reconciler, deployment contract, CI identities and the product delivery pipeline as defined in `docs/specs/cloud-platform.md`. Trigger: the product's local edition is ready.
- **PLAT-02**: Re-run the ACC-04 isolation check when staging and prod are created.

## Out of Scope

| Item | Reason |
|------|--------|
| Staging and prod environments, deployment contract, host reconciler, delivery pipeline | Follow the product's local edition; specified in the platform specification |
| Agent #2 | Gated on Anthropic's human answer on agent seats |
| Product support for per-worktree overrides | Product work in `hyprn-mvp` |
| Signed commits | Not required for now (ADR-0001 section 5) |
| Product code in this repository | Belongs in `hyprn-mvp` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| POL-01 | Phase 1 | Pending |
| POL-02 | Phase 1 | Pending |
| POL-03 | Phase 1 | Pending |
| POL-04 | Phase 1 | Pending |
| SEC-01 | Phase 1 | Pending |
| SEC-02 | Phase 1 | Pending |
| DOC-01 | Phase 1 | Complete |
| GH-01 | Phase 2 | Pending |
| GH-02 | Phase 2 | Pending |
| GH-03 | Phase 2 | Pending |
| ACC-01 | Phase 3 | Pending |
| ACC-02 | Phase 3 | Pending |
| ACC-03 | Phase 3 | Pending |
| ACC-04 | Phase 3 | Pending |
| ACC-05 | Phase 3 | Pending |
| ACC-06 | Phase 3 | Pending |
| MEAS-01 | Phase 4 | Pending |
| MEAS-02 | Phase 4 | Pending |
| MEAS-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-10-12*
*Last updated: 2026-10-12 after roadmap creation*
