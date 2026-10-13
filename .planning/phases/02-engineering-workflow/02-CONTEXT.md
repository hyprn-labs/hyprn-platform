# Phase 2: Engineering workflow - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning
**Mode:** Auto-discussed (user directed autonomous run without stops; all answers at agent discretion)

<domain>
## Phase Boundary

Ada turns Slack tasks into draft pull requests from clean worktrees, and the owner sees every session in one cockpit. Slack-to-PR from task tags, one worktree per task with cleanup, pinned toolchains and persistent caches, herdr as laptop cockpit and host runtime, daily usage telemetry. Depends on Phase 1 (verification deferred-human — live proofs pending; plans must order Phase 2 live tests after the Phase 1 green run or mark them gated).

</domain>

<decisions>
## Implementation Decisions

### Worktree helper (auto-accepted at agent discretion)

- Extend the `opencode-task` pattern (`agents/host/files/bin/opencode-task`): one worktree per task on branch `agent/<name>/<slug>`, with its own port block, Docker Compose project, and test database; worktree and local branch removed on merge/close.
- Product-side overrides (port, Compose project, database from environment) are deferred to `hyprn-mvp` — known blocker in STATE.md; the helper must work without them and pick them up when the product provides them.

### Slack-to-PR flow (auto-accepted at agent discretion)

- Build on the channel server's task tags (`agents/marketplace/plugins/slack/server.py`) and the token broker (ADR-0005). Draft PRs authored by the agent bot state what changed and how it was verified; the agent never merges (deny rules backstop until the ruleset).
- Codd's terminal-driven draft-PR contract (`runbooks/agents/opencode.md`) is the same shape — one contract for both engineering agents.

### herdr cockpit and runtime (auto-accepted at agent discretion)

- Laptop runs herdr as cockpit (owner seats + agent host over IAP SSH; one Claude Code config dir per seat; Remote Control for owner seats). Host replaces the tmux wrapper (`hyprn-agent@.service`, `hyprn-agent-session`) with pinned herdr (checksum-verified, systemd under the agent user, hooks allowed by POL-01); tmux stays the fallback.
- Agent-to-agent prompting stays off (locked, waits on Anthropic). Laptop install, seat config, and host provisioning apply are owner-go checklists, never automated.

### Toolchains, caches and telemetry (auto-accepted at agent discretion)

- Provisioning installs the toolchains the product repositories pin (EFF-01); package and Docker layer caches persist per agent across tasks and host stops (EFF-02).
- Claude Code telemetry reaches a host collector; a daily per-agent report (tokens, cost, seat-limit hits) posts to Slack (OBS-01). The CODD-03 monthly free-tier model/terms re-check rides the same reporting cycle.

### Agent's Discretion

All Phase 2 answers were taken at agent discretion under the user's autonomous-run direction. Anything the planner finds unimplementable comes back as a planning question.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `agents/host/files/bin/opencode-task`: branch-per-task worktree creator — the GH-02 helper extends this, not a new tool.
- `agents/marketplace/plugins/slack/server.py`: task tags, sender allowlist, catch-up threads — GH-01 builds here.
- `agents/host/files/hyprn-agent@.service` + `hyprn-agent-session`: tmux session runtime herdr replaces (COK-02).
- `agents/host/provision.sh`: toolchain installs to extend for EFF-01; per-agent caches persist alongside.
- `agents/wake/wake.py` + host idle-stop: activity model running containers must respect (RT-01 later, do not break now).

### Established Patterns

- One task = one branch = one worktree = one draft PR; owner merges.
- Root-owned marketplace and managed configs; dated records per run in `runbooks/agents/`.
- `set -euo pipefail` scripts; systemd user units per agent.

### Integration Points

- Slack channel server (task intake) → worktree helper → draft PR (bot author) → owner merge.
- herdr on laptop (cockpit) ↔ herdr on host (runtime) over IAP SSH.
- Telemetry collector on host → daily Slack digest.

</code>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Standing direction: owner go per infra/vendor step; Codd's App covers both repositories; Phase 1 live proofs pending.

</specifics>

<deferred>
## Deferred Ideas

- Product-side worktree overrides (hyprn-mvp reads port/Compose/DB from environment).
- Agent-to-agent prompting (waits on Anthropic's answer).
- GitHub Issues intake (FLEET-04); Boole/control-plane work (Phases 3–5).

</deferred>

---

*Phase: 2-Engineering workflow*
*Context gathered: 2026-10-13*
