---
phase: "1"
slug: "security-baseline"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash + `tests/agents/host-checks.sh` (no language test runner in this repo) |
| **Config file** | none — Wave 0 installs nothing |
| **Quick run command** | `tests/agents/host-checks.sh` |
| **Full suite command** | `tests/agents/run.sh` (created in this phase, ACC-08) |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `tests/agents/host-checks.sh`
- **After every plan wave:** Run `tests/agents/run.sh`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner per task — every task MUST carry `<automated>` + `<fails_when>`) | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/agents/run.sh` — orchestrator stub covering host checks + security checks (ACC-08)

*Existing infrastructure (`tests/agents/host-checks.sh`, 40 passing checks) covers the host baseline; Wave 0 adds the runner.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Break-glass admin exists with offline key material | SEC-01 | Owner hands only; must never be automated | Owner confirms per runbook checklist; plan requests explicit go |
| 2FA required in hyprn-labs | SEC-02 | GitHub org setting, owner hands | Owner confirms org setting screenshot/state |
| Admin-console policy matches managed-settings.json | POL-01 | Team Owner applies in console | Owner applies reviewed file, records in runbook |
| Alert emails delivered | DET-01/02 | Test secret read + IAM change need owner-go actions | Owner performs test actions on go; confirm mail receipt |
| Slack permission relay + sender allowlist | ACC-01/02 | Needs live Ada session + owner messages | Owner drives live session test |
| IAM search with owner credentials | ACC-04 | Requires owner-cred gcloud | Owner runs search, planner lists exact expected roles |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
