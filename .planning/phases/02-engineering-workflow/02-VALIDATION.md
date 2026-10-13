---
phase: "2"
slug: "engineering-workflow"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: 02-RESEARCH.md ## Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash (`tests/agents/run.sh` runs `host-checks.sh` then every executable `tests/agents/checks/*.sh`, dated record to `runbooks/agents/`) |
| **Config file** | none |
| **Quick run command** | `bash -n <changed-script> && shellcheck <changed-script>` |
| **Full suite command** | `tests/agents/run.sh` (static subset off-host; full green on host after owner-go apply) |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** syntax gate above (no host needed).
- **After every plan wave:** `run.sh` static subset off-host (host-only live checks SKIP).
- **Before `/gsd-verify-work`:** Full `run.sh` green on the host; live GH-01/COK-02/OBS-01 proofs additionally gated on Phase 1 green run.
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner per task — every task MUST carry `<automated>` + `<fails_when>`) | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/agents/checks/worktree.sh` — GH-02 (two-worktree isolation + cleanup incl. volumes/DBs)
- [ ] `tests/agents/checks/herdr.sh` — COK-02 (unit active, version pin + checksum, p2p off, hooks in policy)
- [ ] `tests/agents/checks/eff.sh` — EFF-01/EFF-02 (toolchain pins, cache persistence markers)
- [ ] `tests/agents/checks/obs.sh` — OBS-01/CODD-03 (collector reachability, digest dry-run, Zen-check staleness)
- [ ] Extend `tests/agents/checks/github.sh` — GH-01 (PR body contract + live bot-author) + GH-03 (negative grep)
- [ ] Runbook `runbooks/agents/engineering-workflow.md` — COK-01 owner checklist (laptop, seats, Remote Control, machine add over IAP)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Laptop cockpit shows local + host sessions | COK-01 | Owner laptop, owner hands | Owner checklist in runbook, dated row |
| Daily digest actually posts to Slack | OBS-01 | Real daily post observed | Dry-run automated; owner confirms first real post |
| Monthly Zen terms still acceptable | CODD-03 | Terms judgment | Owner confirms; dated row ≤ 31 days |
| Live GH-01/COK-02 proofs | GH-01, COK-02 | Gated on Phase 1 green run + host apply | Owner-go apply, then live run |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
