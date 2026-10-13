# 01-02 Summary: enforced agent policy (reviewed file + checks + owner checklist)

**Status:** done-with-blockers (1 owner console-apply checkpoint)
**Date:** 2026-10-13

## Tasks done

1. **Author the managed policy file and placeholder allowlist** — created
   `agents/policy/managed-settings.json` (10 deny entries: merge, 5+
   push-to-main spellings incl. refspec/plus-sign/force variants, `-C`
   directory form, admin-merge and branch-protection API paths; ask for
   read-only `gh api`; 7 routine-work allows with no deny overlap;
   managed-only locks, marketplace pin to `hyprn-labs/hyprn-agents`,
   sandbox network allowlist seeded with 4 hosts + managed-domains-only,
   minimum-version floor 2.1.282) and `agents/policy/egress-allowlist.txt`
   (M3-enforcement header per D-02, 4 seed hosts).
2. **Add the policy check script including marketplace evidence** — created
   `tests/agents/checks/policy.sh` (17 named checks: validity, deny
   families, locks, marketplace pin, sandbox posture, allowlist content,
   allow/deny non-overlap, POL-03 console-deferral wiring). Host-executed
   portions run as root on the agent host; the script runs standalone.
3. **Checkpoint: owner applies the policy in the admin console** — created
   `runbooks/agents/claude.md` (console path, verbatim-paste instruction,
   diff-match expectation, POL-03 three-part evidence, dated record table
   with a pending-sign-off row). **Not automatable — owner go required.**

## Verify results

- `POLICY_STATIC_OK` (parses, ≥8 denies, allowlist has domain lines)
- `POLICY_CHECKS_OK` (bash -n clean, ≥5 named checks)
- `checks/policy.sh` standalone: **17/17 PASS**, exit 0
- `CLAUDE_RECORD_OK` (runbook exists with dated row)

## Deviations

None — plan executed as written. Note: the plan's `<verify>` for task 1
requires only one allowlist domain line; the file carries four seed hosts
per the acceptance criteria (≥3).

## Blocked

1. **Owner applies `agents/policy/managed-settings.json` in the Claude
   admin console and records it (plan checkpoint, gate blocking-human).**
   Steps: console Policy page → paste file verbatim → `diff`
   console-export vs file shows no differences → confirm routine worktree
   work runs without prompts (roadmap criterion 2) → record POL-03
   three-part evidence → sign the dated row in `runbooks/agents/claude.md`.
   Who: Team Owner (console access + organization authority). This worktree
   cannot perform it: no console access, and per D-08/AGENTS.md it must
   never be scripted. Console apply is reversible (re-paste restores).
