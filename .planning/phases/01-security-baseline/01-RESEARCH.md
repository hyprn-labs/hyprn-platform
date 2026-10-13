# Phase 1: Security baseline - Research

**Researched:** 2026-10-13
**Domain:** Agent-fleet safety controls (GitHub org protection, Claude Code/OpenCode policy enforcement, host egress observation, GCP misuse detection, account safeguards, one-command acceptance checks)
**Confidence:** MEDIUM (official-docs-backed for GitHub/Claude/GCP shapes; host-side specifics inferred from in-repo assets)

## Summary

Phase 1 proves the platform's safety controls in one check command (`tests/agents/run.sh`, greenfield) while the GitHub Team plan purchase is still pending. The central constraint is D-01: on the Free plan neither organization rulesets nor branch protection on private repositories can be applied, so GHE-01 enforcement is deferred and the phase delivers a **reviewed ruleset definition ready to apply** plus **proven deny rules as the interim control**. Everything else — App-scope refusal checks (GHE-03), the Claude Code organization policy (POL-01..04), Squid egress observation (EGR-01), Secret Manager/IAM alerts (DET-01/02), break-glass and 2FA (SEC-01/02), Slack relay and isolation checks (ACC-01..06), the `run.sh` harness (ACC-08), and Codd both-repo scope (CODD-01) — is provable now.

The recommended shape per requirement group is: (1) a `agents/github/main-ruleset.json` file matching the REST `create-a-repository-ruleset` payload with an empty `bypass_actors` list, reviewed but not applied; (2) `agents/policy/managed-settings.json` written in the exact managed-settings shape (deny-first rules, `disableBypassPermissionsMode`, `allowManagedPermissionRulesOnly`, `strictKnownMarketplaces` pinned to `hyprn-agents`, sandbox network allowlist) with variant-tolerant Bash patterns; (3) an explicit (non-transparent) Squid forward proxy with per-agent credentials/ports, nftables drop-direct rules keyed on agent UIDs **plus their subuid ranges**, DNS port 53 kept open, and access logs shipped to Cloud Logging; (4) `DATA_READ` audit config for Secret Manager plus two log-based Monitoring alert policies emailing `gcp-admins@hyprn.ai`; (5) owner-go checklists for break-glass, 2FA, console policy match, and alert live-tests; (6) `run.sh` as a `set -euo pipefail` orchestrator over `host-checks.sh` plus new per-domain check scripts, each run writing a dated record to `runbooks/agents/`.

**Primary recommendation:** Build the phase as "deny-rules + observe-everything + reviewed-but-unapplied ruleset", with every owner-hand step an explicit checklist item the plan requests but never automates.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** GHE-01 enforcement is deferred to the Team-plan purchase (owner decision 2026-10-13, purchases arrive later). Phase 1 delivers a reviewed ruleset definition ready to apply plus proven Claude Code deny rules (POL-04) as the interim control. The planner MUST reshape success criterion 1 accordingly instead of planning an impossible apply.
- **D-02:** GHE-03 (refuse merge/push to `main` by Apps) is provable now through deny rules in both repositories; only its ruleset half is deferred with GHE-01.
- **D-03:** The App-scope check covers both `hyprn-platform` and `hyprn-mvp` — Codd's App installation on both was verified 2026-10-13 by a branch push to each (commit `30ee1b1`). The stale "platform-only" lines merged earlier (REQUIREMENTS CODD-01, spec §2 GitHub row, README, PROJECT.md) are corrected inside Phase 1 as CODD-01 groundwork.
- **D-04:** `hyprn-mvp` carries no secrets and no staging/prod. Host-level controls (managed OpenCode policy, egress, Linux user boundary) cover both repositories identically; repo-level assertions (App scope, deny-rule refusals) are checked per repository.
- **D-05:** Observe mode means per-agent, per-destination connection logs to Cloud Logging with no blocking. In scope: the `ada` and `codd` Linux users and their containers, plus wake-service traffic. DNS stays allowed — the metadata-server address is also the resolver, so blocking it must keep port 53 open (known gotcha).
- **D-06:** Observation runs continuously from Phase 1; allowlist enforcement stays Phase 7 (EGR-02). Phase 1 is done when logs flow per agent and the direct-connection drop test passes (existing success criterion 4).
- **D-07:** Build `tests/agents/run.sh` on top of `tests/agents/host-checks.sh` (40 pass). Every check writes a dated record to `runbooks/agents/`. `agents/policy/` currently holds only a README — `managed-settings.json` and the egress allowlist file are created in this phase.
- **D-08:** Live-test deny-rule refusals (Ada session and Codd), the egress drop, and alert delivery. Owner-hand steps — break-glass admin, 2FA, admin-console policy match, alert test actions, IAM search with owner credentials — are explicit owner-go checklists the plan requests; the plan MUST NOT automate them. POL-03 (`strictKnownMarketplaces` evidence) is a must-verify item (flagged unevidenced in STATE.md).

### The Agent's Discretion

The user approved all four areas beforehand and asked for an autonomous run. All decisions above were taken at agent discretion within locked prior decisions (deny-rules as interim control, deferred purchases, Codd on both repos, owner go per infra step). Anything the planner finds unimplementable should come back as a planning question, not a silent scope change.

### Deferred Ideas (OUT OF SCOPE)

- GHE-01 ruleset enforcement at Team-plan purchase time (deferred requirement, not in this phase).
- Boole, gateway, and control-plane work (Phases 3–5); fleet-as-code onboarding of Codd-pattern agents (Phase 6, CODD-02).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GHE-01 | Team plan + CODEOWNERS + ruleset on `main` (PR required, human owner approval, stale dismissed, no force push, no App bypass) | Ruleset JSON shape (§GHE); Free-plan gap analysis; CODEOWNERS pattern |
| GHE-03 | GitHub refuses agent-App merge/push to `main`; agent approval doesn't satisfy the rule | Interim deny-rule proof; ruleset `bypass_actors: []`; live refusal tests |
| POL-01 | Org policy in `agents/policy/managed-settings.json` (allow/ask/deny + herdr hooks); owner applies in console; changes recorded in `runbooks/agents/claude.md` | Managed-settings shape + precedence rules (§POL) |
| POL-02 | Sandbox network allowlist in that policy; off-list hosts fail inside sandbox | `sandbox.network.allowedDomains` + `allowManagedDomainsOnly` |
| POL-03 | `strictKnownMarketplaces` accepts only `hyprn-agents` | Managed-only key semantics + evidence procedure |
| POL-04 | Deny rules refuse merge, push to `main`, force push in every repo | Deny-first precedence + variant-tolerant Bash patterns |
| EGR-01 | Squid forward proxy as only way out; firewall by Linux user; drop direct; DNS allowed; per-agent destinations to Cloud Logging, observe mode | Explicit-proxy design + nftables skuid + per-agent identity (§EGR) |
| DET-01 | Data Access audit on Secret Manager; alert to `gcp-admins@hyprn.ai` on unexpected reads, creates/deletes/new readers | Audit config + log-based alert query (§DET) |
| DET-02 | Alert on IAM policy change in `hyprn-agents`; folder-level via log sink | SetIamPolicy alert + sink design |
| SEC-01 | Break-glass super admin (own key + offline backups, no standing GCP role); use in `runbooks/agents/gcp.md` | Owner checklist (§SEC) |
| SEC-02 | 2FA required for all `hyprn-labs` members | Console step, Free-plan eligible |
| DOC-01 | ADR-0003 records own Slack channel server | Complete — no research needed |
| ACC-01..06 | Slack relay, sender allowlist, refusals, IAM search, host cleanliness, wake limits | Verification procedures (§Validation) |
| ACC-08 | One command `tests/agents/run.sh` + dated record; later phases extend | Harness pattern (§Checks) |
| CODD-01 | Codd scope: App on both repos, 1h tokens, user `codd`, managed OpenCode config, no Slack/Workspace | Existing assets + both-repo checks |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `main` protection (ruleset definition) | GitHub (SaaS control plane) | — | Enforcement lives in GitHub; repo holds only the reviewed definition |
| Merge/push refusal (interim) | Agent host (harness policy) | GitHub App permissions | Deny rules in managed configs; App perms (Contents+PR, no Admin/Workflows) bound blast radius |
| Agent policy (Claude/OpenCode) | Agent host (managed files) | Claude admin console | Console enforces for Claude; root-owned files enforce on host |
| Egress observation | Agent host (Squid + nftables) | Cloud Logging | Proxy sees destinations; logs shipped to GCP for alerting/query |
| Misuse detection | Google Cloud (Audit + Monitoring) | — | Secret/IAM telemetry exists only in GCP; Terraform owns the config |
| Account safeguards | Google Workspace + GitHub org consoles | Runbooks | Break-glass/2FA are console actions; runbooks record them |
| Acceptance checks | Repo (`tests/agents/`) | Agent host (execution) | Checks versioned in git; executed as root on the host |

## Standard Stack

### Core

| Component | Version / Shape | Purpose | Why Standard |
|-----------|----------------|---------|--------------|
| GitHub ruleset definition (JSON file) | REST `repos/rulesets` payload shape [CITED: docs.github.com/en/rest/repos/rules] | Reviewed-but-unapplied `main` protection | Only machine-appliable artifact; `gh api` applies it unchanged at Team-plan time |
| `CODEOWNERS` | `* @hyprn-labs/<human-team>` | Human-only approval source | Ruleset `require_code_owner_review` needs a human team to mean anything [CITED: docs.github.com available-rules-for-rulesets] |
| Claude Code `managed-settings.json` | Settings-reference shape, Claude Code ≥ 2.1.282 for `strictKnownMarketplaces` enforcement semantics [CITED: code.claude.com/docs/en/managed-settings] | Org policy for Ada | Console-enforced, user/project files cannot override managed rules |
| OpenCode `agents/host/files/opencode.json` | Existing schema [VERIFIED: agents/host/files/opencode.json:1-28] | Codd policy (deny push-to-main etc.) | Already managed, root-owned, non-overridable; extend, don't replace |
| Squid (explicit forward proxy) | apt `squid` on Debian 12 host [ASSUMED] | Only-way-out egress with per-destination logs | Explicit proxy handles HTTPS via CONNECT without breaking TLS; transparent interception cannot cover HTTPS [CITED: kernel tproxy docs + squid transparent-proxy literature] |
| nftables `inet hyprn_agents` table | Existing base [VERIFIED: agents/host/files/egress.nft:1-15] | Per-user drop-direct + DNS-allow | `meta skuid` match already proven for metadata block; extend same table |
| Cloud Logging + Monitoring log-based alerts | `auditConfigs` + `google_monitoring_alert_policy` via Terraform [CITED: docs.cloud.google.com/logging/docs/alerting/log-based-alerts] | DET-01/02 detection | Documented pattern incl. the exact Secret-Manager human-access query |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| google-cloud-ops-agent (or fluent) on host | Ship Squid `access.log` to Cloud Logging with agent label | EGR-01 per-agent destination logs |
| `gh api` with owner credentials | Ruleset dry-review, App-scope checks, installation repo lists | GHE/CODD verification (owner-go, never in automation) |
| host `gh` wrapper [VERIFIED: runbooks/agents/opencode.md via agents/host/files/bin/gh reference] | Agent-identity API calls in checks | Scope/freshness assertions as the agent user |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Explicit Squid proxy | Transparent intercept (REDIRECT/TPROXY) | Transparent breaks on HTTPS without TLS interception; explicit `http_proxy`/`https_proxy` env covers TLS cleanly — use explicit [ASSUMED] |
| Squid | Tinyproxy / Dante | Squid access-log richness (user, host, bytes) is what per-agent Cloud Logging needs; tinyproxy logs less [ASSUMED] |
| Per-agent proxy ports | Single port + proxy-auth usernames | Either works; ports are simpler to attribute in nftables, auth usernames simpler in one Squid instance — planner's call [ASSUMED] |
| Classic branch protection now | Nothing (deny rules only) | Classic protection is also unavailable on private Free-plan repos [CITED: docs.github.com/en/rest/branches/branch-protection]; deny rules are the only interim control |
| Log-based alert policies | Log-based metrics + metric alerts | Direct log-based alert is fewer moving parts for two alerts; metric route useful if alert volume needs aggregation later [CITED: cloud.google.com log-based-alerts doc] |

**Installation:**
```bash
# Agent host only (owner-go provisioning step, not automated by the plan):
sudo apt-get install -y squid
# Cloud side is Terraform in infra/agents (reviewed plan, owner-go apply)
```

**Version verification:** No registry packages are introduced by this phase (apt `squid` + Terraform provider resources only — see Package Legitimacy Audit). `gh 2.102.0` and `gcloud 588.0.0` are present in this worktree for definition authoring [VERIFIED: local probe 2026-10-13].

## Package Legitimacy Audit

This phase installs no npm/PyPI/crates packages. The only new software is the OS package `squid` (Debian apt, installed during owner-go provisioning) and Terraform-managed GCP resources (no new providers — `infra/agents/` already manages the project).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| squid | Debian apt | decades | distro-wide | squid-cache.org | OK | Approved (apt, not a registry-supply-chain risk) |
| (no npm/pypi/crates) | — | — | — | — | — | None introduced |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious SUS:** none.

## Architecture Patterns

### System Architecture Diagram

```text
Ada session (herdr, user ada) ──┐
                                ├─► Squid :3128+ (per-agent port/user) ──► internet (CONNECT logged)
Codd session (user codd) ───────┘                │
                                                 └──► access.log ──► Cloud Logging (per-agent destinations)
agent users/containers ──► nftables inet hyprn_agents ──► direct 80/443 DROPPED; DNS :53 ALLOWED
                                                                                │
Secret Manager reads ──► Data Access audit log ──► log-based alert ──► email gcp-admins@hyprn.ai
IAM SetIamPolicy ──────► Admin Activity audit log ─► log-based alert ──► email gcp-admins@hyprn.ai
folder agents changes ─► log sink ──► hyprn-agents ─► same IAM alert path
GitHub push/merge to main ──► DENIED by harness policy (interim) / ruleset (later)
```

Entry points: agent shell commands, Slack permission replies, GitHub pushes, GCP API calls. Processing: policy/deny evaluation → proxy/audit observation → alerting. Decision points: deny-vs-ask-vs-allow (deny wins), observe-vs-enforce (observe in Phase 1), owner-go gates (never automated).

### Recommended Project Structure

```text
agents/policy/managed-settings.json   # NEW: Claude org policy (reviewed copy; console enforces)
agents/policy/egress-allowlist.txt    # NEW: placeholder allowlist file (enforced Phase 7, EGR-02)
agents/github/main-ruleset.json       # NEW: reviewed ruleset definition (applied at Team-plan time)
agents/github/CODEOWNERS               # NEW or repo-root CODEOWNERS (human team)
tests/agents/run.sh                   # NEW: orchestrator over host-checks.sh + new check scripts
tests/agents/checks/<domain>.sh       # NEW: per-domain checks (github/policy/egress/detect/accounts/codd)
runbooks/agents/checks-YYYY-MM-DD.md  # NEW per run: dated record (ACC-08)
runbooks/agents/claude.md             # NEW: policy change record (POL-01)
```

### Pattern 1: Reviewed-but-unapplied ruleset (GHE-01)

**What:** A JSON file matching `POST /repos/{owner}/{repo}/rulesets` with `enforcement: "active"`, branch targeting on `main`, PR + code-owner + non-fast-forward rules, and an **empty `bypass_actors` list** (nobody bypasses, incl. all Apps).
**When to use:** Whenever enforcement needs a paid plan that hasn't arrived — review the artifact now, apply it mechanically later.
**Example:**
```json
{
  "name": "main-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["refs/heads/main"], "exclude": [] } },
  "rules": [
    { "type": "non_fast_forward" },
    { "type": "deletion" },
    { "type": "required_linear_history" },
    { "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": true,
        "require_last_push_approval": true
      } }
  ],
  "bypass_actors": []
}
```
Shape per [CITED: docs.github.com/en/rest/repos/rules] (`pull_request` params incl. `dismiss_stale_reviews_on_push`, `require_code_owner_review`, `require_last_push_approval`) and rule catalog per [CITED: docs.github.com available-rules-for-rulesets] (`non_fast_forward` = block force pushes). File-level `bypass_actors: []` is the "no bypass for any App" encoding [ASSUMED — verify against the API schema at apply time; planner adds a schema-validation check task].

Free-plan scoping note: rulesets require Team/Enterprise [CITED: docs.github.com about-rulesets], and classic branch protection on private repos likewise needs a paid plan [CITED: docs.github.com/en/rest/branches/branch-protection] — so on Free with private repos **no server-side control can be applied now**, which is exactly D-01's deferral. (If either repo were public, classic protection would work on Free — but both are private product/platform repos [ASSUMED].)

### Pattern 2: Managed-settings policy with variant-tolerant deny rules (POL-01/02/04)

**What:** `managed-settings.json` in the documented org-policy shape: managed-only locks (`allowManagedPermissionRulesOnly`, `strictKnownMarketplaces`, `disableBypassPermissionsMode`) plus `permissions.deny` entries covering command-text variants.
**When to use:** All Claude Code policy for Ada.
**Example** (adapted from [CITED: code.claude.com/docs/en/settings-example]):
```json
{
  "permissions": {
    "deny": [
      "Bash(git push *main*)",
      "Bash(git push *--force*)",
      "Bash(git push *-f*)",
      "Bash(git -C * push *)",
      "Bash(gh pr merge*)",
      "Bash(gh api repos/*/branches/main/protection*)"
    ],
    "disableBypassPermissionsMode": "disable"
  },
  "allowManagedPermissionRulesOnly": true,
  "strictKnownMarketplaces": [{ "source": "github", "repo": "hyprn-labs/hyprn-agents" }],
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "network": { "allowedDomains": ["<seed allowlist>"], "allowManagedDomainsOnly": true }
  },
  "requiredMinimumVersion": "2.1.282"
}
```
Key semantics the planner must encode: rules evaluate **deny → ask → allow**, and an allow rule can never carve out of a deny [CITED: code.claude.com/docs/en/permissions]. **Bash rules match the command text as Claude writes it** — `Bash(git push *)` does NOT match `git -C . push` [CITED: code.claude.com/docs/en/settings-example] — so every refusal needs variant patterns (`git -C`, absolute paths, `sh -c` wrappers) plus a live refusal test. `strictKnownMarketplaces` is Managed-scope only [CITED: settings-reference]; an invalid value fails closed (enforced as empty allowlist) [CITED: managed-settings]. POL-01 allow/ask lists: routine worktree work allowed, risky actions asked — exact lists are planner + owner-review content, not research content.

**POL-03 evidence procedure** (must-verify per D-08): (1) console shows the marketplace list matching the file; (2) `claude doctor` / `/status` on the host shows the managed source active; (3) negative test — attempt to add a non-listed marketplace in Ada's session is blocked. All three recorded in the dated check record [ASSUMED procedure — composed from documented primitives].

### Pattern 3: Explicit-proxy egress observation (EGR-01)

**What:** Squid as an **explicit** forward proxy (`http_proxy`/`https_proxy` set for agent users and injected into their containers); nftables drops direct outbound 80/443 for agent UIDs while keeping DNS (UDP+TCP 53 to the resolver) open; Squid `access.log` (with per-agent port or auth user) shipped to Cloud Logging.
**When to use:** All agent-user and agent-container egress from Phase 1 onward.
**Extension of the existing base:**
```nft
# Existing: skuid 20000-20999, DNS allowed, metadata dropped [VERIFIED: agents/host/files/egress.nft:7-14]
# Add (observe mode): drop direct HTTP/HTTPS for agent UIDs, allow proxy port + DNS
meta skuid 20000-20999 tcp dport {80, 443} counter drop
meta skuid 20000-20999 tcp dport 3128 accept   # per-agent ports as needed
```
Per-agent attribution: distinct listen ports (`http_port 3128/3129` + ACL per port) or `proxy_auth` usernames `ada`/`codd` baked into each user's env; the access log's port/user field becomes the Cloud Logging agent label [ASSUMED design — standard Squid practice]. Containers inherit the user's proxy env so their traffic is attributed to the owning agent [ASSUMED].

**Known gotchas the plan must include:** (1) DNS stays allowed — the metadata address is also the VPC resolver [VERIFIED context: egress.nft comments lines 1-3]; (2) rootless-container packets may carry **subuid-range UIDs**, not the user's login UID — the `skuid 20000-20999` match alone can miss container traffic; either extend the match to the subordinate ranges in `/etc/subuid` or force container traffic through the proxy env and verify with a container-originated drop test [ASSUMED — standard rootless networking behavior, MUST be live-tested]; (3) wake-service traffic originates on the controller VM, not the agent host — host firewall cannot see it; cover via the wake host's own Squid/logs or VPC flow logs, flagged as an open question below.

The direct-connection drop test (success criterion 4): as `ada`, `curl --noproxy '*' https://example.com` fails while the same URL via proxy succeeds; both attempts visible (drop logged by nftables counter, success in Squid log) [ASSUMED procedure].

### Pattern 4: Audit-config + log-based alerts (DET-01/02)

**What:** Enable `DATA_READ` Data Access audit logs for `secretmanager.googleapis.com`; two Monitoring log-based alert policies with an email notification channel to `gcp-admins@hyprn.ai`.
**Queries** (documented pattern [CITED: docs.cloud.google.com/logging/docs/alerting/log-based-alerts]):
```text
# DET-01 unexpected secret read (adapt: allowlist host/wake/controller identities)
protoPayload.@type = "type.googleapis.com/google.cloud.audit.AuditLog"
protoPayload.serviceName = "secretmanager.googleapis.com"
protoPayload.methodName =~ "AccessSecretVersion$"
protoPayload.authenticationInfo.principalEmail !~ "gserviceaccount.com$"
# plus: creates/deletes/new readers via CreateSecret/DeleteSecret/SetIamPolicy on secretmanager
# DET-02 IAM change in hyprn-agents
protoPayload.methodName = "SetIamPolicy" AND resource.labels.project_id = "hyprn-agents"
```
Audit-config mechanics: Data Access logs are **disabled by default** and must be enabled per service/permission-type via the IAM policy `auditConfigs` section (`DATA_READ` covers `secretmanager.versions.access` = `AccessSecretVersion`) [CITED: cloud.google.com/logging/docs/audit/configure-data-access + secret-manager/docs/audit-logging]. Folder-level `agents` changes reach the project alert through a **log sink into `hyprn-agents`** (DET-02 second half) [ASSUMED — standard sink pattern; planner confirms sink filter]. Group-deliverability: `gcp-admins@hyprn.ai` must accept mail from Google Cloud notification channels — an owner-go console check [ASSUMED].

### Pattern 5: Owner-go checklists (SEC-01/02 + console/alert tests)

**What:** Each owner-hand step is a named checklist with a console path, expected end-state, and a record row — requested by the plan, executed by the owner, never scripted.
**Checklists:** (a) break-glass admin — Workspace Admin user, own hardware key + printed backup codes stored offline away from daily keys, no standing GCP role, use documented in `runbooks/agents/gcp.md` (extends the existing access-model section [VERIFIED: runbooks/agents/gcp.md:20-24]); (b) 2FA — org Settings → Authentication security → require 2FA (eligible on Free/Team plans [CITED: docs.github.com requiring-two-factor-authentication]); notify members first since non-2FA members lose access [CITED: same]; (c) admin-console policy match — Team Owner pastes/applies `managed-settings.json` content, check asserts console ≡ file; (d) alert live-tests — read a canary secret as an unexpected principal + make a canary IAM change, confirm both emails arrive; (e) org-wide IAM search with owner credentials (ACC-04).

### Pattern 6: `run.sh` harness over `host-checks.sh` (ACC-08)

**What:** `tests/agents/run.sh` orchestrates `host-checks.sh` (unchanged, 40 passing checks [VERIFIED: tests/agents/host-checks.sh:1-49]) plus new `tests/agents/checks/<domain>.sh` scripts; every script follows the established `check "name" "predicate"` + counted PASS/FAIL + non-zero-exit-on-failure shape; each full run appends a dated record `runbooks/agents/checks-YYYY-MM-DD.md`.
**Conventions to preserve** [VERIFIED: host-checks.sh:4-8,49]: `set -uo pipefail` (add `-e` in orchestrator with per-script failure capture so one domain's failure doesn't hide later domains), `run as root on the host`, `stat -c %U:%a` ownership assertions, tmpfs-secret permission assertions (`$name:400`), per-agent loops reading `agents/host/agents.txt` skipping comments [VERIFIED: line 47]. New checks needing agent-user context use the `run() { runuser -l "$name" -c ...; }` wrapper [VERIFIED: line 22]. GitHub-identity assertions use the host `gh` wrapper and `installation/repositories` total-count scoping [VERIFIED: lines 36,42] — extended per-repo for both repositories (D-04).

### Anti-Patterns to Avoid

- **Applying half a ruleset on Free:** don't plan `gh api PUT rulesets` tasks that fail at execution — the plan must contain definition-review tasks only, with apply gated on the Team purchase (D-01).
- **Single-pattern deny rules:** one `Bash(git push *)` is theater — command-text matching needs variants + live tests (see Pattern 2).
- **Transparent-proxy ambition:** TLS interception breaks the security model; explicit proxy + drop-direct is the design.
- **Blocking DNS with metadata:** port 53 to the resolver must stay open or all egress (incl. the proxy's) breaks.
- **Automating owner steps:** any task that scripts break-glass creation, 2FA toggles, console pastes, or owner-credential IAM searches violates standing direction — these are checklist requests, not scripts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret-misuse detection | Custom log tailers/cron greps | Cloud Audit + log-based alert policies | Retention, dedup, notification channels, and the documented human-access query already exist |
| Egress attribution | Packet-capture scripts | Squid access.log + ops-agent to Cloud Logging | Per-user/port/destination fields are native; hand-rolled sniffers miss TLS SNI and container traffic |
| Permission enforcement | Shell wrappers blocking `git push` | Managed-settings deny + OpenCode permission blocks | Wrappers are bypassable by absolute paths/flags; managed deny is evaluated before allow at the harness layer |
| Marketplace pinning | Manual plugin audits per session | `strictKnownMarketplaces` + vendored marketplace | Console/file enforced, fails closed on invalid values |
| Check orchestration | New test framework | Bash `check()` pattern from host-checks.sh | 40 passing checks already; consistency beats framework novelty |

**Key insight:** Every control in this phase is a vendor-native enforcement point (GitHub, Claude Code, Squid, GCP Audit) with the repo holding only reviewed definitions and checks. Custom enforcement code would be weaker and unreviewable by the owner.

## Common Pitfalls

### Pitfall 1: Planning an impossible ruleset apply
**What goes wrong:** Executor burns a wave on `gh api` ruleset calls that return 404/403 on the Free plan.
**Why it happens:** Ruleset APIs exist but are plan-gated; existence of docs ≠ availability.
**How to avoid:** Definition-review tasks only; a `checkpoint:human-verify` (owner-go) gates the future apply; success criterion 1 reshaped per D-01.
**Warning signs:** Plan contains `repos/rulesets` write calls without a Team-plan precondition.

### Pitfall 2: Deny-rule bypass by command variant
**What goes wrong:** Refusal tests pass for `git push origin main` but `git -C /path push` or `gh pr merge --admin` slips through.
**Why it happens:** Bash permission patterns match literal command text [CITED: settings-example].
**How to avoid:** Variant patterns per refusal + live refusal tests in both Ada's session and Codd (D-08), including `--admin`/`--force` flag variants.
**Warning signs:** Deny list shorter than ~6 git/gh patterns.

### Pitfall 3: Container egress invisible to UID match
**What goes wrong:** Drop-direct rules cover login UIDs but container traffic flows direct.
**Why it happens:** Rootless containers map to subuid ranges outside `20000-20999` [ASSUMED].
**How to avoid:** Extend nftables match to subordinate ranges and/or enforce proxy env in containers; verify with a container-originated drop test.
**Warning signs:** Drop test only run as the login user, never from inside a container.

### Pitfall 4: Audit logs assumed on
**What goes wrong:** Alerts never fire because Data Access logs were never enabled.
**Why it happens:** Data Access audit logs are disabled by default [CITED].
**How to avoid:** Explicit `auditConfigs` Terraform + a check asserting the config + the canary-read live test (D-08).
**Warning signs:** DET plan has alert policies but no audit-config change.

### Pitfall 5: Alert emails silently dropped
**What goes wrong:** Policies fire; nobody receives mail.
**Why it happens:** Group address rejects Google-notification mail or external-member settings block it.
**How to avoid:** Owner-go deliverability check + live canary alerts as phase proof (success criterion 5).
**Warning signs:** No end-to-end alert test task in the plan.

### Pitfall 6: Stale "platform-only" scope lines
**What goes wrong:** Checks assert Codd sees 1 repo; both-repo reality fails the check.
**Why it happens:** Merged lines predate the 2026-10-13 both-repo verification (D-03).
**How to avoid:** CODD-01 groundwork corrects REQUIREMENTS, spec §2, README, PROJECT.md, `runbooks/agents/github.md` repo-access section [VERIFIED stale: github.md:9,32], and the host-check App-scope assertion [VERIFIED stale: host-checks.sh:36]; new checks assert both repos per D-04.
**Warning signs:** Any remaining "platform-only" string in scope docs.

## Code Examples

### Ruleset apply (Team-plan time, NOT this phase)

```bash
# Source shape: POST /repos/{owner}/{repo}/rulesets [CITED: docs.github.com/en/rest/repos/rules]
# Owner-go only, after Team purchase. Phase 1 reviews the file; this command is recorded, not run.
GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api repos/hyprn-labs/hyprn-platform/rulesets \
  --input agents/github/main-ruleset.json
```

### App-scope assertion (both repos, agent identity)

```bash
# Extension of the host-check pattern [VERIFIED: host-checks.sh:36,42]
run 'gh api installation/repositories --jq .repositories[].full_name' | sort
# expect: hyprn-labs/hyprn-mvp + hyprn-labs/hyprn-platform (D-04: per-repo assertion)
```

### Audit-config Terraform sketch

```hcl
# Enables DATA_READ for Secret Manager; exact resource: google_project_iam_audit_config [ASSUMED name]
resource "google_project_iam_audit_config" "secretmanager_data_read" {
  project = "hyprn-agents"
  service = "secretmanager.googleapis.com"
  audit_log_config { log_type = "DATA_READ" }
}
```

### Squid per-agent logging sketch

```text
# /etc/squid/conf.d/hyprn.conf [ASSUMED — planner confirms paths on host]
http_port 3128   # ada
http_port 3129   # codd
acl ada_port localport 3128
acl codd_port localport 3129
access_log /var/log/squid/access.log squid
# ops-agent ships access.log to Cloud Logging; localport becomes the agent label
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Machine account + 90-day token (ADR-0004) | Per-agent GitHub App + 1h tokens (ADR-0005) | 2026-10-13 | No long-lived GitHub credentials; scope checks use installation repo lists |
| OpenCode on Ada | OpenCode on Codd only; Ada is Claude Code | 2026-10-13 [VERIFIED: opencode.md:63-64] | Policy split: managed-settings.json (Ada) vs opencode.json (Codd) |
| Codd platform-only | Codd on platform + mvp | 2026-10-13 (commit `30ee1b1`) | All scope assertions per-repo over both repos |
| Classic branch protection as interim | Deny rules as interim; ruleset definition reviewed | This phase (D-01) | No server-side control exists on Free/private — plan accordingly |

**Deprecated/outdated:**
- `agents/host/agents.txt` + `wake.json` as agent declarations — replaced by `fleet.yaml` in Phase 6, not this phase; checks keep reading `agents.txt` for now.
- Stale "platform-only" lines (REQUIREMENTS CODD-01, spec §2, README, PROJECT.md, github.md, host-checks.sh:36) — corrected as CODD-01 groundwork in this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Both repos are private (so no Free-plan protection applies) | Ruleset pattern | If either is public, classic protection could apply now — planner verifies visibility first |
| A2 | `bypass_actors: []` is valid and means no-bypass | Ruleset example | Apply-time schema check needed; planner adds validation task |
| A3 | Squid via apt on Debian 12; explicit proxy design | EGR-01 | Host OS/config paths may differ — planner confirms on host before writing tasks |
| A4 | Rootless containers use subuid ranges outside skuid match | Pitfall 3 | If wrong, the extra match rules are harmless but the container drop test still required |
| A5 | Per-agent ports/auth-user attribution scheme | EGR-01 | Planner picks ports-vs-auth with owner; either satisfies per-agent logs |
| A6 | Wake-service traffic needs separate observation path | EGR-01 / Open Q | If wake runs on the agent host, host rules cover it — planner confirms placement |
| A7 | `google_project_iam_audit_config` resource shape; folder sink pattern | DET | Terraform plan review catches drift; owner-go apply |
| A8 | POL-03 evidence procedure (console + doctor/status + negative test) | POL-03 | May need adjustment to actual CLI output; check tasks assert loosely |
| A9 | Group mail deliverability needs an owner check | DET | If already deliverable, the check is a no-op pass |

## Open Questions

1. **Wake-service placement and traffic path**
   - What we know: D-05 scopes wake-service traffic into observation; ADR-0002 puts the wake service on the always-on controller (`hyprn-agents-wake-01`).
   - What's unclear: whether any wake traffic traverses the agent host.
   - Recommendation: planner adds a discovery task (confirm placement first), then host rules or controller-side/VPC-flow-log observation accordingly. Must not silently drop the scope.

2. **Squid log shipping mechanism on the host**
   - What we know: ops-agent is the standard shipper to Cloud Logging.
   - What's unclear: whether ops-agent is already installed on the agent host.
   - Recommendation: planner checks during provisioning discovery; fallback is rsyslog/fluent-bit.

3. **Seed sandbox network allowlist for POL-02**
   - What we know: shape (`allowedDomains` + `allowManagedDomainsOnly`); routine worktree work must run without prompts (success criterion 2).
   - What's unclear: the actual domain set Ada needs.
   - Recommendation: seed from observed hosts (github.com, registry.npmjs.org, anthropic endpoints), refine by trial; over-narrow breaks criterion 2, over-broad weakens POL-02.

4. **Claude Code version on host vs `requiredMinimumVersion`**
   - What we know: `strictKnownMarketplaces` enforcement semantics need ≥ 2.1.282 [CITED].
   - What's unclear: installed Claude Code version on the host.
   - Recommendation: planner adds a version-assert task; pin `requiredMinimumVersion` accordingly.

## Environment Availability

Research is read-only; execution targets the agent host and GCP consoles. Local worktree probes (2026-10-13):

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `gh` (host wrapper) | Definition authoring, scope checks | ✓ (worktree) | 2.102.0 | — |
| `gcloud` | Audit/alert Terraform authoring | ✓ (worktree) | 588.0.0 | — |
| Agent host shell (root) | Squid/nftables/checks execution | ✗ (not from here) | — | Executor runs on host via IAP SSH (owner-go) |
| Squid / nftables | EGR-01 | ✗ (local) | — | Installed on agent host at provisioning |
| GitHub org admin | Ruleset review, 2FA, App scope | owner-go | — | Checklist, never automated |
| Claude admin console | Policy match (POL-01) | owner-go | — | Checklist, never automated |
| `gcp-admins@hyprn.ai` deliverability | DET-01/02 proof | unknown | — | Owner-go check + canary alerts |

**Missing dependencies with no fallback:** none for research; all owner-go items are checklist-gated in the plan, not blockers.

## Validation Architecture

Test framework: **Bash checks** — no unit-test framework applies. Existing: `tests/agents/host-checks.sh` (40 passing, root-on-host, counted PASS/FAIL, non-zero exit). New: `tests/agents/checks/<domain>.sh` in the same shape + `tests/agents/run.sh` orchestrator. Quick run: `sudo tests/agents/run.sh` (full suite is the quick suite; each domain script runnable standalone).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| GHE-01 | Ruleset definition valid + reviewed; NOT applied | static review + schema check | `python3 -m json.tool agents/github/main-ruleset.json` + reviewer sign-off | ❌ Wave 0 (new file) |
| GHE-03 | App cannot merge/push to `main` (deny-rule interim) | live refusal (owner-go session) | `run.sh: checks/github.sh` (attempted push to `main` refused; App approval doesn't satisfy — asserted post-Team-plan) | ❌ Wave 0 |
| POL-01 | Console policy ≡ `managed-settings.json`; changes recorded | diff + owner-go console check | `diff` console export vs file; `runbooks/agents/claude.md` row present | ❌ Wave 0 (file + runbook) |
| POL-02 | Off-allowlist host fails inside sandbox | live negative test | Ada session requests unlisted host → refused | ❌ Wave 0 |
| POL-03 | Only `hyprn-agents` marketplace accepted | console + doctor/status + negative test | `checks/policy.sh` (3-part evidence) | ❌ Wave 0 |
| POL-04 | Merge/push-to-main/force-push refused every repo | live refusal per repo | Ada session + Codd refusal attempts, both repos | ❌ Wave 0 |
| EGR-01 | Per-agent destinations in Cloud Logging; direct dropped | log query + drop test | `checks/egress.sh` (drop as user + from container; log-flow query) | ❌ Wave 0 |
| DET-01 | Canary secret read → email to gcp-admins | live alert test (owner-go) | canary read + inbox assertion | ❌ Wave 0 |
| DET-02 | Canary IAM change → email; folder sink exists | live alert test + config assert | canary change + sink `gcloud` describe | ❌ Wave 0 |
| SEC-01 | Break-glass exists, documented, no standing role | owner-go checklist + IAM assert | checklist sign-off; `get-iam-policy` shows no standing grant | ❌ Wave 0 |
| SEC-02 | 2FA required on org | owner-go console check | org auth-security setting + member 2FA status | ❌ Wave 0 |
| ACC-01/02 | Slack relay + sender allowlist | live session test | risky action → owner-only approval; non-listed sender ignored | ❌ Wave 0 |
| ACC-03 | Session-level refusals | live refusal | merge/push/force/bypass refused in Ada session | ❌ Wave 0 |
| ACC-04 | Org-wide IAM = declared roles only | owner-credential search | `gcloud organizations get-iam-policy` review | ❌ Wave 0 |
| ACC-05 | Host clean: no user creds/keys/staging/prod | host check (extends existing) | existing key-file/service checks + secret-scan | ✅ `host-checks.sh` covers keys; extend for staging/prod |
| ACC-06 | Wake limits (get/start/stop only; no Slack while host runs; disk persists) | config + live asserts | IAM binding review + wake behavior checks | ❌ Wave 0 |
| ACC-08 | `run.sh` passes + dated record written | harness self-check | `run.sh` exit 0 + `runbooks/agents/checks-<date>.md` exists | ❌ Wave 0 |
| CODD-01 | App on both repos; tokens; user; managed config; scope corrections | host + API checks | installation repo list = 2 repos; `opencode.json` ownership/content; stale-line corrections merged | Partial (extend `host-checks.sh:36`) |

### Sampling Rate
- **Per task commit:** affected domain script standalone (`sudo tests/agents/checks/<domain>.sh`)
- **Per wave merge:** full `sudo tests/agents/run.sh`
- **Phase gate:** full suite green + dated record kept before verify-work

### Wave 0 Gaps
- [ ] `tests/agents/run.sh` — orchestrator + dated-record writer
- [ ] `tests/agents/checks/{github,policy,egress,detect,accounts,codd}.sh` — per-domain checks
- [ ] `agents/policy/managed-settings.json` — policy definition under check
- [ ] `agents/policy/egress-allowlist.txt` — placeholder (enforced Phase 7)
- [ ] `agents/github/main-ruleset.json` — reviewed definition under check
- [ ] `CODEOWNERS` (human team) — required for code-owner rule meaning
- [ ] `runbooks/agents/claude.md` — policy change record

## Security Domain

`security_enforcement: true`, ASVS L1. This phase IS the security baseline; the whole phase is threat-model work.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | GitHub Apps (1h tokens, ADR-0005); break-glass key + offline backups (SEC-01) |
| V3 Session Management | partial | 1h installation-token rotation via root broker; Slack Socket Mode outbound-only |
| V4 Access Control | yes | Ruleset (later) + deny rules (now); Linux-user boundary; per-agent tmpfs secrets `400` |
| V5 Input Validation | yes | Slack sender allowlist (ACC-02); untrusted-content discipline (spec §7) |
| V6 Cryptography | yes | No hand-rolled crypto: App JWT via broker, Secret Manager storage, TLS via proxy CONNECT |
| V8 Data Protection | yes | Secrets never in git; per-agent secret isolation; Zen free-tier data-use boundary for Codd |
| V9 Communications | yes | Egress observation (EGR-01); IAP-only SSH; no public IPs |
| V10 Malicious Code | partial | `strictKnownMarketplaces` + vendored marketplace; pinned herdr hooks |
| V14 Configuration | yes | Managed configs root-owned; `run.sh` drift checks; Terraform-reviewed cloud changes |

### Threat Model Notes (security baseline)

Attack surfaces in scope with primary mitigations:

| Surface | Threat (STRIDE) | Mitigation in this phase |
|---------|-----------------|--------------------------|
| Agent shell as `ada`/`codd` | Elevation to another agent's home/secrets/tokens (EoP, InfoDisc) | Linux-user boundary + rootless Docker + private homes + per-agent tmpfs secrets; proven by host checks |
| Slack channel server as agent user | Spoofed owner approval; non-owner instruction injection (Spoofing, Tampering) | Sender allowlist + owner-only permission replies (ACC-01/02); untrusted-input boundary |
| Token broker (root, host) | Private-key exfiltration; token replay beyond 1h (InfoDisc, EoP) | Key in Secret Manager, JWT in memory only, tokens on tmpfs `400`, ≤35min freshness checks |
| Wake service | Unauthorized host start/stop; Slack socket while host runs (EoP, Repudiation) | Wake identity limited to get/start/stop (ACC-06); host keeps disk; audit-logged |
| `main` branch (pre-ruleset) | Agent push/merge bypassing review (Tampering) | Deny rules interim (POL-04 + opencode.json); ruleset definition ready; App perms exclude Admin/Workflows |
| Egress path | Data exfiltration to unobserved hosts; metadata-identity theft (InfoDisc, EoP) | Squid-only egress + drop-direct + metadata block; per-agent Cloud Logging |
| Secret Manager / IAM | Silent grant expansion; secret reads by unexpected principals (EoP, InfoDisc) | DET-01/02 alerts to gcp-admins; org-wide IAM search (ACC-04) |
| Codd free-tier model | Prompts training Meta (InfoDisc by design) | Owner-accepted prototyping terms; no secrets/staging/prod in Codd's reach; binding moves at company-terms time |

Residual risks carried forward (not solved here): no server-side `main` protection until Team plan (accepted, D-01); sandbox covers shell only so the user boundary does the rest (ADR-0001 §4); seat-limit pauses; channels research-preview churn.

## Sources

### Primary (HIGH confidence)
- In-repo reads this session: `01-CONTEXT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `config.json`, `agent-fleet.md` (§1–3, §13), ADR-0001, ADR-0005, `runbooks/agents/{opencode,gcp,github}.md`, `tests/agents/{host-checks.sh,README.md}`, `agents/{host/files/egress.nft,host/files/opencode.json,policy/README.md}`; local probes (`gh 2.102.0`, `gcloud 588.0.0`)

### Secondary (MEDIUM confidence)
- [CITED: docs.github.com/en/rest/repos/rules] — ruleset REST payload, `pull_request` parameters (`dismiss_stale_reviews_on_push`, `require_code_owner_review`, `require_last_push_approval`)
- [CITED: docs.github.com/.../available-rules-for-rulesets] — `non_fast_forward` (block force push), code-owner approvals, review dismissal
- [CITED: docs.github.com/.../about-rulesets] — rulesets require Team/Enterprise
- [CITED: docs.github.com/en/rest/branches/branch-protection] — classic protection on Free covers public repos only
- [CITED: docs.github.com/.../requiring-two-factor-authentication-in-your-organization] — 2FA requirement available on Free/Team; procedure + removal warning
- [CITED: code.claude.com/docs/en/settings-example] — managed-settings example shape; command-text matching caveat
- [CITED: code.claude.com/docs/en/managed-settings] — `strictKnownMarketplaces` semantics, invalid-fails-closed, version gates (2.1.277/282)
- [CITED: code.claude.com/docs/en/permissions] — deny → ask → allow precedence
- [CITED: docs.cloud.google.com/logging/docs/alerting/log-based-alerts] — log-based alerts incl. Secret-Manager human-access query pattern
- [CITED: docs.cloud.google.com/secret-manager/docs/audit-logging] — `AccessSecretVersion` = DATA_READ
- [CITED: docs.cloud.google.com/logging/docs/audit/configure-data-access] — Data Access logs disabled by default; `auditConfigs` mechanics

### Tertiary (LOW confidence)
- Transparent-proxy/TPROXY literature (squid/shorewall/kernel docs) — used only to justify explicit-proxy choice
- Squid multi-port/auth attribution, subuid/nftables interaction, Terraform resource names, ops-agent presence — all tagged [ASSUMED] inline with live-test mitigations

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — vendor shapes verified against official docs; host-side paths need on-host confirmation
- Architecture: MEDIUM — patterns composed from documented primitives + in-repo conventions; wake-scope placement open
- Pitfalls: HIGH — each pitfall traces to a cited default (plan-gating, text-matching, default-off audit logs) or a verified in-repo staleness

**Research date:** 2026-10-13
**Valid until:** 2026-11-12 (stable domain; re-check Claude Code version gates if host upgrades)
