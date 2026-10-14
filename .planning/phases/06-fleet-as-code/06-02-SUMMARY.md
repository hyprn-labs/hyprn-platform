# 06-02 Summary: fleet add/remove drivers

**Status:** done
**Plan:** 06-fleet-as-code / 02 (wave 2, depends on 06-01)

## What was built

- `agents/fleet` (bash, executable): `add <name> --kind engineering|operations
  [--harness claude|opencode] [--dry-run] [--owner-go]` and
  `remove <name> [--dry-run] [--owner-go]`.
  - add validates the name (opencode-task regex, no `agent-` prefix), allocates
    the next free UID in 20000-20999, validates a provisional registry entry,
    renders to temp and shows the diff, prints the Terraform delta intent and a
    numbered 8-action owner checklist; engineering output states the stop before
    the Claude seat invite; harness opencode prints the Codd-pattern path
    (GitHub App + Linux user + OpenCode + herdr); operations prints the gateway
    key path. `--dry-run` executes nothing and changes no files.
  - remove `--dry-run` prints the manual-remainder table (App deletion confirm,
    secret-version cleanup, Workspace delete/suspend, group-to-user notes,
    userdel + destroy-scope) and touches nothing, even for fixture names.
  - Fail-closed: non-dry-run without `--owner-go` refuses (add and remove);
    CLOUDSDK_CONFIG is required for real runs only, so dry-runs stay static.
  - Handles-only secrets throughout; fleet.sh asserts no value-taking flags.
- `agents/fleet-render`: added `--agents-out/--wake-out/--tfvars-out` overrides
  so dry-runs can render provisional registries to temp (needed by this task).
- `tests/agents/checks/fleet.sh`: 14 new CLI assertions (dry-runs per kind exit
  0, checklist/seat-stop/Codd-path/remainder markers, tree-unmodified via
  before/after snapshot, no-value-flags over agents/fleet) plus timed EVIDENCE
  lines per kind (0s dry-run, 8 owner actions — inside the 15-min/~8-action
  budget; live vendor approvals stay owner gates).

## Verifies

- `agents/fleet add test-eng --kind engineering --harness opencode --dry-run`
  → exit 0, checklist + seat-stop + Codd-path lines.
- `agents/fleet add test-ops --kind operations --dry-run` → exit 0, 8 actions.
- `agents/fleet remove test-eng --dry-run` → exit 0, remainder table, tree clean.
- Fail-closed probes: add/remove without `--dry-run`/`--owner-go` refuse (exit 1);
  bad agent name refused (exit 1).
- `bash tests/agents/checks/fleet.sh` → 29 PASS, exit 0.

## Deviations

- `agents/fleet-render` gained `--*-out` overrides (same commit, needed so
  dry-run can render provisional entries without touching the tree).
  [Rule 3 - blocking need of this task]
- CLOUDSDK_CONFIG guard enforced for real runs only, not `--dry-run`, so checks
  stay static and local per the plan's own under-60s/no-SSH constraint.
  [Rule 2 - correctness]
- Fixed-width agents.txt columns merge for long fixture names (e.g.
  `test-eng-agent-hyprn` overflows the 18-wide app column in temp diffs only);
  real agent names follow the short convention (ada/codd/boole). Known
  limitation, dry-run display only, never committed.

## Blocked

None (live vendor approvals are owner gates by design; dry-run proof is the
phase artifact per 06-CONTEXT.md).
