# Phase 4: Boole and the meeting loop - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning
**Mode:** Auto-discussed (user directed autonomous run without stops; all answers at agent discretion)

<domain>
## Phase Boundary

Each meeting becomes decisions, actions and Notion updates without the owner starting anything: Granola → Notion → loop → Slack with approved writes, Boole isolated from Ada. The Granola→Notion path (LOOP-01) is NOT settled — plans must build to a trigger seam, not a chosen integration. Boole's Workspace user and Notion integration are owner vendor steps. Depends on Phase 3 (code complete, live runs deferred-human).

</domain>

<decisions>
## Implementation Decisions

### Trigger seam, not integration (auto-accepted at agent discretion)

- LOOP-01 unsettled: plans target the settled seam — controller polls the Notion meetings database every 5 minutes, one run per new meeting page — and treat the Granola→Notion leg as a documented assumption with a file-drop/manual-page fallback for testing.
- No Granola credentials, scrapers, or unofficial APIs in plans. Settling LOOP-01 is an owner decision recorded before live runs, not an implementation task.

### Loop with approved writes (auto-accepted at agent discretion)

- Meeting loop at A1: extracts decisions/actions, proposes Notion updates, posts Slack summary; Notion writes need owner approval via Boole's Slack bot (approval-park pattern from Phase 3). Test with fakes (fake Notion pages, fake Slack answers).
- 10-meetings-in-two-weeks within $30/month is the live trial shape — plans deliver the metered path (cost per run visible via gateway budget path), the trial itself is an owner-go checkpoint.

### Isolation proven in code (auto-accepted at agent discretion)

- ACC-07: Ada and Boole cannot reach each other's homes, secrets, containers, tokens or bots — extend Phase 1's per-agent checks to Boole's declared identities (Linux user, secret names, container user, bot tokens) as static assertions + live checks gated on identities existing.
- Boole's GitHub App is Phase 5 (OPS-03) — not here.

### Identities declared, vendor steps listed (auto-accepted at agent discretion)

- OPS-02 (Workspace user + Notion integration, tokens in Secret Manager) ships as declarations + manifests + owner checklists. Nothing created vendor-side in execution.

### Agent's Discretion

All Phase 4 answers at agent discretion under the autonomous-run direction. Planner must not select a Granola integration.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `controller/dispatcher.py` + queue + approval-park (Phase 3): the meeting loop is the first registered loop.
- `agents/loops/` registry + validator: meeting-loop YAML is the reference example.
- Slack bot pattern (Ada channel server) for Boole's approval bot shape.
- `tests/agents/run.sh` + checks: loop checks join the one-command run.

### Established Patterns

- Fake seams for all external systems; owner-go checkpoints never automated.
- Dated records; least privilege; trigger payloads untrusted.

### Integration Points

- Notion meetings database (polled) → dispatcher → meeting loop → Slack summary + proposed Notion updates.
- Gateway budget path for per-run cost (keys later).

</code>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Standing direction: LOOP-01 settling is an owner decision; vendor steps are owner checklists.

</specifics>

<deferred>
## Deferred Ideas

- Granola→Notion integration choice (owner decision, LOOP-01).
- Boole's GitHub App (Phase 5, OPS-03).
- Learning/evals (Phase 5); second loops.

</deferred>

---

*Phase: 4-Boole and the meeting loop*
*Context gathered: 2026-10-13*
