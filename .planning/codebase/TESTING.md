---
last_mapped_commit: a393bda2510b521148d626a02e4a5aef58dae1d6
last_mapped_at: 2026-10-13
---

# Testing Patterns

**Analysis Date:** 2026-10-13

## Test Framework

**Runner:**
- Bash assertions executed on the live host — no Jest, Vitest, pytest, Go test, or TFLint config exists in the repo (verified: no `package.json`, `pyproject.toml`, `*_test.py`, `*.test.*`, `.github/`, `tflint*`, or `Makefile*`).
- The executable suite is `tests/agents/host-checks.sh` (Bash, `set -uo pipefail`, run as root). ADR Confirmation sections (`docs/adr/0001-agent-fleet.md`, `docs/adr/0005-agent-github-app.md`) define what must be checked; runbook Record tables (`runbooks/agents/host.md`, `runbooks/agents/gcp.md`, `runbooks/agents/opencode.md`) record the pass counts as test evidence.
- Config: none — thresholds and expectations live inline in the script and the ADRs.

**Assertion Library:**
- One local helper, no library:
```bash
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
# ...
exit $fail
```
(`tests/agents/host-checks.sh:7-8`, `:49`). Every assertion prints `PASS <label>` / `FAIL <label>`; any failure sets the exit code non-zero without aborting the run.

**Run Commands:**
```bash
sudo bash tests/agents/host-checks.sh          # Run the suite on the host as root
agents/host/apply.sh                           # Ship provisioning + run provision.sh + host checks (workstation, needs CLOUDSDK_CONFIG)
gcloud compute ssh hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap  # Reach the host first
```
- `agents/host/apply.sh` tars `agents/host agents/roles agents/marketplace tests/agents`, ships them over IAP, then runs `provision.sh` followed by `host-checks.sh` on the host — so every provisioning change is immediately tested (`agents/host/apply.sh:9-14`).
- There is no watch mode and no coverage command. The closest equivalent is re-running `agents/host/apply.sh` after each change (see `runbooks/agents/host.md` B3: first run failed on DNS/metadata, second run passed all checks).

## Test File Organization

**Location:**
- Single suite, co-located with its docs: `tests/agents/host-checks.sh` plus `tests/agents/README.md` (one-paragraph scope) and `tests/README.md` (one-line scope for the whole `tests/` tree: "Schema, render, policy, IAM and lifecycle tests: golden fixtures prove stable rendering, unsafe fixtures must fail").
- Planned but not yet present: `contracts/v1/` golden and negative fixtures ("with golden and negative fixtures" in `contracts/v1/README.md`), schema/render/policy/IAM/lifecycle checks named in `tests/README.md`, and the host renderer/reconciler under `host/` (currently a README only).

**Naming:**
- `host-checks.sh` — `<target>-checks.sh`. Future suites should follow `<area>-checks.sh` under `tests/` (e.g. `tests/render-checks.sh`, `tests/policy-checks.sh`).

**Structure:**
```
tests/
├── README.md            # Scope: schema, render, policy, IAM, lifecycle; golden vs unsafe fixtures
└── agents/
    ├── README.md        # Scope of the host suite (one paragraph enumerating every check)
    └── host-checks.sh   # The suite; runs as root on hyprn-agents-host-01
```

## Test Structure

**Suite Organization:**
```bash
#!/usr/bin/env bash
# Isolation checks on the agent host (ADR-0001 confirmation). Run as root on
# the host; exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AGENTS="$HERE/../../agents/host/agents.txt"
fail=0
check() { ... }

# 1. Host-level control checks (run once as root)
check "root reaches metadata (control)" "curl -sf -m 5 -H Metadata-Flavor:Google $md"
check "no rootful Docker daemon" "! systemctl is-active --quiet docker.service"
# ...

# 2. Per-agent loop over the agents.txt fixture
while read -r name uid harness _; do
  run() { runuser -l "$name" -c "$1" </dev/null; }
  check "$name: home is private" "[ \"\$(stat -c %a /home/$name)\" = 700 ]"
  # ...
done < <(grep -vE '^\s*(#|$)' "$AGENTS")

exit $fail
```
(`tests/agents/host-checks.sh`.) Pattern: header comment citing the ADR → strict mode minus `-e` → `HERE`/`AGENTS` fixture paths → host-level controls → per-agent loop → `exit $fail`.

**Patterns:**
- Setup pattern: none — the suite assumes `agents/host/provision.sh` just ran (via `agents/host/apply.sh`) and asserts the resulting state. The `root reaches metadata (control)` check is the positive control proving the negative per-agent metadata checks are meaningful (`tests/agents/host-checks.sh:12` vs `:27`).
- Teardown pattern: none — checks are read-only (`curl`, `stat`, `id`, `systemctl is-active`, `gh api`, `find -mmin`); nothing is created or mutated.
- Assertion pattern: `check "<agent-or-host>: <property>" "<predicate>"` where the predicate is a shell expression evaluated by `eval`, often negated with `!` for must-not-hold properties (`! id -nG $name | grep -qwE 'sudo|docker|adm'`, `! grep -rlsq '"private_key"' /home /root /etc`).

## Mocking

**Framework:** none — and deliberately so. Every check runs against the real host, real VM identity, real Secret Manager-backed files, and real GitHub App tokens.

**Patterns:**
- Privilege separation via `runuser`: `run() { runuser -l "$name" -c "$1" </dev/null; }` re-executes the predicate as the agent user, proving the boundary from the restricted side (`tests/agents/host-checks.sh:22`).
- Harness branching: `if [ "$harness" = claude ]` asserts Claude Code + Slack plugin and OpenCode refusal; else asserts OpenCode runs and no Slack tokens exist (`tests/agents/host-checks.sh:29-37`).
- Cross-agent isolation loop: for each agent, assert no readability of every other home (`for other in /home/*; ... check "$name: cannot read $other" "! run 'ls $other'"` at `:43-46`).

**What to Mock:**
- Nothing in the current suite. When the planned golden/negative fixture tests arrive (`contracts/v1/README.md`, `tests/README.md`), unsafe fixtures must fail rendering/apply without touching cloud state — i.e. fixture files, not live resources.

**What NOT to Mock:**
- Metadata-server reachability, file ownership/modes (`stat -c %U:%a` pinned to `root:644` / `$name:400` / `700`), systemd state, Docker rootless mode, token freshness, GitHub API reach, and absence of key material — all asserted live (`tests/agents/host-checks.sh:12-42`).

## Fixtures and Factories

**Test Data:**
- `agents/host/agents.txt` is the agent fixture: `name uid harness app_slug app_id installation_id bot_id display` per line; comments/`#` and blanks skipped via `grep -vE '^\s*(#|$)'` (`tests/agents/host-checks.sh:47`, documented in `agents/host/README.md`).
- `OPENCODE_VERSION` is parsed out of the system under test so the test can never drift from it:
```bash
OPENCODE_VERSION="$(sed -n 's/^OPENCODE_VERSION="\(.*\)"/\1/p' "$HERE/../../agents/host/provision.sh")"
```
(`tests/agents/host-checks.sh:9`.)
- Planned: golden fixtures (must render stably) and unsafe fixtures (must fail) for contracts/schemas (`tests/README.md`, `contracts/v1/README.md`) — not yet present in the tree.

**Location:**
- Live fixtures: `agents/host/agents.txt` (agents), `/run/hyprn-agents/` tmpfs files (secrets/allowlist), `/etc/hyprn-agents/` (harness/config). Planned static fixtures will live beside their schemas (`contracts/v1/`, `policies/`).

## Coverage

**Requirements:** none enforced by tooling. Coverage is social: each ADR's Confirmation section lists the checks that must exist, and each runbook Record row reports the pass count.

**Observed counts (from runbook records):**
- B3 first provisioning: DNS/metadata failure found by the suite, fixed, second run all 13 checks pass (`runbooks/agents/host.md`).
- OpenCode 1.19.0 install: 26 pass (`runbooks/agents/opencode.md` 2026-10-13).
- Codd onboarding: 40 pass (`runbooks/agents/opencode.md` 2026-10-13).

**View Coverage:**
```bash
sudo bash tests/agents/host-checks.sh | tee /tmp/host-checks.log; grep -c '^PASS' /tmp/host-checks.log
```
(No built-in summary — count `PASS`/`FAIL` lines.)

## Test Types

**Unit Tests:**
- Not used as a category. The smallest units (shell predicates, Python helpers) are exercised only through the live host suite. Do not add a unit framework; extend `host-checks.sh` following the `check "<who>: <property>"` pattern.

**Integration Tests:**
- The host suite IS the integration test: provisioning output × VM identity × Secret Manager files × systemd × GitHub API, asserted end-to-end on the real host. Add per-agent assertions inside the `while read` loop and host-wide assertions above it (`tests/agents/host-checks.sh:12-20` vs `:21-47`).

**E2E Tests:**
- Manual, recorded in runbooks rather than scripts: Slack wake round-trip (DM → wake reply → host start → agent answer, ~50 s per `agents/wake/README.md`), Ada sign-in + session resume after reboot (`runbooks/agents/host.md` B4/B5), draft-PR authorship by the App bot (`docs/adr/0005-agent-github-app.md` Confirmation), non-allowlisted sender ignored (`docs/adr/0001-agent-fleet.md` Confirmation). To automate an E2E check, add its terminal assertion to `host-checks.sh` (e.g. token freshness, `gh` reachability) rather than scripting Slack itself.

**Planned (from `tests/README.md` + specs, not yet implemented):**
- Schema/render tests with golden + unsafe fixtures (`contracts/v1/`, `policies/`); IAM negative tests (org-wide search proving `hyprn-agents` principals hold no role outside the project — currently a manual step in `docs/adr/0001-agent-fleet.md` Confirmation and `runbooks/agents/gcp.md` A2 removals); lifecycle tests for the host reconciler (`host/`, `docs/specs/cloud-platform.md` section 9).

## Common Patterns

**Async Testing (timers, background refresh):**
```bash
check "idle-stop timer active" "systemctl is-active --quiet hyprn-idle-stop.timer"
check "$name: GitHub App token fresh (under 35 minutes)" "find /run/hyprn-agents/secrets/$name/github-token -mmin -35 | grep -q ."
```
- Assert the timer is active AND the artifact is fresh — the 30-minute broker interval vs 35-minute freshness bound proves the loop is running, not just enabled (`tests/agents/host-checks.sh:15`, `:41`; broker in `agents/host/README.md`).

**Error Testing (negative assertions):**
```bash
check "$name: metadata unreachable" "! run 'curl -sf -m 5 -H Metadata-Flavor:Google $md'"
check "no service-account key files on host" "! grep -rlsq '\"private_key\"' /home /root /etc"
check "$name: no sudo or docker group" "! id -nG $name | grep -qwE 'sudo|docker|adm'"
```
- Every privilege boundary is a negated predicate, always paired with its positive control (`root reaches metadata (control)` proves the test could reach the server at all). Short timeouts (`-m 5`, `-m 10`) keep negative network checks fast.

**Ownership/mode assertions:**
```bash
check "OpenCode policy root-owned, opencode provider only" "[ \"\$(stat -c %U:%a /etc/opencode/opencode.json)\" = root:644 ] && jq -e '.enabled_providers == [\"opencode\"]' /etc/opencode/opencode.json"
```
- Combine `stat -c %U:%a` (owner:mode) with a content assertion (`jq -e`) in one `check` so ownership and shape cannot drift independently (`tests/agents/host-checks.sh:18`, `:38-39`).

---

*Testing analysis: 2026-10-13*
