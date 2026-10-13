# Phase 1: Security baseline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-13
**Phase:** 1-Security baseline
**Areas discussed:** Team-plan-less scope, Codd repo scope, Egress observation, Checks shape

---

## Team-plan-less scope

| Option | Description | Selected |
|--------|-------------|----------|
| Defer GHE-01, prove the rest | Ruleset definition reviewed and ready; deny-rules proven as interim control; planner reshapes criterion 1 | ✓ |
| Prove readiness only | Dry-run ruleset plan without applying, plus everything else | |
| Reshape Phase 1 | Move repo-protection criteria to a later phase entirely | |

**User's choice:** Freeform — "I approve beforehand all, run autonomously" (all areas at agent discretion, no further questions)
**Notes:** Purchases deferred per owner 2026-10-13; enforcing ruleset impossible on GitHub Free. GHE-03 provable via deny rules now.

---

## Codd repo scope

| Option | Description | Selected |
|--------|-------------|----------|
| Both repos | platform + mvp (verified 2026-10-13); correct stale platform-only lines in Phase 1 | ✓ |
| Platform only | Keep merged wording; treat mvp coverage as out of scope | |
| Defer correction | Leave stale lines; planner works around them | |

**User's choice:** Freeform — "I approve beforehand all, run autonomously"
**Notes:** Commit 30ee1b1 verified App installation on both repos by branch push. mvp has no secrets/staging; host controls cover both identically.

---

## Egress observation

| Option | Description | Selected |
|--------|-------------|----------|
| Per-agent logs, no blocking | Cloud Logging per agent+destination; ada+codd+containers+wake; DNS allowed | ✓ |
| Blocking from day one | Enforce allowlist immediately (rejected: belongs to Phase 7 EGR-02) | |
| Host-aggregate only | Single log stream without per-agent attribution (rejected: criterion 4 needs per-agent) | |

**User's choice:** Freeform — "I approve beforehand all, run autonomously"
**Notes:** Observation continuous from Phase 1; enforcement stays Phase 7. Metadata-server/DNS gotcha carried from STATE.md.

---

## Checks shape

| Option | Description | Selected |
|--------|-------------|----------|
| Build on host-checks.sh | run.sh orchestrates 40 existing + new security checks; dated records to runbooks/agents/ | ✓ |
| Fresh runner | New harness ignoring host-checks.sh (rejected: discards 40 passing checks) | |
| Automate owner steps | Script break-glass/2FA/console/IAM-search (rejected: needs explicit per-step go, never automate) | |

**User's choice:** Freeform — "I approve beforehand all, run autonomously"
**Notes:** Owner-hand steps become explicit go checklists. POL-03 evidence is must-verify. agents/policy/ artifacts (managed-settings.json, allowlist) created in phase.

---

## Agent's Discretion

All four areas were decided at agent discretion under the user's beforehand approval. No area was escalated back.

## Deferred Ideas

- GHE-01 ruleset enforcement at Team-plan purchase time.
