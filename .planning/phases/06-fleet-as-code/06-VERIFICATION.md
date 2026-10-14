---
status: gaps_found
score: 0/4
phase: 06-fleet-as-code
verified: 2026-10-14
criteria_total: 4
criteria_passed: 0
criteria_partial: 3
criteria_failed: 1
next_action: "Resolve SC1 scope mismatch (migrate provision/wake/checks off agents.txt/wake.json and delete them, or reword SC1 to generated-not-gone), then owner executes the gated live trial (Workspace admin role, vendor approvals, Ada group-to-user move)."
next_command: "/gsd-plan-phase --gaps (06-fleet-as-code: SC1 consumer migration + legacy deletion)"
gates:
  - "SC1 FAILED: agents/host/agents.txt and agents/wake/wake.json still committed and still read directly by provision.sh, wake.py, and checks; registry renders but does not replace."
  - "Live vendor approvals + owner trial not executed (by design): dry-run proof green, live onboarding/offboarding ungated work remains."
  - "06-03 Task 3 blocking-human checkpoint (owner runbook acceptance + live-trial approval) not recorded."
---

# Phase 6 Verification: Fleet as code and onboarding

**Goal (ROADMAP):** Adding or removing an engineering or operations agent is one command.
**Mode:** Read-only, goal-backward. SUMMARY claims treated as leads, not evidence.
**Checks run:** `bash tests/agents/checks/fleet.sh` (30 PASS, exit 0), `fleet-validate` (exit 0), `fleet-render --check` (exit 0), live `fleet add/remove --dry-run` probes, consumer grep traces.

## Per-criterion verdicts (ROADMAP Phase 6 SC 1-4)

### SC1 — `agents/fleet.yaml` is the only declaration; `agents.txt` and `wake.json` are gone — FAIL
- **Proven:** `agents/fleet.yaml` declares ada (20001/claude/slack true/workspace group) + codd (20002/opencode/slack false/workspace none); `fleet-render --check` exit 0; committed `agents.txt`/`wake.json` byte-identical to render (GENERATED header in agents.txt); `fleet-validate` accepts registry and rejects bad harness / duplicate UID / `agent-` legacy name / Slack-less wake entry (all exit non-zero, asserted in fleet.sh); `fleet.auto.tfvars.json` renders `agents [ada codd]` sorted + `slack_agents [ada]`.
- **Fails the letter of the SC:** both legacy files are still committed and still the files live consumers read — `agents/host/provision.sh:267` parses `agents.txt` directly, `agents/wake/wake.py:22` loads `wake.json`, `agents/wake/provision.sh:15` installs `wake.json`, and `egress.sh`/`github.sh`/`herdr.sh` checks read `agents/host/agents.txt`. Nothing in provisioning, wake, or those checks reads `fleet.yaml`. Terraform consumes the generated tfvars shape, but the host/wake path does not.
- **Why:** 06-01 PLAN explicitly scoped deletion/migration out ("Do NOT delete or stop committing the legacy files; consumers migrate later"). So the phase as planned could never satisfy SC1 as written. Resolution is a scope decision: either (a) migrate the remaining consumers to the registry and delete the two files, or (b) reword SC1 to "generated, regen-clean" instead of "gone".
- **Requirement impact:** FLT-01 partially met (single hand-edited declaration + deterministic render proven; replacement of consumers incomplete).

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
1. **SC1 consumer migration + legacy deletion** (or SC reword): migrate `provision.sh`, `wake.py`/`wake/provision.sh`, and `egress`/`github`/`herdr` checks to read the registry/generated output, then delete `agents/host/agents.txt` + `agents/wake/wake.json`.
2. **Live trial execution + recording** (SC2/SC4-live, FLT-04/06/07-live, CODD-02-live): run the owner-gated trial, keep the dated record.
3. **Workspace live state** (SC3-live, FLT-02-live): admin-role grant + Ada group-to-user move (or dated deferral); optionally run one live probe per deferred finding.
4. **Owner acceptance record** (FLT-08): one-line sign-off of the runbook + trial plan in the Record table.

## Deferred / explicitly out-of-scope (not gaps)
- Claude-seat invitation automation (no member API; engineering test stops before it by design).
- Money movement / signing (never delegated).
- Further seat agents (FLEET-01, waits on Anthropic).
