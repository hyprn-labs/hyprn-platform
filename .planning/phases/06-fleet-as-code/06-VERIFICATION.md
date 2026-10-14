---
status: human_needed
score: 1/4
phase: 06-fleet-as-code
verified: 2026-10-14
criteria_total: 4
criteria_passed: 1
criteria_partial: 3
criteria_failed: 0
next_action: "Owner executes the gated live trial (Workspace admin role, vendor approvals, Ada group-to-user move) and records runbook acceptance (closes the 06-03 blocking-human checkpoint)."
next_command: "Owner-gated live trial per runbooks/agents/onboarding.md — no further /gsd-plan-phase --gaps for SC1."
gates:
  - "SC1 CLOSED by 06-04 (re-verified): legacy files deleted from git, all consumers render at provision/check time, byte-identical outputs."
  - "Live vendor approvals + owner trial not executed (by design): dry-run proof green, live onboarding/offboarding ungated work remains."
  - "06-03 Task 3 blocking-human checkpoint (owner runbook acceptance + live-trial approval) not recorded."
---

# Phase 6 Verification: Fleet as code and onboarding

**Goal (ROADMAP):** Adding or removing an engineering or operations agent is one command.
**Mode:** Read-only, goal-backward. SUMMARY claims treated as leads, not evidence.
**Checks run:** `bash tests/agents/checks/fleet.sh` (30 PASS, exit 0), `fleet-validate` (exit 0), `fleet-render --check` (exit 0), live `fleet add/remove --dry-run` probes, consumer grep traces.
**Re-verification (06-04, read-only):** `git ls-files` deletion proofs, `fleet-render --agents-out/--wake-out` diffs vs pre-deletion blobs (both empty), consumer grep traces, `fleet.sh` 34 PASS exit 0, `fleet-render --check` + `fleet-validate` exit 0, `wake.py` untouched, full `run.sh` SCRIPT profile unchanged.

## Per-criterion verdicts (ROADMAP Phase 6 SC 1-4)

**Re-verification regression check (06-04):** SC2–SC4 verdicts unchanged — `fleet.sh` dry-run/evidence assertions green within the 34 PASS, `runbooks/agents/onboarding.md` + `infra/agents/workspace.tf` + `agents/fleet.yaml` all present, `run.sh` profile identical to baseline. No regressions.

### SC1 — `agents/fleet.yaml` is the only declaration; `agents.txt` and `wake.json` are gone — PASS (closed by 06-04, re-verified)
- **Proven (re-verification, read-only):** `git ls-files agents/host/agents.txt agents/wake/wake.json` returns empty and neither path exists in the working tree (deletion commit `2f32bd9`); `fleet-render --agents-out/--wake-out` diffs empty against the pre-deletion blobs (`AGENTS_PARITY_OK`, `WAKE_PARITY_OK`); `agents/host/provision.sh:270-272` runs validate-then-render-to-mktemp-then-parse with the `add_agent` loop body untouched; `agents/wake/provision.sh:19-20` validates fail-closed then renders `--wake-out` directly to `/etc/hyprn-agents/wake.json` (the path `wake.py` reads); `git diff` shows `wake.py` byte-untouched; `egress.sh`/`github.sh`/`herdr.sh`/`host-checks.sh`/`ada-digest` all use render-to-temp (`mktemp` + `fleet-render --agents-out`, loop bodies untouched); remaining `agents.txt`/`wake.json` string references under `agents/`+`tests/` are comments, the renderer definition itself, or `fleet.sh` proof lines — zero live readers of committed legacy paths; `fleet.sh` 34 PASS exit 0 (incl. git-ls-files deletion proofs, no-live-readers scan, render-parity `ada 20001`/`codd 20002`/wake `[ada]`); `fleet-render --check` + `fleet-validate` exit 0; full `run.sh` SCRIPT-PASS/FAIL profile unchanged vs pre-change baseline (remaining FAILs host-gated off-host by design).
- **Requirement impact:** FLT-01 replacement half met (single hand-edited declaration + deterministic render + full consumer migration proven).

### SC2 — Test agent of each kind onboarded and offboarded within 15 min / ~8 actions (eng stops before seat invite) — PARTIAL (dry-run proven, live gated)
- **Proven:** `agents/fleet add test-eng --kind engineering --harness opencode --dry-run` and `add test-ops --kind operations --dry-run` both exit 0 with numbered 8-action owner checklists; engineering output states the seat-invite stop; remove `--dry-run` exits 0 with manual-remainder table and leaves the tree clean (`git status` clean asserted in fleet.sh); timed EVIDENCE lines (0s, 8 actions — inside 15-min/~8-action budget) present for both kinds; fail-closed probes (no `--owner-go` refusal, bad-name refusal) pass; handles-only secrets asserted over `agents/fleet`.
- **Not proven:** no live onboarding or offboarding executed — no test agent was ever created or removed. Vendor steps exist only as printed go-checklists. Per 06-CONTEXT this was the agreed shape (live vendor approvals are owner gates), but the SC as written ("is onboarded and offboarded") is not observably true in any environment.
- **Requirement impact:** FLT-06/FLT-07 dry-run halves met; live halves pending owner trial. FLT-04 manifest-flow/API-discovery exists only as dry-run intent text, no live App created (by design).

### SC3 — Ada runs as a Workspace user; the onboarding runbook stands on its own — PARTIAL (runbook proven, Ada move pending)
- **Proven:** `runbooks/agents/onboarding.md` exists and covers prerequisites, per-kind add flows (Claude, Codd-pattern, operations), remove + manual-remainder table, vendor appendix referencing all three findings, dated Record table, out-of-scope items — asserted green in fleet.sh. All three spike findings exist with explicit `Standing verdict: manual step` lines (workspace FLT-02, slack-icon FLT-03, setup-token FLT-05); `infra/agents/workspace.tf` declares the `workspace-user-admin` service account + prebuilt User Management Admin role shape, marks the grant and Ada's group-to-user move as owner console steps, forbids DWD.
- **Not proven:** `fleet.yaml` still declares ada `workspace: group` (transient pre-move state); no Workspace user exists for Ada; admin-role grant not performed (owner console step). Findings are static-evidence-only records of blocked attempts — complete as spikes per plan, but no live probe (DWD-free `users.insert`, `apps.icon.set`, setup-token channel test) was ever run.
- **Requirement impact:** FLT-02/FLT-03/FLT-05 spike-recording halves met; automation/live halves pending. FLT-08 written half met; owner-acceptance half pending (blocking-human checkpoint unrecorded).

### SC4 — Codd-pattern agent onboarded by the same command — PARTIAL (path proven, live gated)
- **Proven:** codd row carries the Codd shape in-schema (opencode harness, no slack, no workspace, repos hyprn-platform + hyprn-mvp); renderer excludes codd from `wake.json` (asserted: ada present, codd absent); validator encodes kind engineering + harness opencode with no third kind; `fleet add --harness opencode --dry-run` prints the first-class Codd path (GitHub App + Linux user + OpenCode + herdr) and drives the `provision.sh` opencode branch shape.
- **Not proven:** no live Codd-pattern onboarding executed (same owner-gate deferral as SC2).
- **Requirement impact:** CODD-02 schema + dry-run path halves met; live half pending.

## Automated substrate (all green, not mistaken for goal achievement)
- `tests/agents/checks/fleet.sh`: 30 PASS, exit 0, auto-discovered by `run.sh` (no harness change).
- `fleet-validate` + `fleet-render --check` + `git diff` regen-clean: all exit 0.
- No secret values in fleet scripts (shape/handles only); no `TBD/FIXME/XXX` debt markers in phase files. One cosmetic `placeholder` word in `agents/fleet:105` refers to a gateway-key name placeholder in dry-run intent text, not a stub — informational only.

## Human gates (owner actions that block SC2/SC3-live/SC4-live)
1. Assign Workspace User Management Admin role to the automation service account (Admin console).
2. Approve + execute the live trial onboardings per the runbook (GitHub App manifest, Slack install + Socket Mode token by owner hands, host provisioning) for one engineering (Codd-pattern, stops before seat invite) and one operations test agent, then the matching live removals.
3. Execute Ada's group-to-user move (or formally defer it with a date).
4. Record approval of `runbooks/agents/onboarding.md` + the deferred live-trial checklist (closes the 06-03 blocking-human checkpoint).

## Gaps (for `/gsd-plan-phase --gaps`)
1. **SC1 consumer migration + legacy deletion — CLOSED by 06-04** (re-verified above; no action).
2. **Live trial execution + recording** (SC2/SC4-live, FLT-04/06/07-live, CODD-02-live): run the owner-gated trial, keep the dated record.
3. **Workspace live state** (SC3-live, FLT-02-live): admin-role grant + Ada group-to-user move (or dated deferral); optionally run one live probe per deferred finding.
4. **Owner acceptance record** (FLT-08): one-line sign-off of the runbook + trial plan in the Record table.

## Deferred / explicitly out-of-scope (not gaps)
- Claude-seat invitation automation (no member API; engineering test stops before it by design).
- Money movement / signing (never delegated).
- Further seat agents (FLEET-01, waits on Anthropic).
