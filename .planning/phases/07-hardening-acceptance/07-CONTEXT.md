# Phase 7: Hardening and acceptance - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning
**Mode:** Auto-discussed (user directed autonomous run without stops; all answers at agent discretion)

<domain>
## Phase Boundary

The fleet runs with egress enforced and every control proven in one final run: the domain allowlist (built from observed traffic) enforced without breaking Ada's or Boole's work, and the full `tests/agents/run.sh` passing with its dated record kept. Only two requirements (EGR-02, ACC-10). Depends on Phase 6; live enforcement and the final green run are owner-gated (host apply + real traffic).

</domain>

<decisions>
## Implementation Decisions

### Allowlist from observed + declared (auto-accepted at agent discretion)

- EGR-02 allowlist (`agents/policy/egress-allowlist.txt`, placeholder from Phase 1) is completed from observed traffic logs plus declared loop/tool destinations. No live traffic exists yet (observe mode never ran live) — the file ships with declared destinations + documented update procedure on first live observation; enforcement logic must handle empty-observed gracefully (fail-closed on unknown, never fail-open).
- Breaking-work protection: enforcement ships with a per-agent drill (Ada/Codd/Boole representative destinations) provable by dry-run/static; live proof gated.

### Final run aggregates, not duplicates (auto-accepted at agent discretion)

- ACC-10: the full `run.sh` pass is the aggregate of all phase checks; this phase adds only the enforcement-on assertions + the kept dated record. No new check domains.
- The kept record is the final acceptance artifact alongside per-phase records.

### Enforcement is a host apply (auto-accepted at agent discretion)

- Switching proxy observe→enforce is a host provisioning change needing owner-go apply. Plans deliver reviewed config + rollback procedure (one-command revert to observe mode); the flip itself is an owner checkpoint.

### Agent's Discretion

All Phase 7 answers at agent discretion under the autonomous-run direction.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `agents/policy/egress-allowlist.txt` (placeholder): completed here.
- Squid + nftables observe stack (Phase 1): enforcement extends it.
- `tests/agents/run.sh`: the final aggregate run.
- Rollback = config flip patterns from provisioning.

### Established Patterns

- Fail-closed, never fail-open; owner-go applies; dated records.

### Integration Points

- Proxy config + firewall rules + allowlist file (one enforced triple).
- run.sh final gate before verify-work.

</code>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Standing direction: enforcement flip is owner-go with rollback ready.

</specifics>

<deferred>
## Deferred Ideas

- Live traffic observation period (starts at first live apply).
- Post-acceptance tuning of the allowlist.

</deferred>

---

*Phase: 7-Hardening and acceptance*
*Context gathered: 2026-10-13*
