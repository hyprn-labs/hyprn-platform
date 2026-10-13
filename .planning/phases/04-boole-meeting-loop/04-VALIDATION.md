---
phase: "4"
slug: "boole-meeting-loop"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 4 — Validation Strategy

> Source: 04-RESEARCH.md ## Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python 3 stdlib `unittest` + Bash `tests/agents/checks/*.sh` (auto-discovered) |
| **Config file** | none |
| **Quick run command** | `python3 -m unittest discover -s controller && bash tests/agents/checks/meeting.sh tests/agents/checks/isolation.sh` |
| **Full suite command** | `bash tests/agents/run.sh` (dated record) |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** quick command above.
- **After every plan wave:** full harness.
- **Before `/gsd-verify-work`:** full suite green; live trial (10 meetings, LOOP-03 budget) explicitly excluded — owner-go checkpoint.
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner — every task MUST carry `<automated>` + `<fails_when>`) | | | | | | | | | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `controller/poll_notion.py` + `test_poll_notion.py` — LOOP-01
- [ ] `agents/loops/meeting.yaml` + prompts + testdata pages — LOOP-02 fixtures
- [ ] `agents/host/files/hyprn-meeting-workflow` — LOOP-02 run path
- [ ] `infra/agents/boole-notion.tf` (declared-not-created) — OPS-02
- [ ] `checks/meeting.sh` — LOOP-01/02/03 + OPS-02 static assertions
- [ ] `checks/isolation.sh` — ACC-07

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Granola→Notion leg choice | LOOP-01 | Owner decision, unsettled | Owner settles, records |
| Notion integration + Workspace user creation | OPS-02 | Human vendor steps | Owner checklists in runbook |
| 10-meeting live trial within budget | LOOP-03 | Live trial, needs gateway+keys | Owner-go checkpoint after keys |
| Notion-write approvals in Slack | LOOP-02 | Needs Boole bot + owner | Live, gated on trial |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
