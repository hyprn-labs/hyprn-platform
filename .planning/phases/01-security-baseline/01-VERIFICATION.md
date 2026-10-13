---
phase: 01-security-baseline
verified: 2026-10-13T22:30:00Z
status: human_needed
score: 7/7 criteria delivered as code, 0/7 proven live (all live proofs are owner/host-hand by locked decision)
success_criteria_total: 7
success_criteria_code_verified: 7
success_criteria_live_proven: 0
next_action: "Owner works the go-checklists in order (claude.md console apply, host provisioning + run.sh green, gcp.md safeguards + canary alerts, live session markers), then signs each record row"
next_command: "sudo tests/agents/run.sh (as root on the agent host, after the checklist steps it depends on)"
---

# Phase 1: Security baseline — Verification Report

**Phase goal (ROADMAP.md):** `main` is protected by GitHub, Ada runs under enforced policy,
outbound traffic is visible, misuse of secrets or IAM raises an alert, and the safety controls
are proven by one command. Codd covered by the same run.

**Locked decisions applied:** D-01 (GHE-01 enforcement deferred to the Team-plan purchase;
phase delivers a reviewed ruleset definition + deny-rule interim control — success criterion 1
is reshaped, not waived), D-03/D-04 (Codd scope is **both** repositories, superseding the
stale "platform-only" wording still in ROADMAP criterion 7), D-08 (owner-hand steps are
go-checklists, never automated — their unexecuted state is expected, not a gap).

**Method:** read-only inspection + committed check scripts only. No Terraform applies, no gcloud
mutations, no secret operations. Live suites FAIL off-host on owner-driven markers and
host-environment items — classified as expected per the phase brief, not as surprises.

## Per-criterion verdicts (against the 7 ROADMAP success criteria, as reshaped)

| # | Criterion (reshaped where locked decisions require) | Code verdict | Live verdict | Overall |
|---|-----------------------------------------------------|--------------|--------------|---------|
| 1 | Ruleset definition protects `main` with no App bypass, ready to apply at Team-plan time; deny rules are the interim control (D-01 reshape) | ✓ VERIFIED — `agents/github/main-ruleset.json` parses, enforcement `active`, 4 rules (non_fast_forward, deletion, required_linear_history, pull_request with 1 approval + stale dismissal + code-owner + last-push), `bypass_actors` length 0; `CODEOWNERS` catch-all `@hyprn-labs/owners` with apply-time team caveat; `checks/github.sh` 16 static checks PASS; negative no-apply grep present, zero apply calls repo-wide | ⏳ PENDING OWNER — Team-plan purchase + `gh api rulesets --input` apply + live App-refusal run on host (`sudo tests/agents/checks/github.sh`; 4 live checks FAIL environmentally here, as designed) | CODE DONE, EXECUTION PENDING |
| 2 | Admin console policy matches `agents/policy/managed-settings.json`; routine work runs without prompts | ✓ VERIFIED — policy file parses, 10 deny entries (merge, 5+ push-to-main spellings, `-C` form, admin-merge, branch-protection API), ask/allow split with no deny overlap, managed-only locks, marketplace pin `hyprn-labs/hyprn-agents`, sandbox allowlist (4 seeds + managed-domains-only), min-version 2.1.282; `checks/policy.sh` 17/17 PASS standalone; `runbooks/agents/claude.md` console path + verbatim-paste + diff-match + POL-03 3-part evidence + dated pending row | ⏳ PENDING OWNER — console apply, prompt-free routine-work confirm, POL-03 evidence, signed row in `claude.md` | CODE DONE, EXECUTION PENDING |
| 3 | Slack approvals work owner-only; others ignored; merge/push-to-main/force-push/bypass refused | ✓ VERIFIED — `tests/agents/checks/session.sh` (bash -n clean, 9 named checks → 13 executions: relay-yes/no/non-owner, allowlist-silence, 4 refusal families × 2 repos with command-text variants in `runbooks/agents/live/README.md`); live steps recorded as `runbooks/agents/live/<test-id>.ok` markers, missing marker = FAIL, nothing simulated | ⏳ PENDING OWNER — owner drives Ada-session + Codd refusal/relay tests per `live/README.md`, writes markers, then `sudo tests/agents/checks/session.sh` must pass on host | CODE DONE, EXECUTION PENDING |
| 4 | Egress proxy logs each agent's destinations; direct outbound dropped | ✓ VERIFIED — `agents/host/files/egress.nft`: metadata block + DNS :53 first (lines 22-23 precede drops at 30-31), proxy accepts 3128/3129, 80/443 drops for login range 20000-20999 AND subuid union 100000-231071, wake-placement finding in header (wake is on `hyprn-agents-wake-01`, never crosses this host — scope correctly not extended); `squid-hyprn.conf`: per-agent ports 3128/3129 + ACLs + `%lp` agent-identifier log, no blocking (observe mode); `checks/egress.sh` 16 checks incl. container-originated drop/proxy pair | ⏳ PENDING HOST/OWNER — `nft --check` never ran (no binary here); Squid install + proxy-env delivery + user/container drop tests + Cloud Logging flow query all need root on host (`sudo tests/agents/checks/egress.sh`); ops-agent-vs-syslog shipper unconfirmed, documented as provisioning-time decision | CODE DONE, EXECUTION PENDING |
| 5 | Canary secret read + canary IAM change each email `gcp-admins` | ✓ VERIFIED — `infra/agents/detect.tf`: DATA_READ audit config for Secret Manager, admins-group email channel, unexpected-access alert (host/wake exclusions; controller/gateway exclusions explicitly deferred to Phases 3-5, never silent), IAM-change alert over project, folder-sink into project; zero secret values (references only, confirmed by read); `checks/detect.sh` 7/7 static PASS, 5 live checks FAIL without owner credentials (expected) | ⏳ PENDING OWNER — reviewed-plan `terraform plan/apply`, break-glass confirm, member-notice-then-2FA (one-way gate), both canary tests with mail arrival, org-wide IAM search; six pending sign-off rows in `runbooks/agents/gcp.md` | CODE DONE, EXECUTION PENDING |
| 6 | `tests/agents/run.sh` passes and writes a dated record | ✓ VERIFIED — `run.sh` (bash -n clean): runs `host-checks.sh` unchanged first, globs every executable `checks/*.sh` with per-script failure capture (scratch-stub aggregation proven in 01-01), dated record with ISO date + checkout hash + per-script outcomes; all 8 scripts bash -n clean; check counts 9–18 per script | ⏳ PENDING HOST — full green requires root on host; off-host trial runs FAIL environmentally. **Working-tree note:** an off-host trial appended FAIL rows to `runbooks/agents/checks-2026-10-13.md` (uncommitted, 22:13Z) — revert before the host run so the dated host record stays clean (same treatment as 01-05) | CODE DONE, EXECUTION PENDING |
| 7 | Codd scope proven by the same run (both repos per D-03, superseding stale criterion text) | ✓ VERIFIED — `checks/codd.sh` 14 checks (per-repo install = exactly 2 repos, token freshness <60min, private home + cross-read negative, managed opencode.json root-owned with deny families + reviewed-copy match, no Slack/Workspace presence); `host-checks.sh` stale single-repo assertion fixed to both-repo form; stale-line sweep: REQUIREMENTS/spec/README/PROJECT.md/runbook all state both-repo; remaining `platform.*only` matches are legitimate non-Codd lines (OPS-03 Boole scope, Slack-allowlist "platform owner only"); ADR-0003 exists (DOC-01) | ⏳ PENDING HOST — per-repo live assertions need App-token `gh` as agent users on host (`sudo tests/agents/checks/codd.sh`) | CODE DONE, EXECUTION PENDING |

## Must-haves roll-up (23 plan truths)

- 01-01 (4/4 code-verified): ruleset readable + ready; run.sh aggregates + exits non-zero; dated record; both-repo assertions.
- 01-02 (4/4 code-verified): deny-first variants; sandbox + marketplace pin + 3-way evidence wiring (console leg by design deferred); owner checklist; policy.sh coverage.
- 01-03 (3/4 code-verified, 1 live-pending): proxy-only + DNS; per-agent logs no blocking; egress.sh coverage; **live user+container drop proof pending host** (human item H-4).
- 01-04 (5/5 code-verified, live-pending by design): audit config + alerts + sink in reviewed TF; host/wake/IAM-search checks; six owner checklists (human items H-5/H-6).
- 01-05 (4/6 code-verified, 2 live-pending): session.sh + codd.sh + stale-line sweep + ADR-0003 verified; **live session proofs** (human item H-3) and **final green host run + sign-off** (human item H-7) pending.

No artifact is MISSING or STUB. No key link is unwired (run.sh glob picks up all 7 domain
scripts with no orchestrator edit; deny entries ↔ refusal tests; audit config ↔ alert queries;
sink → project alert path). No blocker anti-patterns (no TBD/FIXME/placeholder in phase files;
no secret values; no automated owner-step; no ruleset apply call).

## Human verification required (all expected owner/host-hand executions)

### H-1. Console policy apply (criterion 2)
**Test:** Team Owner pastes `agents/policy/managed-settings.json` verbatim on the Claude admin
console Policy page, diffs console export vs file, confirms routine worktree work runs without prompts,
records POL-03 3-part evidence. **Expected:** diff empty, no routine-work prompts, signed row in
`runbooks/agents/claude.md`. **Why human:** console access + org authority; must never be scripted (D-08).

### H-2. Team-plan purchase + ruleset apply (criterion 1)
**Test:** After purchase, owner applies `agents/github/main-ruleset.json` to both repositories via
`gh api .../rulesets --input`, confirms the `@hyprn-labs/owners` team name. **Expected:** GitHub
refuses App merge/push to `main`. **Why human:** paid-plan purchase + org-admin credentials (D-01).

### H-3. Live session proofs (criterion 3)
**Test:** Owner drives relay/allowlist/refusal tests per `runbooks/agents/live/README.md`, writes
`runbooks/agents/live/<test-id>.ok` markers (13 tests: relay trio, allowlist-silence, 4 refusals ×
2 repos, Ada session + Codd), then `sudo tests/agents/checks/session.sh` on host. **Expected:** all
13 PASS, captured in the dated record. **Why human:** live Slack participation cannot be simulated.

### H-4. Host provisioning + egress live proof (criterion 4)
**Test:** Owner-go `apt-get install -y squid`, render `squid-hyprn.conf` + `egress.nft`
(`nft --check` first, then `systemctl restart hyprn-agents-egress`), confirm log shipper
(ops-agent vs syslog fallback), run `sudo tests/agents/checks/egress.sh` incl. container-originated
drop test + Cloud Logging flow query. **Expected:** direct dropped (user + container), DNS + proxy
work, per-agent destinations queryable. **Why human:** root on host + host change authority.

### H-5/H-6. Detection apply + safeguards + canary alerts (criterion 5)
**Test:** Owner reviews exact `detect.tf` revision → `terraform plan/apply` → break-glass confirm →
member notice THEN 2FA toggle → canary secret read + mail arrival → canary IAM change + mail arrival
→ org-wide IAM search matching declared roles; sign all six rows in `runbooks/agents/gcp.md`.
**Expected:** both emails received at `gcp-admins@hyprn.ai`, IAM output matches. **Why human:**
owner credentials + console + irreversible-ish 2FA gate (D-08).

### H-7. Final green host run + sign-off (criteria 6/7)
**Test:** After H-1–H-6 markers exist, `sudo tests/agents/run.sh` on host; keep dated record; sign
criteria 3/6/7. **Expected:** every domain PASS. **Why human:** requires the host + all prior gos.
**Pre-step:** `git checkout -- runbooks/agents/checks-2026-10-13.md` to drop the off-host trial rows.

## Gaps

None. Every code deliverable promised for this phase (given D-01 deferral and D-08 no-automation
rule) exists, is substantive, and is wired. The only unproven items are the owner/host executions
above, which the plans explicitly gated as blocking-human checkpoints — they are human_needed,
not gaps_found.

## Deferred (not gaps — scheduled or purchase-gated by locked decision)

| Item | Addressed in | Evidence |
|------|-------------|----------|
| GHE-01 ruleset enforcement (apply) | Team-plan purchase (owner decision 2026-10-13) | D-01; CONTEXT "reviewed ruleset definition ready to apply" |
| EGR-02 allowlist enforcement | Phase 7 | `egress-allowlist.txt` M3-enforcement header; ROADMAP Phase 7 SC-1 |
| Controller/gateway alert exclusions | Phases 3–5 (identities do not exist yet) | `detect.tf` comment; 01-04 summary deviation |
| Wake-side egress observation | Follow-up (wake is a separate VM) | `egress.nft` header finding; 01-03 summary deviation |

_Verified: 2026-10-13T22:30:00Z_
_Verifier: gsd-verifier (Phase 1 security baseline)_
