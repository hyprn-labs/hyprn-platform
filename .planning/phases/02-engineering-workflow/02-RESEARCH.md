# Phase 2: Engineering workflow - Research

**Researched:** 2026-10-13
**Domain:** Agent engineering workflow (git worktrees, Slack-to-PR, herdr sessions, toolchains/caches, Claude telemetry)
**Confidence:** MEDIUM

## Summary

Phase 2 makes Ada turn Slack tasks into draft pull requests from isolated worktrees, and gives the owner one cockpit (herdr on the laptop + herdr on the host) plus daily cost visibility. The phase builds directly on five existing, audited assets: `opencode-task` (worktree creator), the Slack channel server (`server.py`), the ADR-0005 token broker, `provision.sh` (toolchain installs), and the `tests/agents/run.sh` + `checks/*.sh` harness.

The standard approach is: extend `opencode-task` into a shared worktree helper (port block + Compose project + test DB derived from a per-worktree index, cleanup on merge/close); add task-tag parsing to the channel server so a Slack task yields branch `agent/<name>/<slug>` + draft PR authored by the agent bot with a fixed body contract; replace the tmux wrapper with pinned, checksum-verified herdr under systemd user units (tmux stays fallback); extend `provision.sh` with product-pinned toolchains and per-agent persistent caches; collect Claude Code OTEL telemetry on the host and post a daily Slack digest (CODD-03 monthly re-check rides the same cycle).

**Primary recommendation:** Extend the five existing assets in place — do not build a new worktree tool, a new Slack bot, a new auth mechanism, or a new telemetry pipeline; every Phase 2 capability is a small delta on an audited file.

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Worktree helper (auto-accepted at agent discretion)

- Extend the `opencode-task` pattern (`agents/host/files/bin/opencode-task`): one worktree per task on branch `agent/<name>/<slug>`, with its own port block, Docker Compose project, and test database; worktree and local branch removed on merge/close.
- Product-side overrides (port, Compose project, database from environment) are deferred to `hyprn-mvp` — known blocker in STATE.md; the helper must work without them and pick them up when the product provides them.

#### Slack-to-PR flow (auto-accepted at agent discretion)

- Build on the channel server's task tags (`agents/marketplace/plugins/slack/server.py`) and the token broker (ADR-0005). Draft PRs authored by the agent bot state what changed and how it was verified; the agent never merges (deny rules backstop until the ruleset).
- Codd's terminal-driven draft-PR contract (`runbooks/agents/opencode.md`) is the same shape — one contract for both engineering agents.

#### herdr cockpit and runtime (auto-accepted at agent discretion)

- Laptop runs herdr as cockpit (owner seats + agent host over IAP SSH; one Claude Code config dir per seat; Remote Control for owner seats). Host replaces the tmux wrapper (`hyprn-agent@.service`, `hyprn-agent-session`) with pinned herdr (checksum-verified, systemd under the agent user, hooks allowed by POL-01); tmux stays the fallback.
- Agent-to-agent prompting stays off (locked, waits on Anthropic). Laptop install, seat config, and host provisioning apply are owner-go checklists, never automated.

#### Toolchains, caches and telemetry (auto-accepted at agent discretion)

- Provisioning installs the toolchains the product repositories pin (EFF-01); package and Docker layer caches persist per agent across tasks and host stops (EFF-02).
- Claude Code telemetry reaches a host collector; a daily per-agent report (tokens, cost, seat-limit hits) posts to Slack (OBS-01). The CODD-03 monthly free-tier model/terms re-check rides the same reporting cycle.

### Agent's Discretion

All Phase 2 answers were taken at agent discretion under the user's autonomous-run direction. Anything the planner finds unimplementable comes back as a planning question.

### Deferred Ideas (OUT OF SCOPE)

- Product-side worktree overrides (hyprn-mvp reads port/Compose/DB from environment).
- Agent-to-agent prompting (waits on Anthropic's answer).
- GitHub Issues intake (FLEET-04); Boole/control-plane work (Phases 3–5).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GH-01 | From a Slack task, Ada creates `agent/ada/<slug>`, pushes it and opens a draft PR authored by `ada-agent-hyprn[bot]` stating what changed and how verified; Ada does not merge | Task-tag parsing in `server.py` + token-broker `gh` wrapper + PR body contract patterns below |
| GH-02 | Worktree helper: one worktree per task with own port block, Compose project, test DB; removes worktree + local branch on merge/close | `opencode-task` extension pattern + per-worktree-index env derivation + Compose project namespacing |
| GH-03 | Interim machine account removed, secret deleted | Complete [VERIFIED: .planning/REQUIREMENTS.md:149] — no work; guard: no plan may reintroduce it |
| EFF-01 | Provisioning installs product-pinned toolchains so tasks start without installing tools | `provision.sh` extension pattern (pinned versions + signing-key checks) |
| EFF-02 | Package + Docker layer caches persist per agent across tasks and host stops | Rootless-docker per-user data-root + language-cache bind/volume persistence patterns |
| COK-01 | Laptop herdr cockpit: owner local seats + agent host over IAP SSH, one Claude config dir per seat, Remote Control on owner seat | herdr `machine add` over SSH + per-seat config-dir pattern |
| COK-02 | Host herdr replaces tmux wrapper: pinned release + checksum, systemd under agent user, resume after boot, hooks allowed by POL-01, agent-to-agent prompting off; Slack/wake/checks keep working | herdr install-verify pattern + systemd user-unit pattern + POL-01 hook-allowlist update |
| OBS-01 | Ada's Claude telemetry reaches host collector; daily per-agent Slack report (tokens, cost, seat-limit hits) | Claude Code OTEL env config + host collector + digest script via existing `reply` path |
| CODD-03 | Monthly free-tier model/cost/data-terms re-check vs Zen list until company move; then binding moves by config, no retirement | Digest-cycle cron + runbook-recorded check against Zen model list |

## Project Constraints (from AGENTS.md)

- Product code never enters this repository; platform infra never enters a product repository [VERIFIED: AGENTS.md:18-22]. Worktree helper must be repo-agnostic; product overrides live in `hyprn-mvp`.
- `hyprn-agents` is engineering tooling only: no product workload/data/deployment authority, no staging/prod access [VERIFIED: AGENTS.md:18-22].
- Spec authorizes nothing by itself — no cloud account/deployment/publication [VERIFIED: AGENTS.md:18-22].
- Every step creating/changing/deleting cloud resources, IAM, org policy, billing, GitHub/Slack/Claude org settings runs only after the platform owner's explicit go for that exact step or reviewed plan; removals get their own go [VERIFIED: AGENTS.md:24-29].
- Terraform: plan, review, apply exactly the reviewed plan; staging/prod separate state and authority [VERIFIED: AGENTS.md:24-29].
- Record what was done in the relevant runbook [VERIFIED: AGENTS.md:24-29].
- Never commit credentials, state/plan files, secret-valued tfvars, SA keys, session data; secrets live in password manager + Secret Manager [VERIFIED: AGENTS.md:31-36].
- Never print a secret value; check by shape only [VERIFIED: AGENTS.md:31-36].
- Run `gcloud`/Terraform/`gh` with HYPRN-dedicated configs (`CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`, `GH_CONFIG_DIR`) [VERIFIED: AGENTS.md:31-36].
- Content names roles/groups/agent identities, never people or personal accounts [VERIFIED: AGENTS.md:31-36].
- Owner-go checklist steps (laptop herdr install, seat config, host apply, console applies) must be plan tasks of type `checkpoint:human-verify` or owner-hand runbook steps, never automated shell actions.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Worktree isolation (ports, Compose project, test DB) | Agent host (Linux user + containers) | — | Isolation is per-OS-user/per-container; git only isolates files |
| Slack task intake + permission relay | Agent host (channel server per agent user) | Laptop (owner's Slack client) | Allowlist + Socket Mode live with the agent identity on the host |
| Draft-PR authoring | Agent host (token broker + `gh` wrapper) | GitHub (App installation) | One-hour installation token minted on host; GitHub enforces scope |
| Session runtime (herdr server per agent) | Agent host (systemd user unit) | Laptop cockpit (herdr client over IAP SSH) | Processes live on host; laptop only attaches/views |
| Toolchain provisioning + caches | Agent host (root provisioning + per-user data roots) | — | Root installs, agent users consume; caches are host disk state |
| Telemetry collection + daily digest | Agent host (collector + cron) | Slack (digest delivery via bot token) | Seat sessions export OTEL; host aggregates where secrets live |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `git worktree` + bash helper (`opencode-task` successor) | git as provisioned on host | One worktree/branch per task, cleanup on close | Existing audited pattern [VERIFIED: agents/host/files/bin/opencode-task:1-22]; `set -euo pipefail` convention [VERIFIED: agents/host/provision.sh:4] |
| Docker Compose (plugin `docker-compose-plugin`) + rootless Docker per agent user | As provisioned (Docker CE + rootless extras) [VERIFIED: agents/host/provision.sh:42-47] | Per-worktree service stacks | `COMPOSE_PROJECT_NAME` namespacing is the documented isolation mechanism [CITED: https://www.wkoorts.com/2026/08/24/one-postgresql-database-per-git-worktree-with-podman-and-codex/] |
| herdr (pinned release, checksum-verified) | Pin at plan time from `https://herdr.dev/latest.json` [ASSUMED] | Session runtime on host + cockpit on laptop | Spec-mandated session layer, tmux fallback [VERIFIED: docs/specs/agent-fleet.md:60-65] |
| Claude Code + Slack channel plugin `slack@hyprn-agents` | Claude Code 2.1.287 on host [VERIFIED: .planning/STATE.md:74]; plugin 0.1.1 [VERIFIED: .planning/STATE.md:74] | Seat sessions + Slack intake | In-service harness for Ada [VERIFIED: docs/specs/agent-fleet.md:19-25] |
| Claude Code OTEL telemetry (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_*_EXPORTER=otlp`) | Requires Claude Code ≥ 2.1.179 for SDK/OTLP diagnostics [CITED: https://code.claude.com/docs/en/agent-sdk/observability] | Token/cost/seat-limit export | First-party mechanism; metrics `claude_code.token.usage`, `claude_code.cost.usage`, `claude_code.session.count` [CITED: https://code.claude.com/docs/en/monitoring-usage/] |
| Python 3 stdlib + Debian `python3-websocket` | As provisioned [VERIFIED: agents/host/provision.sh:18-23] | Channel server runtime (no new deps) | ADR-0003 audit bar: stdlib-only, ~300 lines [VERIFIED: docs/adr/0003-own-slack-channel-server.md:29-34] |
| systemd user units (`hyprn-agent@.service` successor) + linger | systemd with `loginctl enable-linger` per agent [VERIFIED: agents/host/provision.sh:124] | Per-agent herdr server lifecycle + resume after boot | Established pattern: user units per agent [VERIFIED: .planning/phases/02-engineering-workflow/02-CONTEXT.md:56-59] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `gh` CLI via agent wrapper (`files/bin/gh`) | As provisioned (signed repo, fingerprint-checked) [VERIFIED: agents/host/provision.sh:34-44] | Draft-PR create/push with current token | All agent GitHub writes; reads token from tmpfs [VERIFIED: agents/host/files/bin/gh:1-5] |
| OpenTelemetry Collector (lightweight, host-local) | Pin at plan time [ASSUMED] | Receive OTLP from seat sessions, persist per-agent aggregates | Only if `claude_code.*` metrics need buffering before the digest; else digest script queries/scrapes directly |
| `direnv`-style env derivation script (`<repo>-env.sh`) | Shell, no package | Derive port block + state dirs from worktree index | Per-worktree env contract when product has services; no-op default for this repo [CITED: https://henrietteharmse.com/2026/07/27/end-to-end-testing-across-git-worktrees/] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extend `opencode-task` | New `wtc`-style orchestrator (`worktree-compose`, npm) | External npm tool adds supply-chain + root-ownership questions; derive-from-index script is ~60 lines and auditable — stay with extension per CONTEXT lock |
| Extend `server.py` task tags | GitHub Issues intake | Deferred to FLEET-04 trigger [VERIFIED: .planning/REQUIREMENTS.md:109]; Slack intake is the Phase 2 lock |
| herdr | Stay on tmux | tmux is the mandated fallback, not the target; spec §4 names herdr the session runtime [VERIFIED: docs/specs/agent-fleet.md:60-65] |
| Host-local OTEL collector + digest script | Hosted observability (Datadog/Honeycomb/Grafana Cloud) | Hosted adds vendor account + egress + cost before M2 gateway; host-local file/SQLite aggregates suffice for one daily Slack post |
| Per-worktree DB container | One shared Postgres with per-worktree logical DBs | Shared server needs in-server naming/cleanup and couples container-level config across branches; per-worktree project+volume is the safer default [CITED: https://www.wkoorts.com/2026/08/24/one-postgresql-database-per-git-worktree-with-podman-and-codex/] |

**Installation:**
```bash
# No new language-package installs. Host deltas ship via the existing path:
agents/host/apply.sh   # provisions toolchains, herdr, units, collector, digest cron
```

**Version verification:** No npm/PyPI/crates packages are recommended — all deltas are pinned host binaries (herdr, Claude Code 2.1.287, OpenCode 1.19.0 [VERIFIED: agents/host/provision.sh:8-12]) verified by fingerprint/checksum at provision time, and Debian packages. Nothing to `npm view`/`pip index`/`cargo search`.

## Package Legitimacy Audit

No external registry packages are installed by this phase. All runtime dependencies are already-provisioned host binaries and Debian packages with signing-key enforcement [VERIFIED: agents/host/provision.sh:28-44]:

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| herdr release tarball (pinned, checksum) | herdr.dev release asset | OK (verify SHA at plan time against `latest.json` + published checksum) | Approved — planner adds checksum-verify step |
| `python3-websocket` | Debian apt | OK | Approved (already provisioned) |
| OTEL Collector binary (if used) | vendor release asset | OK (verify checksum at plan time) | Approved — planner adds checksum-verify step |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious (SUS):** none.

## Architecture Patterns

### System Architecture Diagram

```text
Slack DM / @mention (owner only, allowlisted)
  │  Socket Mode (outbound WS, no public endpoint)
  ▼
channel server per agent (server.py + task tags) ── permission relay ──► owner yes/no
  │  task tag: "<slug>: <goal>" in thread
  ▼
worktree helper (opencode-task successor)
  │  branch agent/<name>/<slug> from origin/main
  │  worktree ~/work/<slug> + port block + COMPOSE_PROJECT_NAME + test DB
  ▼
agent session (herdr server under agent UID, systemd user unit)
  │  code + tests; gh wrapper mints App token (1h, broker)
  ▼
draft PR authored by <name>-agent-hyprn[bot] (body: changed + verified)
  │  owner reviews + merges (deny rules / ruleset backstop: agent never merges)
  ▼
cleanup hook: worktree remove + local branch delete on merge/close
  ║
  ╠═ telemetry: seat OTEL ─► host collector ─► daily Slack digest (+ monthly CODD-03 check)
  ╚═ cockpit: laptop herdr ──IAP SSH──► host herdr servers (watch/take over)
```

### Recommended Project Structure

```text
agents/host/files/bin/
├── opencode-task / ada-task (shared helper)  # one worktree per task + env derivation + cleanup
agents/marketplace/plugins/slack/
├── server.py                                  # task-tag parsing + reply/permission path (unchanged transport)
├── slack-app-manifest.yaml                    # unchanged scopes
agents/host/files/
├── hyprn-agent@.service (successor: herdr@.service)  # systemd user unit per agent
├── hyprn-agent-session (successor: herdr-session)    # herdr server launch + resume
agents/policy/
├── managed-settings.json                      # + herdr hooks allowlist (POL-01)
tests/agents/checks/
├── worktree.sh  # GH-02 checks (new)
├── github.sh    # + GH-01 PR-contract checks (extend)
├── herdr.sh     # COK-01/02 checks (new)
├── eff.sh       # EFF-01/02 checks (new)
├── obs.sh       # OBS-01/CODD-03 checks (new)
runbooks/agents/
├── engineering-workflow.md (new)  # helper use, PR contract, cockpit, digest
```

### Pattern 1: Per-worktree index → port block + Compose project + test DB

**What:** A single shell snippet derives every per-worktree value from one integer index (main checkout = 0). Ports, `COMPOSE_PROJECT_NAME`, state dirs, and DB names are pure functions of the index; nothing is negotiated or remembered [CITED: https://henrietteharmse.com/2026/07/27/end-to-end-testing-across-git-worktrees/].
**When to use:** Any repo with services (product repos); this repo (platform) uses the same helper with an empty service map so the contract is uniform.
**Example:**
```bash
# Source: derived from henrietteharmse.com worktree-isolation pattern + wkoorts.com Compose-project pattern
WORKTREE_INDEX="${WORKTREE_INDEX:-0}"          # 0 = main checkout; N = Nth worktree
BASE=$((20000 + WORKTREE_INDEX * 100))         # stride 100 avoids clustered-port collisions
export APP_PORT=$((BASE)); export APP_PORT_TEST=$((BASE + 1))
export COMPOSE_PROJECT_NAME="hyprn-wt-${WORKTREE_INDEX}-$(basename "$TASK_SLUG")"
export TEST_DB="hyprn_test_wt${WORKTREE_INDEX}"
# Compose file uses ${APP_PORT:-8080} style defaults so main checkout is unaffected
```

### Pattern 2: Slack task tag → branch → draft PR (one contract, both agents)

**What:** The channel server recognizes a task line (`task: <slug> <goal>` or equivalent tag the planner fixes), the helper creates `agent/<name>/<slug>`, and the agent opens a draft PR via the token-broker `gh` wrapper. The PR body always has `What changed` + `How verified`; the agent never runs `gh pr merge` (deny rules refuse it [VERIFIED: agents/policy/managed-settings.json:4-15]).
**When to use:** Every Ada task (Slack-driven) and every Codd task (terminal-driven, same body shape per `runbooks/agents/opencode.md` [VERIFIED: runbooks/agents/opencode.md:30-44]).
**Example:**
```bash
# Source: ADR-0005 token broker + runbooks/agents/opencode.md worktree flow
git -C "$BASE" fetch -q --prune origin
git -C "$BASE" worktree add -q "$DIR" -b "agent/$(id -un)/$SLUG" origin/main
# ... work ...
gh pr create --draft --title "<slug>: <goal>" --body "$(printf '## What changed\n%s\n\n## How verified\n%s' "$CHANGED" "$VERIFIED")"
```

### Pattern 3: herdr server per agent under systemd, laptop as cockpit

**What:** Host: pinned herdr binary (checksum-verified at provision, root-owned), one systemd user unit per agent (`loginctl enable-linger` already in place [VERIFIED: agents/host/provision.sh:124]), herdr server started under the agent UID, layout/session restore after boot; tmux unit kept disabled-but-present as fallback. Laptop: `herdr machine add` over IAP SSH; local owner seats each get their own Claude config dir; Remote Control only for the owner's own seat [VERIFIED: docs/specs/agent-fleet.md:146-149].
**When to use:** COK-01 (laptop) + COK-02 (host) together; never split — a host-only herdr with no cockpit leaves sessions invisible, violating the phase goal.
**Example:**
```bash
# Source: herdr remote-machine flow (herdr.dev/docs) + existing linger pattern
herdr machine add hyprn-agents-host-01 --ssh "gcloud compute ssh hyprn-agents-host-01 --tunnel-through-iap"
herdr machine status hyprn-agents-host-01   # reachable check for checks/herdr.sh
```

### Pattern 4: OTEL telemetry → host collector → daily Slack digest

**What:** Seat sessions export with `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` (host-local collector) [CITED: https://code.claude.com/docs/en/monitoring-usage/]; a small aggregator buckets by agent/day over `claude_code.token.usage` / `claude_code.cost.usage` / session/limit events; a cron posts per-agent tokens + estimated cost + seat-limit hits to Slack via the agent bot token; the same cron runs the CODD-03 monthly Zen-list re-check and appends to the runbook.
**When to use:** OBS-01 daily + CODD-03 monthly; seat sessions never pass through the M2 gateway [VERIFIED: docs/specs/agent-fleet.md:92-96].

### Anti-Patterns to Avoid

- **Product-specific ports baked into the helper:** helper must read env overrides with main-checkout defaults; hardcoded ports collide on the second worktree [CITED: https://henrietteharmse.com/2026/07/27/end-to-end-testing-across-git-worktrees/].
- **State inside the worktree:** large state slows git and `git worktree remove` refuses dirty trees — keep runtime state in sibling dirs keyed by worktree name [CITED: https://henrietteharmse.com/2026/07/27/end-to-end-testing-across-git-worktrees/].
- **One shared DB across worktrees:** migrations/seeds on one branch corrupt another — one project + volume per worktree [CITED: https://www.wkoorts.com/2026/08/24/one-postgresql-database-per-git-worktree-with-podman-and-codex/].
- **Agent merges its own PR:** refused by deny rules today and the Team-plan ruleset in Phase 1 — plans must never include a merge step for the agent [VERIFIED: agents/policy/managed-settings.json:4-15].
- **Automating owner-go steps:** laptop install, seat sign-in, console applies, `apply.sh` on the host need explicit go per AGENTS.md — automate nothing that touches those identities [VERIFIED: AGENTS.md:24-29].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Worktree orchestration | New CLI/daemon | Extend `opencode-task` + index-derived env | Audited 22-line base [VERIFIED: agents/host/files/bin/opencode-task:1-22]; community equivalents need registries/daemons |
| Slack transport | New bot framework / webhook receiver | Extend `server.py` task tags; keep Socket Mode | ADR-0003 audit (stdlib-only, allowlist, no inbound endpoint) [VERIFIED: docs/adr/0003-own-slack-channel-server.md:29-34]; webhook receiver is explicitly deferred to its own ADR [VERIFIED: docs/specs/agent-fleet.md:83-85] |
| GitHub auth | Long-lived tokens / machine accounts | ADR-0005 App + broker + `gh` wrapper | 1-hour tokens, no seat/email/2FA, bot-attributed PRs [VERIFIED: docs/adr/0005-agent-github-app.md:28-32]; machine account is removed (GH-03) |
| Session persistence | Custom tmux manager | herdr (pinned) + systemd user units | Spec §4 mandates it; restore/resume/handoff semantics already tested upstream [CITED: https://herdr.dev/docs/session-state/] |
| Telemetry pipeline | Custom token counting / log scraping | Claude Code OTEL (`claude_code.token.usage`, `claude_code.cost.usage`) | First-party counters with per-model breakdown [CITED: https://code.claude.com/docs/en/monitoring-usage/]; scraping undercounts cache reads |
| Approval flow | Parallel approve mechanism | Claude Code permission relay via channel server (`yes/no <id>`) | ADR-0003 driver: the agent cannot change the approver list [VERIFIED: docs/adr/0003-own-slack-channel-server.md:13-18] |

**Key insight:** Every Phase 2 problem already has an audited half-solution in the repo; the failure mode of this phase is building a second copy instead of extending the first.

## Common Pitfalls

### Pitfall 1: Second worktree collides on ports/volumes/DB

**What goes wrong:** Two tasks run side by side (roadmap success criterion 2) and the second fails with "address already in use" or corrupts the first's data.
**Why it happens:** Git isolates files only; ports, data dirs, Compose projects, and DBs are machine-global [CITED: https://henrietteharmse.com/2026/07/27/end-to-end-testing-across-git-worktrees/].
**How to avoid:** Index-derived port blocks (stride 100), `COMPOSE_PROJECT_NAME` per worktree, per-worktree DB name/volume, state dirs outside the worktree.
**Warning signs:** Single-worktree tests pass; two-worktree test fails.

### Pitfall 2: Claude Code replaces the channel server seconds after start; intake work is lost

**What goes wrong:** Task-tag handling added at server start never runs for the first message.
**Why it happens:** Known gotcha — Claude Code may replace the channel server a few seconds after start [VERIFIED: .planning/STATE.md:84].
**How to avoid:** Keep task-tag parsing stateless (derive from the message, not startup state); keep the 5/30/90 s catch-up [VERIFIED: agents/marketplace/plugins/slack/server.py:37]; dedupe via `seen.json` [VERIFIED: agents/marketplace/plugins/slack/server.py:130-146].
**Warning signs:** First task after boot is ignored; repeats work.

### Pitfall 3: herdr version skew between laptop and host breaks attach

**What goes wrong:** Cockpit shows `! error` / attach fails after one side updates.
**Why it happens:** Remote attach negotiates endpoint generations; pre-generation-1 servers need a stop [CITED: https://herdr.dev/docs/cli-reference/].
**How to avoid:** Pin the same herdr release on both ends in the same plan; `herdr machine status` in checks; document `herdr update` as an owner-go step, never silent auto-update.
**Warning signs:** `machine list` reachable but panes don't render.

### Pitfall 4: Telemetry lost on short sessions (batch flush window)

**What goes wrong:** Daily digest undercounts costs.
**Why it happens:** CLI batches telemetry (metrics 60 s, logs 5 s defaults) and flush is bounded on exit; killed-before-flush data is lost [CITED: https://code.claude.com/docs/en/agent-sdk/observability].
**How to avoid:** Lower `OTEL_METRIC_EXPORT_INTERVAL` / `OTEL_LOGS_EXPORT_INTERVAL` for seat sessions; keep collector host-local (fast ack); treat digest as lower-bound and say so in the post.
**Warning signs:** Digest total < sum of visible session costs.

### Pitfall 5: Idle-stop kills the host mid-task or mid-digest

**What goes wrong:** Host powers off during a long agent run or before the digest cron fires.
**Why it happens:** Idle stop watches terminal input/SSH/load/agent activity; an idle-at-prompt agent does not hold the host [VERIFIED: runbooks/agents/opencode.md:38].
**How to avoid:** herdr server activity must count as agent activity (extend the same signal OpenCode/Claude sessions emit); digest cron touches `/run/hyprn-agents/hold` while running; running containers already hold the host for M2 parity [VERIFIED: docs/specs/agent-fleet.md:66].
**Warning signs:** Morning digest missing; sessions report restart without reboot.

### Pitfall 6: Product-override blocker silently reappears

**What goes wrong:** Helper assumes product env vars exist; platform tasks pass but product tasks collide.
**Why it happens:** Product-side overrides are deferred (known blocker [VERIFIED: .planning/STATE.md:110]) — helper must work without them.
**How to avoid:** `${VAR:-default}` in every Compose port and env read; fail-fast `*_TEST` guard (never fall back to production values) [CITED: https://henrietteharmse.com/2026/07/27/end-to-end-testing-across-git-worktrees/].
**Warning signs:** Helper works on `hyprn-platform`, breaks on `hyprn-mvp`.

## Code Examples

### Task-tag delivery (extend, do not replace)

```python
# Source: agents/marketplace/plugins/slack/server.py:185-223 (verbatim structure)
# _on_event routes DM/app_mention -> _deliver; allowlist + seen-dedupe stay.
# Phase 2 adds: TASK_TAG regex + notify("notifications/hyprn/task", {...})
# alongside the existing channel notify — transport, VERDICT relay, catch-up unchanged.
TASK_TAG = re.compile(r"^\s*task:\s*([a-z0-9][a-z0-9-]{0,40})\s+(.+)$", re.IGNORECASE | re.DOTALL)
```

### Worktree create + cleanup (extend opencode-task)

```bash
# Source: agents/host/files/bin/opencode-task:10-22 + runbooks/agents/opencode.md:40-44
set -euo pipefail
task="${1:?usage: <helper> <task-name>}"
[[ "$task" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || { echo "use lowercase letters, digits and dashes" >&2; exit 1; }
base="$HOME/work/hyprn-platform"   # or "$HOME/work/hyprn-mvp" for product tasks
branch="agent/$(id -un)/$task"; dir="$HOME/work/$task"
git -C "$base" fetch -q --prune origin
if [ ! -d "$dir" ]; then
  if git -C "$base" show-ref --quiet --verify "refs/heads/$branch"; then
    git -C "$base" worktree add -q "$dir" "$branch"
  else
    git -C "$base" worktree add -q "$dir" -b "$branch" origin/main
  fi
fi
# Phase 2 adds: source env-derivation (Pattern 1) + herdr/tmux session exec (already execs tmux [VERIFIED: agents/host/files/bin/opencode-task:22])
# Cleanup (post-merge/close hook): git -C "$base" worktree remove "$dir" && git -C "$base" branch -d "$branch"
```

### Draft PR with contract body (token-broker gh)

```bash
# Source: ADR-0005 broker + agents/host/files/bin/gh:1-5 (GH_TOKEN from tmpfs)
gh pr create --draft --title "$SLUG: $GOAL" \
  --body "## What changed
$CHANGED

## How verified
$VERIFIED"
# Never: gh pr merge (denied [VERIFIED: agents/policy/managed-settings.json:4-15])
```

### Seat telemetry env (host-provisioned)

```bash
# Source: https://code.claude.com/docs/en/monitoring-usage/ (env table)
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_METRIC_EXPORT_INTERVAL=10000 OTEL_LOGS_EXPORT_INTERVAL=2000
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Machine account + 90-day token (ADR-0004) | Per-agent GitHub App + 1-hour broker tokens (ADR-0005) | 2026-10-13 [VERIFIED: docs/adr/0005-agent-github-app.md:1-5] | GH-01 PRs authored by bot; GH-03 cleanup complete |
| tmux wrapper as session runtime | herdr server per agent + systemd user unit | This phase (spec §4 target) [VERIFIED: docs/specs/agent-fleet.md:60-65] | Sessions resumable, cockpit-visible; tmux fallback retained |
| Manual usage eyeballing | OTEL `claude_code.*` metrics + collector + digest | This phase (OBS-01) | Daily cost/seat-limit visibility; monthly tier review input |
| Free-form Slack instructions | Task-tag convention → branch → draft PR | This phase (GH-01) | Traceable task→branch→PR chain |

**Deprecated/outdated:**
- `hyprn-ada` machine account + `ada-agent-github-token` secret: removed [VERIFIED: runbooks/agents/github.md:43]; plans must not reference them.
- OpenCode for Ada: removed; OpenCode is Codd's harness only [VERIFIED: runbooks/agents/opencode.md:64].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | herdr release pin + checksum URL shape (`latest.json`, per-arch tarball) | Standard Stack / Pattern 3 | Low — planner pins exact version + checksum at plan time; checksum-verify step catches mismatch |
| A2 | herdr IAP-SSH cockpit works through `gcloud compute ssh --tunnel-through-iap` as the SSH transport | Pattern 3 | Medium — IAP TCP forwarding quirks; mitigate with `machine status` check + owner-go setup step |
| A3 | OTEL Collector needed vs digest-script-only | Pattern 4 | Low — planner spikes host-local collector; fallback is direct scrape into SQLite |
| A4 | Product-pinned toolchain list (product repos' pinned versions) | EFF-01 | Medium — unknown until product repos read; planner reads `hyprn-mvp` pins at plan time, defaults to current host set |
| A5 | Seat-limit-hit signal available in telemetry (vs console-only) | OBS-01 | Medium — if no counter exists, digest infers from 429/error events; flag as Wave 0 spike |

## Open Questions

1. **Exact task-tag syntax**
   - What we know: server routes DMs + mentions with allowlist + dedupe [VERIFIED: agents/marketplace/plugins/slack/server.py:185-223]; no tag convention exists yet.
   - What's unclear: `task: <slug> <goal>` vs richer structured tag (repo choice platform/mvp, thread binding).
   - Recommendation: planner fixes `task: <slug> <goal> [--repo mvp]` in the plan; discuss-phase confirms.

2. **herdr pinned version**
   - What we know: spec mandates pinned + checksum [VERIFIED: docs/specs/agent-fleet.md:60-65]; OpenCode precedent pins version + SHA in `provision.sh` [VERIFIED: agents/host/provision.sh:8-12].
   - What's unclear: which herdr release is current on plan day.
   - Recommendation: planner resolves `latest.json` at plan time, records version + SHA in the plan.

3. **Collector vs direct-scrape for OBS-01**
   - What we know: OTEL metrics + endpoint env documented [CITED: https://code.claude.com/docs/en/monitoring-usage/]; seat-limit semantics uncertain (A5).
   - What's unclear: whether a collector binary is justified for a single daily post.
   - Recommendation: Wave 0 spike — try digest-script-only first, add collector only if batching loses data (Pitfall 4).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Agent host `hyprn-agents-host-01` | All host work | ✓ (on demand, IAP SSH) [VERIFIED: .planning/STATE.md:72] | Debian 12, t2d-standard-8 | Start via gcloud; owner-go |
| git + `gh` (signed, fingerprinted) | GH-01/GH-02 | ✓ on host [VERIFIED: agents/host/provision.sh:18-44] | gh via githubcli apt | None — host-provided |
| Rootless Docker + Compose plugin per agent | GH-02 test stacks | ✓ on host [VERIFIED: agents/host/provision.sh:130-133] | As provisioned | Skip service stacks; code-only tasks |
| Claude Code seat (Ada) + channel plugin | GH-01/OBS-01 | ✓ [VERIFIED: .planning/STATE.md:74] | 2.1.287 / plugin 0.1.1 | None — seat required; owner-go sign-in |
| herdr release asset | COK-01/02 | [ASSUMED] downloadable at plan time | Pin at plan time | tmux wrapper stays (mandated fallback) |
| OTEL collector binary (optional) | OBS-01 | [ASSUMED] | Pin at plan time | Digest-script-only (no collector) |
| Slack bot tokens (per agent, Secret Manager) | GH-01/OBS-01 digest | ✓ (`ada-agent-*` v1, allowlist v3) [VERIFIED: .planning/STATE.md:73] | — | None — owner loads values |
| GitHub Apps (`ada-agent-hyprn`, `codd-agent-hyprn`) | GH-01 | ✓ (Apps 5299141/5306008) [VERIFIED: .planning/STATE.md:75] | — | None |
| Product toolchain pins (`hyprn-mvp`) | EFF-01 | Unknown until product read (A4) | — | Current host set; record gap |

**Missing dependencies with no fallback:**
- GitHub Team plan (ruleset hard backstop) — arrives later per STATE purchases note [VERIFIED: .planning/STATE.md:96]; until then deny rules are the only control [VERIFIED: .planning/STATE.md:104]. Phase 2 live merge-refusal tests must order after the Phase 1 green run or be marked gated (see Ordering section below).

**Missing dependencies with fallback:**
- herdr binary (fallback: tmux), collector binary (fallback: direct scrape), product pins (fallback: current toolchains).

## Ordering vs Deferred Phase 1 Live Proofs

Phase 1 verification is `verification_deferred_human`, resume via `/gsd-verify-work 1` [VERIFIED: .planning/STATE.md:121-126]. Phase 2 plans MUST NOT assume Phase 1 controls are proven:

1. Any Phase 2 live test that depends on a Phase 1 control (ruleset refuses agent merge/push to `main`; deny rules refuse `gh pr merge`; egress observe-mode logging; allowlist-gated Slack intake) is ordered **after** the Phase 1 green run, or marked **gated** with its Phase 1 gate named.
2. Static/file work (helper script, server tag parsing, unit files, collector config, digest script, new `checks/*.sh`) proceeds immediately — no gate.
3. The GH-01 end-to-end live proof (Slack task → draft PR, agent-does-not-merge) additionally requires the Team plan if the ruleset backstop is asserted; otherwise it asserts the deny-rule backstop only and says so in the check output (mirrors `checks/github.sh` static/live split [VERIFIED: tests/agents/checks/github.sh:35-47]).

## Validation Architecture

Test harness: `tests/agents/run.sh` runs `host-checks.sh` then every executable `tests/agents/checks/*.sh` and appends a dated record to `runbooks/agents/` [VERIFIED: tests/agents/run.sh:1-14]. Each Phase 2 group adds one script (ACC-08 continuity).

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| GH-01 | Task tag → branch `agent/<name>/<slug>` + draft PR by bot with contract body; `gh pr merge` refused in session | integration (live, gated on Phase 1 green) + static (body template, deny rule present) | `tests/agents/run.sh` (domain `checks/github.sh` extended) | ❌ Wave 0 (extend `checks/github.sh`) |
| GH-02 | Two worktrees side by side (ports/Compose/DB isolated); merge/close leaves no worktree, branch, volume, or DB | integration (two concurrent worktrees run test stacks) | `tests/agents/checks/worktree.sh` via `run.sh` | ❌ Wave 0 (new) |
| GH-03 | No machine account/secret resurrected | static (grep: no `hyprn-ada` account refs, no `ada-agent-github-token` secret) | part of `checks/github.sh` | ✅ exists (extend with negative grep) |
| EFF-01 | Fresh worktree runs pinned toolchain versions without installs | integration (`--version` pins match product pins) | `tests/agents/checks/eff.sh` via `run.sh` | ❌ Wave 0 (new) |
| EFF-02 | Caches survive task cycle + host stop/start cycle | integration (marker file in cache vol survives helper cycle; best-effort across reboot) | `tests/agents/checks/eff.sh` via `run.sh` | ❌ Wave 0 (new) |
| COK-01 | Laptop herdr shows local + host sessions (`machine status` reachable) | manual-only (laptop is owner hands) + static (manifest of expected machines) | owner checklist in runbook, recorded dated row | ❌ Wave 0 (runbook section; cannot automate owner laptop) |
| COK-02 | Host sessions run under herdr (systemd active, survives reboot signal, hooks in POL-01, p2p off); Slack/wake/checks green | integration (unit active, resume, hook-allowlist grep) + regression (`run.sh` full pass) | `tests/agents/checks/herdr.sh` via `run.sh` | ❌ Wave 0 (new) |
| OBS-01 | Telemetry reaches collector; daily digest posts tokens/cost/limit-hits to Slack | integration (emit test metric → collector; digest dry-run) + manual (real daily post observed) | `tests/agents/checks/obs.sh` via `run.sh` | ❌ Wave 0 (new) |
| CODD-03 | Monthly Zen-list re-check recorded | static (dated runbook row ≤ 31 days) + manual (owner confirms terms) | `tests/agents/checks/obs.sh` (staleness grep) | ❌ Wave 0 (new; same script) |

### Sampling Rate

- **Per task commit:** `bash -n <changed-script> && shellcheck <changed-script>` (fast syntax gate; no host needed).
- **Per wave merge:** `tests/agents/run.sh` static subset off-host ( host-only live checks SKIP as in `checks/github.sh` [VERIFIED: tests/agents/checks/github.sh:39-47]).
- **Phase gate:** Full `tests/agents/run.sh` green **on the host** (after owner-go `apply.sh`) before `/gsd-verify-work`; live GH-01/COK-02/OBS-01 proofs additionally gated on Phase 1 green run.

### Wave 0 Gaps

- [ ] `tests/agents/checks/worktree.sh` — covers GH-02 (two-worktree isolation + cleanup incl. volumes/DBs)
- [ ] `tests/agents/checks/herdr.sh` — covers COK-02 (unit active, herdr version pin + checksum, p2p off, hooks in policy)
- [ ] `tests/agents/checks/eff.sh` — covers EFF-01/EFF-02 (toolchain pins, cache persistence markers)
- [ ] `tests/agents/checks/obs.sh` — covers OBS-01/CODD-03 (collector reachability, digest dry-run, Zen-check staleness)
- [ ] Extend `tests/agents/checks/github.sh` — GH-01 (PR body contract grep + live bot-author assertion) + GH-03 (negative grep)
- [ ] Runbook `runbooks/agents/engineering-workflow.md` — COK-01 owner checklist (laptop install, seat config dirs, Remote Control, `machine add` over IAP)

*(No existing test infrastructure covers Phase 2 behaviors — all five scripts are new or extended.)*

## Security Domain

`security_enforcement` is `true` and `security_asvs_level` is 1 [VERIFIED: .planning/config.json:46-50] — this section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | GitHub App 1-hour installation tokens via root broker; Slack `xapp`/`xoxb` in Secret Manager → tmpfs agent-only; no long-lived tokens in agent reach [VERIFIED: docs/adr/0005-agent-github-app.md:28-32] |
| V3 Session Management | Yes | herdr servers per Linux UID with 0700 homes [VERIFIED: agents/host/provision.sh:117]; systemd user isolation; tmux/herdr attach requires `sudo -iu` (admin) |
| V4 Access Control | Yes | Ruleset on `main` (Phase 1, Team plan) + Claude deny rules second layer [VERIFIED: agents/policy/managed-settings.json:4-15]; agent never merges; Codd App limited to 2 repos [VERIFIED: runbooks/agents/github.md:32] |
| V5 Input Validation | Yes | Slack allowlist by member ID (`U`/`W`, never `A` app IDs [VERIFIED: .planning/STATE.md:86]); task-tag slug regex `^[a-z0-9][a-z0-9-]{0,40}$` [VERIFIED: agents/host/files/bin/opencode-task:8]; `*_TEST` fail-fast guards |
| V6 Cryptography | Partial | App private keys in Secret Manager (host-read-only); JWT held in memory only [VERIFIED: docs/adr/0005-agent-github-app.md:28-32]; herdr/checksum verification over TLS |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Slack sender spoofing / non-owner task injection | Spoofing | Allowlist + `yes/no` from allowlisted IDs only; non-allowlisted dropped without reaction [VERIFIED: agents/marketplace/plugins/slack/server.py:194-198] |
| Task slug → path/branch injection | Tampering | Strict slug regex + `set -euo pipefail`; never interpolate slug into shell without quoting |
| Agent self-merge / push to `main` | Elevation of privilege | Deny rules + ruleset (no App bypass; `bypass_actors` empty asserted [VERIFIED: tests/agents/checks/github.sh:19]) |
| Token exfiltration via PR body / Slack reply | Information disclosure | Secrets never in replies (server INSTRUCTIONS [VERIFIED: agents/marketplace/plugins/slack/server.py:39-45]); shape-only checks [VERIFIED: AGENTS.md:31-36] |
| Cross-agent secret/container reach | Information disclosure | 0700 homes, per-agent tmpfs secrets, per-agent Docker context; ACC-07 full isolation lands Phase 4 |
| Egress bypass from worktree containers | Tampering / Exfiltration | Phase 1 observe-mode proxy covers agent users; run-container allowlists are Phase 3 (EGR-03) — Phase 2 containers inherit host egress posture, do not weaken it |
| Prompt-in-task-payload injection | Tampering | Trigger payloads are untrusted; authority is the reviewed loop/helper definition (ADR-0006 rule 3 [VERIFIED: docs/adr/0006-agent-first-operating-model.md:39-51]) |

## Sources

### Primary (HIGH confidence)

- `agents/host/files/bin/opencode-task` (22 lines) — worktree/branch/session base pattern
- `agents/marketplace/plugins/slack/server.py` (329 lines) — allowlist, VERDICT relay, catch-up, dedupe, reply tool
- `agents/host/provision.sh` — pinned versions (Claude 2.1.287, OpenCode 1.19.0 + SHA), signing-key checks, linger, per-agent setup
- `agents/host/files/hyprn-agent@.service` + `hyprn-agent-session` — tmux unit being replaced
- `agents/policy/managed-settings.json` — deny/ask/allow + bypass-disable (POL-01/04)
- `docs/adr/0003/0005/0006`, `docs/specs/agent-fleet.md` §§2/4/11, `runbooks/agents/{opencode,github,slack,host}.md`
- `.planning/{REQUIREMENTS,ROADMAP,STATE}.md`, `02-CONTEXT.md`, `tests/agents/{run.sh,checks/github.sh}`

### Secondary (MEDIUM confidence)

- [CITED: https://code.claude.com/docs/en/monitoring-usage/] — OTEL env vars, `claude_code.*` metric names
- [CITED: https://code.claude.com/docs/en/agent-sdk/observability] — batching/flush loss, ≥2.1.179 diagnostics, console-exporter warning
- [CITED: https://herdr.dev/docs/session-state/] — restore/resume semantics, logind shutdown delay
- [CITED: https://herdr.dev/docs/cli-reference/] — `machine add/status`, version-generation skew, `--handoff` scope
- [CITED: https://henrietteharmse.com/2026/07/27/end-to-end-testing-across-git-worktrees/] — index-derived ports/state, `${VAR:-default}`, `*_TEST` fail-fast
- [CITED: https://www.wkoorts.com/2026/08/24/one-postgresql-database-per-git-worktree-with-podman-and-codex/] — Compose-project + volume + port-per-worktree DB isolation

### Tertiary (LOW confidence)

- herdr `latest.json` pin shape, OTEL collector choice, seat-limit-hit metric availability, product toolchain pins — all [ASSUMED], carried in Assumptions Log A1–A5 for planner spikes/confirmations.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — in-repo assets verified by Read this session; herdr/OTEL specifics cited from official docs; four values pinned at plan time.
- Architecture: MEDIUM — patterns combine verified in-repo structure with cited community isolation practice; product-side contract unknowable until `hyprn-mvp` read.
- Pitfalls: HIGH — five of six pitfalls are in-repo gotchas (STATE.md) or documented upstream flush/skew semantics.

**Research date:** 2026-10-13
**Valid until:** 2026-11-13 (stable domain; re-pin herdr/Claude versions at plan time)
