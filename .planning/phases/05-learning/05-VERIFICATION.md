---
phase: 05-learning
status: human_needed
score: 6/9
verified: 2026-10-14
machinery: 6/6 verified (green on seeds)
live_gates: 3 pending (owner/trial)
no_fabricated_real_results: true
next_action: Owner runs the trial plus vendor steps (Boole App creation, real runs, merges, promotion); machinery needs no rework.
next_command: Trial first, then `/gsd-verify-work` for Phase 5 live gates.
---

# Phase 5: Learning — Verification Report

Goal-backward verify, read-only. Machinery expected green on seeds;
App creation, real cases, merges, executed promotion are owner/live
gates. No fabricated real results confirmed.

## Per-criterion verdicts (ROADMAP Phase 5 SC 1–3)

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| SC1a | Feedback stored with each run (LRN-01) | ✅ VERIFIED | `controller/schema.sql` feedback table; `Dispatcher.record_feedback` closed kinds + dedupe + owner-gated approval insert; `python3 -m unittest discover -s controller` 26 tests OK; `learning.sh` zero FAIL |
| SC1b | Eval set holds ≥20 cases (seed machinery) (LRN-02) | ✅ VERIFIED (as seeds) | `agents/loops/meeting-eval.jsonl` = 20 lines, all `origin: seed`, `seed-` ids, 12 regression-true; `run.py --eval … --fixture …` → `seed: 20/20 pass, overall: PASS`; fixtures dir has 4 canned inputs + 4 canned outputs + SEED-README |
| SC1c | …at least 20 **real** cases | ⏳ OWNER/TRIAL GATE | By design (05-CONTEXT D-seeds): seeds labeled seeds everywhere; real-run cases arrive with the trial. `promotion.py` confirms `real: 0 runs considered`. Not a code gap. |
| SC2a | Improvement-PR gate proven (LRN-03 machinery) | ✅ VERIFIED | Runner fixture/live/post modes + `--post` seed-labeled body; `learning.sh` probes both directions live (pass queues for owner, fail stays draft, autonomy diffs rejected); no `gh pr merge` literal in new code (grep exit 1) |
| SC2b | …PR by `boole-agent-hyprn[bot]` passes evals and is **merged by owner** | ⏳ OWNER GATE | Fixture proof only in-phase; merge is explicitly the owner step (05-03 SUMMARY blockers). Not a code gap. |
| SC3a | Promotion rule check honest (LRN-04 machinery) | ✅ VERIFIED | `agents/eval/promotion.py` reads 3 thresholds from registry at check time, real-only counting, exits 3 with `INSUFFICIENT DATA (seeds excluded): 0 real runs` on seeds-only; changes no autonomy |
| SC3b | …loop **moves to A2** by reviewed change | ⏳ TRIAL GATE | Template only in-phase; executed promotion needs 10 real runs (deferred per D-promotion-template). Not a code gap. |
| OPS-03 | Boole App declared-not-created | ✅ VERIFIED | Manifest + `hyprn-platform`-only scope + Contents/PR-write + webhook inactive + broker path + owner checklist in `runbooks/agents/learning.md` + `github.md` row; declaration probes green; zero creation, zero key material |
| ANTI-FAB | No fabricated real results | ✅ VERIFIED | 0 lines with `origin: real`; runner prints `seed:`/`real:` tallies on separate lines; reports and PR body say seeds; `promotion.py` prints `seeds excluded` |

## Checks run (read-only)

- `python3 -m unittest discover -s controller` → 26 tests, OK.
- `bash tests/agents/checks/learning.sh` → zero FAIL, 3 live SKIP with reason (gateway host, PR-post token, bot wiring).
- `python3 agents/eval/run.py --eval agents/loops/meeting-eval.jsonl --fixture agents/loops/testdata/eval-fixtures` → `fixture pages: 4/4 shape-ok`, `seed: 20/20 pass`, `overall: PASS`.
- `python3 agents/eval/promotion.py agents/loops/meeting.yaml` → exit 3, `INSUFFICIENT DATA (seeds excluded)`.
- Full `tests/agents/run.sh` overall FAIL is the pre-existing off-host set only (unchanged across 05-01→05-03); `checks/learning` PASS throughout.

## Gaps

None in machinery. The three ⏳ items above are owner/trial gates, not gaps — no `/gsd-plan-phase --gaps` round needed.

## Next

Owner vendor + trial steps are listed in `05-03-SUMMARY.md` Blockers (App create → install on `hyprn-platform` only → key to broker → trial runs → merges → promotion). Re-verify live gates after the trial.
