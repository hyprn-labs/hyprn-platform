---
phase: "7"
slug: "hardening-acceptance"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 7 — Validation Strategy

> Source: 07-RESEARCH.md ## Validation Architecture. Smallest phase: extend egress.sh, aggregate run.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Bash checks (`tests/agents/checks/*.sh` via run.sh) |
| **Config file** | none |
| **Quick run command** | `bash tests/agents/checks/egress.sh` (static subset anywhere; live probes SKIP/FAIL off-host by design) |
| **Full suite command** | `tests/agents/run.sh` on host as root (appends dated record) |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** `bash -n` + egress.sh static subset.
- **Before `/gsd-verify-work`:** owner-go host run.sh green.
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner — every task MUST carry `<automated>` + `<fails_when>`) | | | | | | | | | ⬜ pending |

---

## Wave 0 Requirements

- [ ] Extend `checks/egress.sh` — enforcement-on + per-agent drill assertions (no new file)
- [ ] Completed allowlist + rollback procedure + final kept record (plan outputs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Enforcement flip + no-break drill live | EGR-02 | Host apply, owner go | Owner applies, runs drill |
| Final full green run + kept record | ACC-10 | Host root run | Owner runs run.sh, keeps record |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
