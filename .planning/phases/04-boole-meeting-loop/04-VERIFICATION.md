---
phase: 04-boole-meeting-loop
status: human_needed
score: 9/9 code truths verified, 0/4 live criteria closed
next_action: Owner executes runbooks/agents/meeting-loop-go.md (settle LOOP-01, create Workspace user + Notion share, place tokens, approve 10-meeting trial)
next_command: owner-go checklist in runbooks/agents/meeting-loop-go.md; then live trial
---

# Phase 4: Boole and the meeting loop — Verification Report

Goal-backward check against ROADMAP Phase 4 success criteria 1–4.
All code/fake evidence verified in the repo; live items are owner gates by design.

## Per-criterion verdicts

| # | Criterion (ROADMAP) | Code evidence | Verdict |
|---|---------------------|---------------|---------|
| 1 | Boole's grants match its declaration in `agents/loops/` and Terraform | `agents/loops/meeting.yaml` (agent_user boole, A1 notion-write, $30/30d, allowlist; `validate.py` exit 0) + `infra/agents/boole-notion.tf` (secret container declared-not-created, host-only accessor, no values) | CODE VERIFIED — live vendor objects pending owner |
| 2 | New meeting page triggers run within 5 min; owner approves Notion updates in Slack | `controller/poll_notion.py` (POLL_INTERVAL_SECONDS 300, idempotency_key notion-page-\<id\>, cursor-after-enqueue; 19/19 controller tests OK) + `hyprn-meeting-workflow` (park+exit, PATCH only on owner `Dispatcher.resume`, `record_cost`; `meeting.sh` 19/19 PASS) | CODE VERIFIED ON FAKES — live trigger + Slack approval pending owner |
| 3 | ≥10 real meetings in two weeks within $30/mo | Metered path present (budget in YAML, `record_cost` in workflow, ledger case in `meeting.sh`); no live runs by design | OWNER GATE — trial not started, gated by 04-03 checkpoint |
| 4 | Ada and Boole cannot reach each other's homes, secrets, containers, tokens, bots | `tests/agents/checks/isolation.sh` green (static assertions pass; ada/codd live legs pass; boole live legs SKIP cleanly — no boole user yet) | CODE VERIFIED — live boole legs pending provisioning |

## Must-have truths (9/9 on fakes)

- 04-01: one queued run per new page; duplicate never re-runs; meeting.yaml validates A1 — VERIFIED (`test_poll_notion` 7/7, full controller 19/19, validator green).
- 04-02: fixed JSON contract w/ quote rule; park-until-owner-yes; per-run cost + over-budget refuse — VERIFIED (`meeting.sh` 19/19, syntax OK, fake smoke in SUMMARY).
- 04-03: declarations-only, no vendor creation; 3-agent isolation; owner checklist gates trial — VERIFIED (static greps green, `isolation.sh` green-with-skips, `meeting-loop-go.md` checklist present).

## Human/owner gates (why human_needed, not passed)

1. LOOP-01 settling (Granola→Notion choice recorded) — owner decision, unsettled by design.
2. Vendor objects (Workspace user, Notion integration share, tokens in Secret Manager, Terraform apply) — owner checklist in `meeting-loop-go.md`, no dated entry yet.
3. Live trial (10 meetings / 2 weeks / $30) + live Slack approvals + live boole isolation legs — require keys, bot, and boole user provisioning.

## Gaps

None blocking code. No gaps_found: everything automatable is green; the rest is explicitly owner-gated per CONTEXT and the 04-03 blocking-human checkpoint.
