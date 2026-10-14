# Phase 6: Fleet as code and onboarding — Pattern Map

**Mapped:** 2026-10-14
**Files analyzed:** 6 (new/modified)
**Analogs found:** 6 / 6

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `agents/fleet.yaml` | config (registry) | transform (YAML → generated files) | `agents/host/agents.txt` + `agents/wake/wake.json` | exact (rows absorbed verbatim) |
| `agents/fleet-render` + `agents/fleet-validate` | utility (renderer + validator) | transform + static gate | `agents/loops/validate.py` | exact (stdlib + PyYAML gate) |
| `agents/fleet` (add/remove driver) | utility (CLI driver, bash) | request-response (sequence existing flows) | `agents/host/provision.sh:add_agent` + `agents/host/apply.sh` + `agents/host/files/bin/opencode-task` (name check) | role-match |
| `tests/agents/checks/fleet.sh` | test (check script) | batch (static assertions) | `tests/agents/checks/loops.sh` | exact |
| `runbooks/agents/onboarding.md` | doc (runbook) | request-response (procedures + checklists) | `runbooks/agents/opencode.md` + `runbooks/agents/github.md` + `runbooks/agents/slack.md` | role-match |
| spike finding records (workspace/slack-icon/setup-token) | doc (dated findings) | event-driven (probe → record) | `runbooks/agents/checks-2026-10-13.md` (dated records) + `tests/agents/run.sh` record block | role-match |

## Pattern Assignments

### `agents/fleet.yaml` (config, transform)

**Analogs:** `agents/host/agents.txt` (lines 1–5), `agents/wake/wake.json` (lines 1–6)

**Row shape to absorb** (`agents/host/agents.txt:1-5`):

```text
# name  uid    harness   github-app        app-id   installation-id  bot-user-id  display name
# One line per agent; UIDs 20000-20999 are agent users; the GitHub App is per agent (ADR-0005).
# harness: claude (Claude Code on a Claude seat, Slack channel) or opencode (OpenCode, terminal only).
ada     20001  claude    ada-agent-hyprn   5299141  170941397        341930344    Ada (AI agent)
codd    20002  opencode  codd-agent-hyprn  5306008  171119571        342187193    Codd (AI agent)
```

**Wake filter to encode** (`agents/wake/wake.json:1-6`): constants `project`/`zone`/`host` plus `agents` = Slack-harness names only (`["ada"]`; Codd excluded). Renderer rule: `[name for agents if slack]`.

**Column order is load-bearing** — reader skips comments/blanks (`agents/host/provision.sh:267`):

```bash
grep -vE '^\s*(#|$)' "$HERE/agents.txt" | while read -r name uid harness app_slug app_id installation_id bot_id display; do
  add_agent "$name" "$uid" "$harness" "$app_slug" "$app_id" "$installation_id" "$bot_id" "$display"
done
```

**Generated-file convention:** commit `agents.txt`/`wake.json`/`fleet.auto.tfvars.json` with `# GENERATED from agents/fleet.yaml — do not edit` headers; consumers (`provision.sh:267`, `tests/agents/host-checks.sh`, `agents/wake/provision.sh:15`, `infra/agents/variables.tf:51-61`) stay unchanged until migrated one at a time.

---

### `agents/fleet-render` + `agents/fleet-validate` (utility, transform + static gate)

**Analog:** `agents/loops/validate.py` (lines 1–62, full file)

**Imports pattern** (lines 10–13) — stdlib + Debian PyYAML only, no new packages:

```python
import sys
import yaml  # Third-party: PyYAML (Debian package python3-yaml).
```

**Core gate pattern** (lines 16–20, 27–47) — copy shape, swap field sets:

```python
REQUIRED = {"name", "owner", "trigger", "steps", "tools", "autonomy",
            "budget", "egress_allowlist", "runtime", "eval_set",
            "promotion_rule"}
AUTONOMY_LEVELS = {"A0", "A1", "A2", "A3"}

def validate(path):
    with open(path, encoding="utf-8") as handle:
        doc = yaml.safe_load(handle)   # safe_load, never load
    ...
    missing = REQUIRED - set(doc)
    assert not missing, "missing %s" % sorted(missing)
```

Fleet validator swaps in: `REQUIRED = {name, uid, kind, harness, display, github, slack, workspace}`; enums `kind={engineering,operations}`, `harness={claude,opencode}`; UID range 20000–20999 + uniqueness; wake-filter assertion (every wake-listed agent has `slack: true`); secret-name assertion `<name>-agent-<purpose>`, reject `agent-<name>-*`.

**CLI pattern** (lines 50–58): `usage: validate.py <file> [...]`, per-file loop, exit 1 on any failure, `log()` to stderr with `hyprn-…:` prefix. Renderer mirrors with `fleet-render --check` (regen-clean) reuse.

---

### `agents/fleet` add/remove driver (utility, request-response)

**Analogs:** `agents/host/provision.sh:174-226` (`add_agent`), `agents/host/apply.sh:1-14`, `agents/host/files/bin/opencode-task:6-9` (name validation)

**Header pattern** (copy from `apply.sh:1-4`, `provision.sh:1-4`):

```bash
#!/usr/bin/env bash
# <one-line purpose>. Idempotent; <where it runs>.
set -euo pipefail
: "${CLOUDSDK_CONFIG:?set CLOUDSDK_CONFIG to the gcloud configuration dedicated to hyprn.ai}"
```

**Name validation** (copy from `opencode-task:7-9`):

```bash
task="${1:?usage: opencode-task <task-name>}"
[[ "$task" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] && [ "$task" != hyprn-platform ] \
  || { echo "opencode-task: use lowercase letters, digits and dashes" >&2; exit 1; }
```

Fleet `add` uses the same regex for agent names (satisfies ASVS V5 input validation).

**Per-agent provisioning core** (`provision.sh:174-185` — `add` drives this, does not duplicate it):

```bash
add_agent() {
  local name="$1" uid="$2" harness="$3" app_slug="$4" app_id="$5" installation_id="$6" bot_id="$7" display="$8"
  local home="/home/$name" sub=$((100000 + (uid - 20000) * 65536))
  case "$harness" in claude|opencode) ;; *) echo "unknown harness for $name: $harness" >&2; exit 1 ;; esac
  if ! id "$name" >/dev/null 2>&1; then
    useradd --create-home --uid "$uid" --user-group --shell /bin/bash --comment "$display" "$name"
  fi
```

Codd-pattern branch (`provision.sh:221-226`) is what `--kind engineering` + `harness: opencode` must drive; the `return 0` before Claude/Slack setup is the selection point.

**Ship-and-run pattern** (`apply.sh:9-14`) — `add`/`remove` end by shipping and running checks:

```bash
cd "$(git rev-parse --show-toplevel)"
tar -czf - agents/host agents/roles agents/marketplace tests/agents |
  gcloud compute ssh "$HOST" --zone="$ZONE" --project="$PROJECT" --tunnel-through-iap --quiet --command \
    'set -e; rm -rf ~/hyprn-provision; mkdir ~/hyprn-provision; tar -C ~/hyprn-provision -xzf -;
     sudo bash ~/hyprn-provision/agents/host/provision.sh;
     sudo bash ~/hyprn-provision/tests/agents/host-checks.sh'
```

**Secrets rule (from `runbooks/agents/slack.md:14-19`):** scripts take secret *paths/handles only*, never values; values travel `pbpaste | gcloud secrets versions add … --data-file=-` in owner hands; verify by shape (`xapp-`, `xoxb-`), never print. No `--token <value>` flags; no `set -x` near handles.

**Remove precedent** (`runbooks/agents/opencode.md:54-56`): `remove` extends this contingency to all kinds — remove YAML entry → re-render → `userdel -r <name>` → App uninstall/delete → secret disable → print remaining manual steps (App deletion confirm, secret-version cleanup, Workspace user delete/suspend). Removals get their own owner go (AGENTS.md authority rule).

---

### `tests/agents/checks/fleet.sh` (test, batch)

**Analog:** `tests/agents/checks/loops.sh` (lines 1–40, full file)

**Harness pattern** (lines 1–12) — copy verbatim, swap paths:

```bash
#!/usr/bin/env bash
# Loop-registry checks (CP-05, EGR-03). Static content assertions run anywhere;
# host-executed portions run as root on the agent host.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
VALIDATOR="$REPO_ROOT/agents/loops/validate.py"
FIXTURE="$REPO_ROOT/agents/loops/testdata/test-loop.yaml"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
```

Fleet checks: `VALIDATOR` → `agents/fleet-validate`; assertions → schema-valid, UID uniqueness/range, regen-clean (`fleet-render | diff`), no-secret-value-flags (`grep -E '\-\-(token|secret|key) ' agents/fleet` must fail), wake-filter (Slack-less agent absent from `wake.json`), runbook-exists (`test -f runbooks/agents/onboarding.md`).

**Negative-probe pattern** (lines 34–38) — copy for fleet negatives (bad harness, duplicate UID, Slack-less agent in wake list):

```bash
BAD="$(mktemp)"
printf 'name: bad\nowner: o\n...' > "$BAD"
check "negative probe: bad autonomy level is rejected" "! python3 '$VALIDATOR' '$BAD'"
rm -f "$BAD"
```

**Registration:** executable `tests/agents/checks/fleet.sh` is auto-discovered by `tests/agents/run.sh:41-46` (guarded per-script loop, non-masking, dated record append at `run.sh:48-60`). No harness change needed.

---

### `runbooks/agents/onboarding.md` (doc, request-response)

**Analogs:** `runbooks/agents/opencode.md` (structure), `runbooks/agents/github.md` + `slack.md` (vendor procedure sections)

**Structure to copy** (from `opencode.md:1-65`): `# <Title>` → identity/limits table → `## Use` (commands an owner pastes) → per-kind flows with owner-checklist callouts → `## Record` dated table:

```markdown
| Date | Action | Result |
|---|---|---|
| 2026-10-13 | Codd prepared: Linux user, policy relaxed ... | App `codd-agent-hyprn` (App 5306008, ...) created by the owner ... |
```

**Content to consolidate (not duplicate):** `slack.md` §1–2 (manifest + token-load), `github.md` create/rotate (manifest flow + `gh api` discovery), `opencode.md` Codd path + `## Remove` contingency, `host.md` provision. Per RESEARCH §(6): (a) one-time prerequisites, (b) `fleet add` per kind with seat-invite stop, (c) `fleet remove` + manual-remainder table, (d) per-vendor appendix, (e) Record table. State out-of-scope (seat automation, money/signing) per REQUIREMENTS.md.

---

### Spike finding records (doc, event-driven)

**Analogs:** `runbooks/agents/checks-2026-10-13.md` (dated record precedent), `tests/agents/run.sh:48-60` (record-append block)

**Format:** short dated notes — finding template `works / doesn't / manual step + evidence lines`, ≤1 page each, appended to the onboarding runbook Record table or as `runbooks/agents/<spike>-finding-YYYY-MM-DD.md`. Time-box ~2h each (FLT-02 Workspace DWD-free `users.insert`, FLT-03 `apps.icon.set` manager-app constraint, FLT-05 `setup-token` channel behavior). A "doesn't" is a complete result that locks the manual step.

## Shared Patterns

### Authority gates (apply to `agents/fleet` add/remove)

**Source:** `AGENTS.md` authority section + `agents/host/apply.sh:3`
Every cloud/vendor create/change/delete step runs only after the platform owner's explicit go for that exact step; removals get their own go. `--dry-run` prints go-checklists with estimated action counts instead of executing. Terraform: plan, review, apply exactly the reviewed plan.

### Secrets by shape/handles (apply to `agents/fleet`, `fleet.sh`, runbook)

**Source:** `runbooks/agents/slack.md:14-19,58`
Scripts accept paths/handles, never values. Verify by shape (`xapp-`, `xoxb-`) never by printing. `fleet.sh` asserts no value-flags exist.

### Bash + stdlib toolchain (apply to all new scripts)

**Source:** `agents/host/provision.sh:4`, `tests/agents/run.sh:7`, `agents/loops/validate.py:9-13`
`set -euo pipefail` (drivers) / `set -uo pipefail` (checks); Python 3 stdlib + Debian `python3-yaml`; `gcloud`/`gh` with `CLOUDSDK_CONFIG`/`GH_CONFIG_DIR`. No new packages; a Workspace client library needs a gated install task if the spike selects one.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| *(none)* | — | — | All six new files have tracked analogs above; planner uses RESEARCH.md §Architecture Patterns for renderer schema field names (`[ASSUMED]`, planner locks them) |

## Metadata

**Analog search scope:** `agents/host/`, `agents/wake/`, `agents/loops/`, `agents/marketplace/plugins/slack/`, `tests/agents/`, `runbooks/agents/`, `infra/agents/`
**Files scanned:** ~25 (all analog paths verified via `git ls-files`, non-empty = tracked)
**Pattern extraction date:** 2026-10-14
