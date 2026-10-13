# Phase 1: Security baseline - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 13 new/modified (7 Wave-0 new files + Terraform/logging + Squid/egress + runbooks + CODD-01 corrections)
**Analogs found:** 10 / 13 (3 greenfield-with-no-in-repo-analog noted below)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tests/agents/run.sh` (NEW) | test harness / orchestrator | batch (runs scripts, aggregates PASS/FAIL) | `tests/agents/host-checks.sh` | exact (same dir, same conventions) |
| `tests/agents/checks/<domain>.sh` (NEW: github, policy, egress, detect, accounts, codd) | test scripts | batch / request-response (assert host + API state) | `tests/agents/host-checks.sh` | exact |
| `agents/policy/managed-settings.json` (NEW) | config (org policy) | file-I/O (reviewed copy; console enforces) | `agents/host/files/opencode.json` | role-match (managed policy JSON, deny-shape) |
| `agents/policy/egress-allowlist.txt` (NEW, placeholder) | config (allowlist) | file-I/O | `agents/host/agents.txt` | role-match (line-oriented data file read by scripts) |
| `agents/github/main-ruleset.json` (NEW) | config (API payload definition) | request-response (reviewed; applied via `gh api` at Team-plan time) | none in repo (shape from RESEARCH.md §Pattern 1) | no analog |
| `CODEOWNERS` (NEW, repo-root or agents/github/) | config | file-I/O | none in repo | no analog |
| `infra/agents/<detect|alerts>.tf` (NEW: audit config + alert policies + notification channel + sink) | config (Terraform) | event-driven (log → alert → email) | `infra/agents/secrets.tf` + `infra/agents/iam.tf` | role-match |
| Squid conf + `agents/host/files/egress.nft` extension (MODIFY) | config (host firewall/proxy) | streaming (egress path) | `agents/host/files/egress.nft` | exact |
| `agents/host/files/hyprn-agents-egress.service` extension (MODIFY) | config (systemd unit) | batch (oneshot nft load) | `agents/host/files/hyprn-agents-egress.service` + `hyprn-agent-secrets@.service` | exact |
| `runbooks/agents/claude.md` (NEW: policy change record) | docs/runbook | file-I/O | `runbooks/agents/github.md` | role-match |
| `runbooks/agents/checks-YYYY-MM-DD.md` (NEW per run) | docs/record | batch output | `runbooks/agents/opencode.md` (verification-record style) | partial |
| `tests/agents/host-checks.sh:36` (MODIFY: both-repo scope) | test | request-response | self (same file, lines 36, 42) | exact |
| CODD-01 stale-line corrections (MODIFY: REQUIREMENTS, spec §2, README, PROJECT.md, `runbooks/agents/github.md`) | docs | file-I/O | `runbooks/agents/github.md` repo-access section | role-match |

## Pattern Assignments

### `tests/agents/run.sh` (test harness, batch)

**Analog:** `tests/agents/host-checks.sh` (lines 1-8, 49)

**Shebang + strict mode + path resolution** (lines 1-6):
```bash
#!/usr/bin/env bash
# Isolation checks on the agent host (ADR-0001 confirmation). Run as root on
# the host; exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
AGENTS="$HERE/../../agents/host/agents.txt"
```

**Orchestrator shape to copy:** `set -euo pipefail` in the orchestrator (host-checks uses `set -uo pipefail` line 4 — orchestrator adds `-e` with per-script failure capture so one domain's failure doesn't hide later domains, per RESEARCH.md Pattern 6); call `host-checks.sh` unchanged first, then each `checks/<domain>.sh`; aggregate non-zero exits; append dated record to `runbooks/agents/checks-YYYY-MM-DD.md` (ACC-08). Run as root on the host: `sudo tests/agents/run.sh`; each domain script runnable standalone.

**Exit convention** (line 49):
```bash
exit $fail
```

---

### `tests/agents/checks/<domain>.sh` (test scripts, batch)

**Analog:** `tests/agents/host-checks.sh` (lines 8, 22, 36, 42, 47)

**Core `check()` pattern** (line 8 — copy verbatim into every domain script):
```bash
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
```

**Agent-user context wrapper** (line 22):
```bash
run() { runuser -l "$name" -c "$1" </dev/null; }
```

**Per-agent loop over agents.txt, skipping comments** (lines 21, 47):
```bash
while read -r name uid harness _; do
  ...
done < <(grep -vE '^\s*(#|$)' "$AGENTS")
```

**GitHub-identity assertions via host `gh` wrapper** (lines 36, 42 — extend per-repo for both repos per D-04):
```bash
check "$name: GitHub App limited to hyprn-platform" "run 'gh api installation/repositories --jq .repositories[].full_name' | grep -qx hyprn-labs/hyprn-platform && [ \"\$(run 'gh api installation/repositories --jq .total_count')\" = 1 ]"
check "$name: gh works with the App token" "run 'gh api installation/repositories --jq .total_count' | grep -qE '^[1-9]'"
```
New `checks/github.sh` asserts `hyprn-labs/hyprn-mvp` + `hyprn-labs/hyprn-platform` (sorted, total 2). Ownership assertions use `stat -c %U:%a` (lines 16, 18, 38-39); tmpfs-secret permission assertions use `$name:400` (lines 38-39).

---

### `agents/policy/managed-settings.json` (config, file-I/O)

**Analog:** `agents/host/files/opencode.json` (lines 1-28, git-tracked)

**File shape to copy:** managed, root-owned JSON policy, `644`, non-overridable. Deny-first `bash` block with variant-tolerant patterns (lines 13-26):
```json
"bash": {
  "*": "allow",
  "git push * main": "deny",
  "git push * main *": "deny",
  "git push *:main*": "deny",
  "git push *+*": "deny",
  "git push *--force*": "deny",
  "git push -f*": "deny",
  "git push * -f": "deny",
  "git push * -f *": "deny",
  "gh pr merge*": "deny",
  "gh api *": "ask",
  "git config --global*": "deny"
}
```

**Ownership assertion pattern** (mirrors `host-checks.sh:18`):
```bash
[ "$(stat -c %U:%a /etc/opencode/opencode.json)" = root:644 ] && jq -e '.enabled_providers == ["opencode"]' /etc/opencode/opencode.json
```
New `checks/policy.sh` asserts managed-settings file ownership/content the same way (`jq -e` on `strictKnownMarketplaces`, deny list, `disableBypassPermissionsMode`). Full managed-settings shape (locks, sandbox allowlist, marketplace pin) comes from RESEARCH.md Pattern 2 — opencode.json is the in-repo analog for the deny-list idiom only.

---

### `agents/policy/egress-allowlist.txt` (config, file-I/O)

**Analog:** `agents/host/agents.txt` (git-tracked) + `agents/policy/README.md` (git-tracked)

**Line-file convention** (agents.txt header):
```text
# name  uid    harness   github-app        app-id   installation-id  bot-user-id  display name
# One line per agent; UIDs 20000-20999 are agent users; the GitHub App is per agent (ADR-0005).
ada     20001  claude    ada-agent-hyprn   5299141  170941397        341930344    Ada (AI agent)
```
Copy: `#`-comment header documenting format, whitespace-separated rows, consumed by scripts via `grep -vE '^\s*(#|$)'`. Phase 1 content is a seeded placeholder (enforced Phase 7/EGR-02); README already reserves the name: "`egress-allowlist.txt` — the domains the egress proxy allows, built from observed traffic and enforced in milestone M3" (`agents/policy/README.md:6`).

---

### `infra/agents/<detect|alerts>.tf` (config, event-driven)

**Analog:** `infra/agents/secrets.tf` (lines 15-32, 34-42) + `infra/agents/iam.tf` (lines 9-18) + `infra/agents/variables.tf` (project/region defaults)

**Resource + label + per-item IAM idiom** (secrets.tf:15-32):
```hcl
resource "google_secret_manager_secret" "agent_slack" {
  for_each  = local.agent_slack_secrets
  secret_id = each.key

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    component  = "agents"
    agent      = each.value
    managed_by = "terraform"
  }
}
```

**Least-privilege grant idiom** (iam.tf:9-18 — copy the `for_each = toset([...])` shape):
```hcl
resource "google_project_iam_member" "host" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.host.email}"
}
```

**Conventions to preserve:** `var.project_id` default `"hyprn-agents"`, `var.region` replication location, `managed_by = "terraform"` labels, `var.admins_group` default `"gcp-admins@hyprn.ai"` for the notification channel email. New resources (`google_project_iam_audit_config` DATA_READ for Secret Manager, two `google_monitoring_alert_policy`, notification channel, folder log sink) have no in-repo analog — Terraform sketch and alert queries come from RESEARCH.md Patterns 4 / Code Examples. Provider/backend pinned in `infra/agents/providers.tf` + `versions.tf` (google `~> 8.6`, GCS backend `hyprn-agents-tfstate`); no new providers.

---

### Egress extension: `egress.nft` + Squid conf (config, streaming)

**Analog:** `agents/host/files/egress.nft` (lines 1-15, git-tracked) + `agents/host/files/hyprn-agents-egress.service` (git-tracked)

**Existing table + DNS-allow idiom to extend** (egress.nft:4-14):
```nft
table inet hyprn_agents {
  chain output {
    type filter hook output priority filter; policy accept;
    meta skuid 20000-20999 ip daddr 169.254.169.254 udp dport 53 accept
    meta skuid 20000-20999 ip daddr 169.254.169.254 tcp dport 53 accept
    meta skuid 20000-20999 ip daddr 169.254.169.254 counter reject
    meta skuid 20000-20999 ip6 daddr fd20:ce::254 counter reject
  }
}
```
Copy: `meta skuid 20000-20999` match, DNS-53-accept-before-drop ordering (file header comment lines 1-3 documents why: same address is the VPC resolver). Observe-mode additions (drop direct 80/443, allow proxy port) per RESEARCH.md Pattern 3 — including the subuid-range gotcha and container-originated drop test.

**Unit wrapper** (hyprn-agents-egress.service:1-13):
```ini
[Unit]
Description=hyprn agents: block metadata server for agent users
After=nftables.service
Before=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/hyprn-agents/egress.nft
ExecStop=/usr/sbin/nft delete table inet hyprn_agents
```
Squid ships via apt on the host (no repo analog); per-agent attribution (ports 3128/3129 or auth users) and ops-agent log shipping per RESEARCH.md Pattern 3 + Squid sketch.

**Templated-unit idiom** (for any per-agent proxy/auth units), from `hyprn-agent-secrets@.service` (git-tracked, lines 6-12):
```ini
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/libexec/hyprn-agent-secrets %i
# The GitHub App token lives in the same tmpfs folder: mint it whenever secrets are (re)loaded.
ExecStartPost=-/usr/local/libexec/hyprn-agent-github-token %i
ExecStopPost=/bin/rm -rf /run/hyprn-agents/secrets/%i
```

---

### `runbooks/agents/claude.md` + dated `checks-*.md` records (docs)

**Analog:** `runbooks/agents/github.md` (git-tracked; owner-command + `GH_CONFIG_DIR` idiom) + `runbooks/agents/opencode.md` (verification-record style)

**Owner-command record idiom** (github.md:14):
```bash
GH_CONFIG_DIR="$HOME/.config/gh-hyprn" gh api orgs/hyprn-labs/installations --jq '.installations[] | "\(.app_slug) app=\(.app_id) installation=\(.id)"'
```
Copy: console path → owner command → expected end-state → record row. `claude.md` records each POL-01 console apply (console ≡ `managed-settings.json` diff + date); `checks-YYYY-MM-DD.md` records each full `run.sh` run (ACC-08). Never automate owner-hand steps (D-08) — checklists only.

---

### CODD-01 groundwork corrections (docs + one test line)

**Analog:** `runbooks/agents/github.md` repo-access section (lines 9, 32 — flagged stale in RESEARCH.md Pitfall 6) + `tests/agents/host-checks.sh:36`

Correct to both-repo scope: REQUIREMENTS CODD-01, spec §2 GitHub row, README, PROJECT.md, `runbooks/agents/github.md:9,32`, and `host-checks.sh:36` (installation repo list = `hyprn-labs/hyprn-mvp` + `hyprn-labs/hyprn-platform`). `tests/agents/README.md` (git-tracked, 3 lines) is the one-paragraph-per-file doc idiom — update its `host-checks.sh` summary line for the both-repo assertion.

---

## Shared Patterns

### Shell-script test style
**Source:** `tests/agents/host-checks.sh:1-8,49` (git-tracked)
**Apply to:** `run.sh` + all `checks/<domain>.sh`
```bash
#!/usr/bin/env bash
set -uo pipefail   # orchestrator adds -e with per-script failure capture
HERE="$(cd "$(dirname "$0")" && pwd)"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
# ...
exit $fail
```
Counted PASS/FAIL, non-zero exit on failure, root-on-host, `runuser -l` for agent context (line 22), `stat -c %U:%a` ownership assertions, `$name:400` tmpfs-secret assertions.

### Managed-policy file shape
**Source:** `agents/host/files/opencode.json:8-27` (git-tracked)
**Apply to:** `managed-settings.json`, OpenCode deny extensions
```json
"bash": { "*": "allow", "git push * main": "deny", "gh pr merge*": "deny", "gh api *": "ask" }
```
Deny-first, variant-tolerant Bash patterns (command-text matching — one pattern is theater; RESEARCH.md Pattern 2 lists the ~6+ git/gh variants + live refusal tests in both Ada's session and Codd).

### Terraform conventions
**Source:** `infra/agents/secrets.tf`, `iam.tf`, `variables.tf`, `providers.tf`/`versions.tf` (all git-tracked)
**Apply to:** new detect/alerts Terraform
HCL with `for_each` over sets, `var.project_id`/`var.region`, `managed_by = "terraform"` labels, per-secret/per-role least-privilege grants, secrets values never in git/Terraform (secrets.tf:1-4 comment), reviewed plan + owner-go apply.

### nftables + unit conventions
**Source:** `agents/host/files/egress.nft`, `hyprn-agents-egress.service` (both git-tracked)
**Apply to:** egress observation work
`table inet hyprn_agents`, `meta skuid` match, DNS-allow-before-drop, `Type=oneshot RemainAfterExit=yes`, `nft -f` load / `nft delete table` unload. Host owns rendered runtime; Terraform roots own cloud resources; neither rewrites the other (CONTEXT.md Established Patterns).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `agents/github/main-ruleset.json` | config (API payload) | request-response | No JSON API-payload definitions exist in repo; planner uses RESEARCH.md Pattern 1 (ruleset example, `bypass_actors: []`, schema-validation task) |
| `CODEOWNERS` | config | file-I/O | No CODEOWNERS in repo; standard `* @hyprn-labs/<human-team>` shape per RESEARCH.md Standard Stack |
| Squid `conf.d` + ops-agent logging config | config (proxy/log shipping) | streaming | No Squid/ops-agent configs in repo; planner uses RESEARCH.md Pattern 3 + Squid sketch, confirms paths on host |

## Metadata

**Analog search scope:** `tests/agents/`, `agents/host/files/`, `agents/host/agents.txt`, `agents/policy/`, `infra/agents/*.tf`, `runbooks/agents/`, `conventions/`
**Files scanned:** ~25 (all git-tracked analogs verified via `git ls-files`)
**Pattern extraction date:** 2026-10-13
