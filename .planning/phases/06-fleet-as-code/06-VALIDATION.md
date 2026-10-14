---
phase: "6"
slug: "fleet-as-code"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 6 — Validation Strategy

> Source: 06-RESEARCH.md ## Validation Architecture. Live vendor approvals are owner gates.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash checks harness (`tests/agents/run.sh` + `checks/*.sh`) |
| **Config file** | none |
| **Quick run command** | `bash tests/agents/checks/fleet.sh` |
| **Full suite command** | `tests/agents/run.sh` (dated record) |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** fleet.sh static (validate + regen-clean + no-value-flags).
- **After every plan wave:** dry-run both kinds (timed, checklist counted).
- **Before `/gsd-verify-work`:** full suite green; live vendor approvals explicitly excluded.
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner — every task MUST carry `<automated>` + `<fails_when>`) | | | | | | | | | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `agents/fleet.yaml` + validator — FLT-01, CODD-02 schema side
- [ ] `agents/fleet` add/remove (dry-run capable) — FLT-06/07, CODD-02 path
- [ ] Spike finding records (FLT-02/03/05) — recorded probes, not rabbit holes
- [ ] `runbooks/agents/onboarding.md` — FLT-08
- [ ] `checks/fleet.sh` — FLT-01/04/06/07/08 + CODD-02 assertions

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live test onboardings with vendor approvals | FLT-06 | Human vendor steps | Owner gates, ~8 actions |
| Workspace admin-role assignment | Phase 6 owners | Console step | Owner assigns, records |
| Ada group→user move | FLT-02 | Console step | Owner executes later |
| Claude-seat invitation | FLT-06 | No member API | Engineering test stops before it |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
