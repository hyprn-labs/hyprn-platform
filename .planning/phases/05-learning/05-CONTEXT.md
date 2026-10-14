# Phase 5: Learning - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning
**Mode:** Auto-discussed (user directed autonomous run without stops; all answers at agent discretion)

<domain>
## Phase Boundary

The meeting loop gets better from the owner's feedback, with every change tested and merged by the owner: Boole's GitHub App, feedback stored with runs, eval set of 20+ real cases, eval runner, improvement pull requests that must pass evals, first promotion A1→A2 by reviewed change. No real runs exist yet (trial deferred-human) — eval content is seeded from fixtures and trial-shaped cases, then fed by real runs later. Depends on Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Evals without real runs yet (auto-accepted at agent discretion)

- Build the eval machinery (runner on host through gateway path with fakes, regression suite shape, 20-case minimum structure) seeded from Phase 4 fixtures and trial-shaped synthetic cases clearly marked as seeds. Real-run cases replace seeds as the trial produces them; the runner accepts both.
- No fabricated "real" results: seeds are labeled seeds everywhere (files, reports, PR bodies).

### Feedback capture ready (auto-accepted at agent discretion)

- Reactions, replies, approval decisions stored with their run (schema + writer path with fakes); Slack shape follows the channel-server event model. Live wiring waits for Boole's bot (owner vendor step).

### Improvement flow as code (auto-accepted at agent discretion)

- Improvement runs propose prompt/skill changes as draft PRs; the eval runner posts results on the PR; only passing changes reach the owner, who merges. Prove the flow with a fixture improvement (seed evals) end to end.
- Promotion A1→A2 ships as a reviewed-change template (rule check: ≥90% over last 10 + <1 correction/meeting), not an executed promotion.

### Boole's App declared-not-created (auto-accepted at agent discretion)

- OPS-03: App manifest + install-scope declaration (`hyprn-platform` only) + broker path, creation itself an owner checklist. No App creation, no keys in this phase's execution.

### Agent's Discretion

All Phase 5 answers at agent discretion under the autonomous-run direction.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- Phase 4 meeting loop + registry + approval-park: first improvement target and eval subject.
- `controller/` test fakes: eval runner extends the fake-seam pattern.
- Token broker + draft-PR contract (Phase 2): improvement PRs follow the same shape.
- `tests/agents/run.sh` + checks: eval checks join the one-command run.

### Established Patterns

- Fake seams for externals; owner merges; dated records; least privilege.

### Integration Points

- Eval runner posts on improvement PRs (needs Boole App + gateway live — gated).
- Feedback store beside run state (schema now, Cloud SQL with gateway apply).

</code>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Standing direction: seeds labeled seeds; vendor/live steps are owner checklists.

</specifics>

<deferred>
## Deferred Ideas

- Real-run eval cases (arrive with the trial).
- Executed A1→A2 promotion (needs 10 real runs + owner merge).
- Second loops' eval sets.

</deferred>

---

*Phase: 5-Learning*
*Context gathered: 2026-10-13*
