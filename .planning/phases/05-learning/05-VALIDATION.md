---
phase: "5"
slug: "learning"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 5 — Validation Strategy

> Source: 05-RESEARCH.md ## Validation Architecture. Seeds labeled seeds everywhere; no fabricated real results.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash checks + Python stdlib `unittest` (auto-discovered by run.sh) |
| **Config file** | none |
| **Quick run command** | `bash -n` on touched scripts + `python3 -m unittest discover -s controller` |
| **Full suite command** | `tests/agents/run.sh` (dated record) |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** quick command above.
- **After every plan wave:** full harness.
- **Before `/gsd-verify-work`:** full suite green; real-run cases + executed promotion explicitly excluded (owner/live gates).
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner — every task MUST carry `<automated>` + `<fails_when>`) | | | | | | | | | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `agents/loops/meeting-eval.jsonl` — ≥20 seed cases (LRN-02)
- [ ] `controller/test_feedback.py` — LRN-01
- [ ] Eval runner (`--fixture` offline + live path + PR post) — LRN-02/03
- [ ] Promotion-check script (INSUFFICIENT DATA under 10 real runs) — LRN-04
- [ ] `checks/learning.sh` — OPS-03 static + LRN probes
- [ ] `agents/loops/testdata/eval-fixtures/` — offline eval proof

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Boole App creation | OPS-03 | Owner vendor step | Owner checklist |
| Real-run eval cases | LRN-02 | Arrive with trial | Trial feeds runner later |
| Improvement PR merge | LRN-03 | Owner merges | Owner merges passing PRs |
| Executed promotion | LRN-04 | Needs 10 real runs | Template only in-phase |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
