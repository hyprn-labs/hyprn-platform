---
phase: "3"
slug: "control-plane-core"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 3 — Validation Strategy

> Source: 03-RESEARCH.md ## Validation Architecture. No new test framework (pytest absent).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `tests/agents/run.sh` harness + `python3 -m unittest` (stdlib) |
| **Config file** | none (`tests/agents/checks/*.sh` auto-discovered) |
| **Quick run command** | `python3 -m unittest discover -s controller` + `bash -n` on new shell files |
| **Full suite command** | `tests/agents/run.sh` (dated record per ACC-08) |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** quick command above.
- **After every plan wave:** full harness.
- **Before `/gsd-verify-work`:** full suite green; live test-loop run explicitly excluded (owner-go checkpoint).
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner — every task MUST carry `<automated>` + `<fails_when>`) | | | | | | | | | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `agents/loops/validate.py` + testdata — CP-05, EGR-03 schema side
- [ ] `controller/schema.sql` + `dispatcher.py` with fake seams — CP-02/03/04
- [ ] `controller/test_dispatcher.py` (stdlib unittest, fakes only)
- [ ] `hyprn-credential-broker` + `hyprn-run-runner` — CP-06, RT-01
- [ ] `infra/agents/gateway.tf` + `controller.tf` + `boole.tf` (reviewed, not applied) — CP-01, OPS-01, ACC-09
- [ ] `checks/loops.sh`, `checks/controller.sh`, `checks/runner.sh` wired into run.sh

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live test-loop run on Fireworks | Phase goal | Needs provider keys + owner go | Owner provides keys, approves run |
| Gateway/controller Terraform apply | CP-01, ACC-09 | Cloud mutations need exact-plan go | Owner reviews plan, applies |
| Boole vendor objects (Slack app, keys) | OPS-01 | Human vendor steps | Owner checklists in runbook |
| Revised budget set | COST-01 | Owner finance decision | Owner sets, records |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
