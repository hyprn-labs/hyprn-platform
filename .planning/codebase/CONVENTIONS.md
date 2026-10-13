---
last_mapped_commit: a393bda2510b521148d626a02e4a5aef58dae1d6
last_mapped_at: 2026-10-13
---

# Coding Conventions

**Analysis Date:** 2026-10-13

## Naming Patterns

**Cloud resources — role-named, never person-named:**
- Physical names follow `hyprn-<environment>-<role>[-<instance>]` per `conventions/README.md`. Examples: `hyprn-agents-host-01` in `infra/agents/host.tf`, `hyprn-agents-wake-01` in `infra/agents/wake.tf`, VPC `hyprn-agents-vpc` in `infra/agents/network.tf`, buckets `hyprn-bootstrap-tfstate` / `hyprn-agents-tfstate` in `bootstrap/bootstrap_project.tf` and `bootstrap/agents.tf`.
- Company namespace is `hyprn`; first product codename is `hyprn-mvp`; environments are `local`, `staging`, `prod`; workload components are `app`, `modeling`, `execution`, `worker` (`conventions/README.md`).
- Never put a person's name, a partner, or a phase number in durable identities (`conventions/README.md`).
- Agent first names (Ada, Codd, Boole) appear in per-agent identities only — never in cloud resources, which stay role-named (`conventions/README.md`, `docs/adr/0001-agent-fleet.md` section 2).

**Agent identity table (the one sanctioned exception):**
- Google Workspace user `<name>@agents.hyprn.ai`, display name `<Name> (AI agent)`, GitHub App `<name>-agent-hyprn` (bot `<app>[bot]`), Linux user `<name>`, secrets `<name>-agent-<purpose>`, branches `agent/<name>/<slug>` — all per `conventions/README.md`. Concrete values in `agents/host/agents.txt`, `infra/agents/variables.tf` (`agents`, `slack_agents`), `infra/agents/secrets.tf`.

**Terraform resource/variable naming:**
- Use short singular resource labels matching the thing: `google_project.bootstrap` in `bootstrap/bootstrap_project.tf`, `google_compute_instance.host` in `infra/agents/host.tf`, `google_compute_network.agents` in `infra/agents/network.tf`, `google_service_account.host` in `infra/agents/iam.tf`.
- Use snake_case variables with a `description` on every variable. Every variable in `bootstrap/variables.tf` and `infra/agents/variables.tf` carries one (e.g. `host_image`: "Pinned Debian 12 image; updated by a reviewed change, never by family lookup").
- Use `component` + `managed_by = "terraform"` labels on every labelled resource (`bootstrap/bootstrap_project.tf`, `bootstrap/agents.tf`, `infra/agents/host.tf`); add `role` (`role = "host"` in `infra/agents/host.tf`) and `agent = each.value` on per-agent secrets (`infra/agents/secrets.tf`).
- Prefix per-agent secrets `<name>-agent-...` (`ada-agent-github-app-key`, shared `agents-slack-allowed-users`) — see `infra/agents/README.md` and `infra/agents/secrets.tf`.

**Files:**
- Lowercase hyphenated: `host-checks.sh`, `provision.sh`, `apply.sh`, `wake.py`, `server.py`, `opencode.json`, `wake.json`, `egress.nft`.
- Systemd units follow the service name: `hyprn-agent@.service`, `hyprn-agent-github-token@.{service,timer}`, `hyprn-idle-stop.{service,timer}` in `agents/host/files/`.
- Terraform files are one concern per file: `versions.tf`, `providers.tf`, `variables.tf`, `outputs.tf`, plus one file per resource group (`host.tf`, `network.tf`, `iam.tf`, `secrets.tf`, `wake.tf` in `infra/agents/`; `bootstrap_project.tf`, `org_policies.tf`, `agents.tf` in `bootstrap/`).
- Every directory has a `README.md` whose first line is `# <path-from-root>` (e.g. `# agents/host` in `agents/host/README.md`, `# infra/agents` in `infra/agents/README.md`). The README states what the directory is and links to spec/ADR sections — never process history or gotchas (those belong in `AGENTS.md` and runbooks per `AGENTS.md` "Writing").

**Functions:**
- Bash: snake_case verbs — `install_base`, `install_host_files`, `install_opencode`, `add_agent`, `as_agent`, `check`, `fail` counter in `agents/host/provision.sh` and `tests/agents/host-checks.sh`; `log() { printf '== %s\n' "$*"; }` in `agents/host/provision.sh`.
- Python: snake_case — `gcp_token`, `slack`, `secret`, `connect`, `disconnect`, `on_envelope` in `agents/wake/wake.py`; `read_env`, `slack_api`, `send`, `notify`, `permission_request`, `_on_event`, `_deliver`, `_catch_up_once` in `agents/marketplace/plugins/slack/server.py`.
- Python classes are CapWords with one class per service: `Waker` in `agents/wake/wake.py`, `SlackChannel` in `agents/marketplace/plugins/slack/server.py`.

**Variables:**
- Bash: UPPER_SNAKE for constants (`OPENCODE_VERSION`, `OPENCODE_SHA256`, `DOCKER_KEY_FPR`, `GH_KEY_FPRS`, `CLAUDE_CODE_VERSION` in `agents/host/provision.sh`; `STOPPED`, `POLL_SECONDS`, `INSTANCE`, `MD`, `CONFIG` in `agents/wake/wake.py`); local lowercase (`name`, `uid`, `harness`, `home`, `sub` in `add_agent`).
- Terraform: snake_case inputs (`org_id`, `billing_account`, `host_machine_type`, `slack_agents`), `each.key`/`each.value` in `for_each` (`infra/agents/secrets.tf`, `bootstrap/bootstrap_project.tf`).
- Python module constants are UPPER_SNAKE (`CONFIG`, `MD`, `INSTANCE`, `STOPPED`, `POLL_SECONDS`, `PROTOCOL_VERSION`, `VERDICT`, `CATCH_UP_SECONDS`, `CATCH_UP_DELAYS`, `INSTRUCTIONS`, `REPLY_TOOL`).

**Types:**
- Terraform variable types are always declared: `type = string` / `number` / `list(string)` in `bootstrap/variables.tf` and `infra/agents/variables.tf`.
- Python uses no annotations; the contract is the module docstring plus `CONFIG` keys (`project`, `zone`, `host`, `agents` in `agents/wake/wake.json`).

## Code Style

**Formatting:**
- Terraform: canonical `terraform fmt` layout — 2-space indent, `key = value` alignment inside blocks, one block per resource. No lint config file exists in the repo; `terraform plan` showing no changes after apply is the style gate (recorded in `runbooks/agents/gcp.md`, `runbooks/agents/host.md`).
- Bash: no formatter config; follow the file-local style — `set -euo pipefail`, 2-space indent, `snake_case` functions. Quote every expansion (`"$name"`, `"${CLOUDSDK_CONFIG:?message}"`).
- Python: stdlib-only style, 4-space indent, double quotes, ~100-col lines. No `pyproject.toml`, `ruff.toml`, or `setup.cfg` exists; the constraint is "Python 3 standard library and Debian's python3-websocket" stated in the module docstrings of `agents/wake/wake.py` and `agents/marketplace/plugins/slack/server.py`.
- Markdown: ATX headings, pipe tables, fenced `bash` blocks. Folder READMEs start with `# <dir>` and a one-sentence definition; ADRs use MADR 4 (see below).

**Linting:**
- No ESLint/Prettier/Biome/Ruff/TFLint configs exist (verified: no `.eslintrc*`, `eslint.config.*`, `.prettierrc*`, `biome.json*`, `pyproject.toml`, `ruff.toml`, `tflint*`, `Makefile*`, `.github/` in repo root).
- Enforcement is by construction instead: signing-key fingerprint checks in `agents/host/provision.sh` (`DOCKER_KEY_FPR`, `GH_KEY_FPRS`), `sha256sum -c` on the OpenCode tarball (`agents/host/provision.sh:97`), `jq -e` shape assertions on fetched secrets (`agents/host/files/hyprn-agent-secrets`), and the host checks in `tests/agents/host-checks.sh`.

**MADR decision records (`docs/adr/`):**
- Front matter on every ADR: `status:`, `date:`, `decision-makers: Owner` (e.g. `docs/adr/0001-agent-fleet.md`, `docs/adr/0005-agent-github-app.md`).
- Required sections in order: Context and Problem Statement, Decision Drivers, Considered Options, Decision Outcome, Consequences, Confirmation, Pros and Cons of the Options, More Information. Follow `docs/adr/0001-agent-fleet.md` as the exemplar.
- An accepted record is superseded by a new one, never edited (`AGENTS.md`); statuses used: `accepted`, `proposed`, `Superseded by 0005` (see `docs/adr/README.md` table).
- Cross-repo rule: decisions spanning product and platform live in `hyprn-mvp/docs/adr/`, linked from `docs/adr/README.md` (`AGENTS.md`).

**Documentation placement (from `AGENTS.md` "Writing"):**
- READMEs state what things are and what they do. Boundaries, process, history, and gotchas belong in `AGENTS.md` and the planning directory — not in READMEs.
- Every operation ends with a dated record row: `| Date | Step | Result |` in runbooks (`runbooks/agents/host.md`, `runbooks/agents/gcp.md`, `runbooks/agents/opencode.md`).

## Import Organization

**Terraform (`bootstrap/`, `infra/agents/`):**
1. `versions.tf` — `terraform { required_version, required_providers, backend "gcs" }` first (`bootstrap/versions.tf`, `infra/agents/versions.tf`).
2. `providers.tf` — provider config with comment on credentials/quota project (`bootstrap/providers.tf`).
3. `variables.tf` → resource files → `outputs.tf`. Pin provider `~> 8.6` and floor `>= 1.9` (`bootstrap/versions.tf`, `infra/agents/versions.tf`).
4. Never look up the boot image by family; pin the full image path in `var.host_image` (`infra/agents/variables.tf:45-49`).

**Python (`agents/wake/wake.py`, `agents/marketplace/plugins/slack/server.py`):**
1. Shebang `#!/usr/bin/env python3` + module docstring stating purpose, ADR link, and the dependency constraint.
2. Standard-library imports (alphabetical: `base64`, `json`, `sys`, `threading`, `time`, `urllib.error`, `urllib.request`).
3. Single third-party import last with Debian-package comment: `import websocket  # Debian package python3-websocket`.
4. No `requirements.txt`, no venv, no pip — dependencies are Debian packages installed by `provision.sh` (`python3-venv`, `python3-websocket` in `agents/host/provision.sh:22-23`).

**Bash (`agents/host/*.sh`, `agents/wake/*.sh`, `tests/agents/*.sh`, `agents/host/files/*`):**
1. Shebang `#!/usr/bin/env bash` + comment block: what the script does, ADR section, where/how to run it (root vs workstation).
2. `set -euo pipefail` immediately (all five top-level scripts: `agents/host/provision.sh`, `agents/host/apply.sh`, `agents/wake/provision.sh`, `agents/wake/apply.sh`, `tests/agents/host-checks.sh`).
3. Env guards with `: "${VAR:?message}"` (e.g. `: "${CLOUDSDK_CONFIG:?...}"` in `agents/host/apply.sh`, `agents/wake/apply.sh`).
4. Resolve own directory first: `HERE="$(cd "$(dirname "$0")" && pwd)"`.

**Path aliases:** none. Use repo-relative paths from the git top level (`cd "$(git rev-parse --show-toplevel)"` in `agents/host/apply.sh`) or absolute on-host paths (`/run/hyprn-agents/`, `/etc/hyprn-agents/`, `/opt/hyprn-agents/`).

## Error Handling

**Bash — fail fast, explain on stderr, exit non-zero:**
- `set -euo pipefail` everywhere; `set -o pipefail` also exported into `runuser` shells (`agents/host/provision.sh:127`).
- Guard clauses print to stderr and exit 1: `[ "$(id -u)" -eq 0 ] || { echo "... must run as root" >&2; exit 1; }` (`agents/host/provision.sh:14`, `agents/wake/provision.sh:5`).
- Validate trust anchors before use: Docker/GH CLI signing-key fingerprint mismatch aborts provisioning (`agents/host/provision.sh:29-30`, `:37-38`); unknown harness aborts (`agents/host/provision.sh:112`).
- Missing optional secrets are non-fatal by design: "Missing secrets are not fatal: the agent session then starts without its Slack channel" (`agents/host/files/hyprn-agent-secrets:4`); provisioning fixes forward (DNS allowlist fix, `HOME_MODE 0700` in `runbooks/agents/host.md` B3 record).
- Test scripts invert the pattern: `set -uo pipefail` (no `-e`) plus a `fail` accumulator so all checks run and the exit code summarizes (`tests/agents/host-checks.sh:4-8`).

**Python — catch at the boundary, log, keep the loop alive:**
- Catch `(urllib.error.URLError, ValueError)` around every network/JSON call and return a `{"ok": False, ...}` sentinel (`agents/wake/wake.py:71-72`, `agents/marketplace/plugins/slack/server.py:104-111`).
- Catch `(OSError, KeyError, ValueError)` around startup/config reads and log `not started:` without crashing (`agents/marketplace/plugins/slack/server.py:304-308`).
- Catch broad `Exception` only in the background catch-up loop with a `# keep the channel alive; record why` comment (`agents/marketplace/plugins/slack/server.py:234-235`); malformed envelopes are silently dropped after ack (`_on_envelope` in both files).
- Main loops never exit on transient failure: status-check failures set `status = ""` and retry in 15 s (`agents/wake/wake.py:133-143`); socket disconnects back off `1→60 s` (`agents/marketplace/plugins/slack/server.py:151-166`).

**Terraform — prevent destruction, require reviewed plans:**
- `deletion_policy = "PREVENT"` on projects, `prevent_destroy = true` on state buckets, `deletion_protection = true` on the host VM (`bootstrap/bootstrap_project.tf`, `bootstrap/agents.tf`, `infra/agents/host.tf`).
- Every apply uses a reviewed plan file (`terraform plan -out=...` then `terraform apply <planfile>` in `bootstrap/README.md`, `infra/agents/README.md`); `-parallelism=1` is required for org-policy writes (`bootstrap/README.md`).
- Destructive or privileged steps need the platform owner's explicit go for that exact step; removals get their own go (`AGENTS.md` "Authority").

## Logging

**Framework:** no logging library. Bash `log()` → stdout, Python `log()` → stderr (+ file for the Slack server).

**Bash pattern (`agents/host/provision.sh:16`):**
```bash
log() { printf '== %s\n' "$*"; }
log "agent $name ($uid, $harness)"
```
- Progress lines prefixed `== `; errors go to stderr with the script/object name (`echo "unexpected Docker signing key" >&2; exit 1`).

**Python pattern (`agents/wake/wake.py:32-33`, `agents/marketplace/plugins/slack/server.py:64-74`):**
```python
def log(*parts):
    print("hyprn-wake:", *parts, file=sys.stderr, flush=True)
```
- Prefix is the service name (`hyprn-wake:`, `hyprn-slack:`); the Slack server additionally appends timestamped lines to `~/.local/state/hyprn-slack/server.log` with 200 KB rotation, swallowing `OSError` so logging never crashes the channel.
- Log lifecycle events (connected/disconnected, delivered/dropped, start requested/failed) and API failures with the method name and error (`slack_api` in both files).

**When to log:** provisioning steps, host start/stop, socket connect/disconnect, delivered vs dropped messages (allowlist drops are logged, not silent), and every external-API failure. Never log secret values — check tokens by shape only and never include secrets in replies (`AGENTS.md`, `agents/marketplace/plugins/slack/server.py:44` INSTRUCTIONS).

## Comments

**When to comment:**
- File header on every script/program: purpose + ADR/section link + how to run (`agents/host/provision.sh:1-3`, `agents/wake/wake.py:1-11`, `tests/agents/host-checks.sh:1-3`, `agents/host/files/hyprn-agent-secrets:1-5`).
- Non-obvious security rationale inline: `# Agents use rootless Docker only; a rootful daemon would be root-equivalent` (`agents/host/provision.sh:46`), `# No access_config: no public IP` (`infra/agents/host.tf:17`), `# The bucket is created by this configuration; the first apply used local state...` (`bootstrap/versions.tf:11-12`).
- Keep-alive rationale on broad catches: `# keep the channel alive; record why` (`agents/marketplace/plugins/slack/server.py:234`).
- No commented-out code observed; pin provenance inline (`# opencode-linux-x64.tar.gz` on the SHA line in `agents/host/provision.sh:11`).

**Docstrings:** Python module docstrings only — one paragraph of what/why plus a `Dependencies:` line. No per-function docstrings; section banners (`# --- inbound ---`) separate the Slack channel's state/inbound/outbound blocks (`agents/marketplace/plugins/slack/server.py:129,147,252`).

## Function Design

**Size:** small single-purpose functions; the two large exceptions are `install_base`/`add_agent` in `agents/host/provision.sh` (linear provisioning steps, ~40/80 lines) and the `SlackChannel` class in `agents/marketplace/plugins/slack/server.py` (one method per protocol concern).
**Parameters:** positional in Bash with `local` bindings first (`add_agent() { local name="$1" uid="$2" ...` in `agents/host/provision.sh:108-109`); small explicit signatures in Python (`reply(self, chat_id, text, thread_ts=None)`).
**Return values:** Bash helpers signal via exit status; test helper `check <label> <predicate>` prints `PASS/FAIL` and sets `fail=1` without aborting (`tests/agents/host-checks.sh:8`). Python API helpers return parsed JSON or `{"ok": False, "error": ...}`; `reply()` returns an `(ok, error)` tuple.

## Module Design

**Exports:** Terraform roots expose only state-bucket IDs, project numbers, and folder references via `outputs.tf` (`bootstrap/outputs.tf`, `infra/agents/outputs.tf`). Python modules export one class (`Waker`, `SlackChannel`) driven by a `main()` loop; no shared library — `http`/`slack_api` helpers are duplicated per file to keep each program single-file deployable.
**Barrel files:** none. Per-directory `README.md` files act as the index: a file-purpose table per directory (exemplar: `agents/host/README.md` table mapping every file to its purpose).
**New code placement:** Terraform resource → the matching file in `bootstrap/` or `infra/agents/` (new concern = new file); host behavior → `agents/host/files/` + wire-up in `agents/host/provision.sh` + row in `agents/host/README.md`; wake behavior → `agents/wake/wake.py`; rendered-config policy → `policies/`; new check → `tests/agents/host-checks.sh` + mention in `tests/agents/README.md` and the ADR's Confirmation section.

---

*Convention analysis: 2026-10-13*
