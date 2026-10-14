# Phase 7: Hardening and acceptance - Research

**Researched:** 2026-10-14
**Domain:** Squid egress enforcement + nftables + Bash acceptance harness
**Confidence:** HIGH

## Summary

Phase 7 flips the existing observe-mode egress stack (Squid forward proxy + nftables drop-direct + `tests/agents/run.sh`) to enforce mode against a completed domain allowlist, without breaking Ada/Boole/Codd routine work, and proves it with one final aggregate run plus kept dated record. No new infrastructure, no new check domains, no new external packages: the work is three reviewed-config edits (allowlist file, Squid enforce ACLs, nftables unchanged), one rollback procedure, one drill, and enforcement-on assertions appended to the existing harness.

**Primary recommendation:** Complete `egress-allowlist.txt` from declared destinations now (observe mode never ran live, so there is no observed traffic to mine), document the first-live-observation update procedure, implement enforcement as generated `dstdomain` ACLs + default-deny in Squid with a one-command observe rollback, and gate the flip plus final run behind the owner-go checkpoint.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- EGR-02 allowlist (`agents/policy/egress-allowlist.txt`, placeholder from Phase 1) is completed from observed traffic logs plus declared loop/tool destinations. No live traffic exists yet (observe mode never ran live) — the file ships with declared destinations + documented update procedure on first live observation; enforcement logic must handle empty-observed gracefully (fail-closed on unknown, never fail-open).
- Breaking-work protection: enforcement ships with a per-agent drill (Ada/Codd/Boole representative destinations) provable by dry-run/static; live proof gated.
- ACC-10: the full `run.sh` pass is the aggregate of all phase checks; this phase adds only the enforcement-on assertions + the kept dated record. No new check domains.
- The kept record is the final acceptance artifact alongside per-phase records.
- Switching proxy observe→enforce is a host provisioning change needing owner-go apply. Plans deliver reviewed config + rollback procedure (one-command revert to observe mode); the flip itself is an owner checkpoint.

### Agent's Discretion
All Phase 7 answers at agent discretion under the autonomous-run direction.

### Deferred Ideas (OUT OF SCOPE)
- Live traffic observation period (starts at first live apply).
- Post-acceptance tuning of the allowlist.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EGR-02 | Proxy enforces domain allowlist reviewed in `agents/policy/egress-allowlist.txt`, built from observed traffic; other domains refused + logged | Allowlist completion table + Squid enforce pattern + update procedure below |
| ACC-10 | Full check run passes with allowlist enforced; dated record kept | Final aggregate run shape + enforcement-on assertions; `run.sh` already appends `runbooks/agents/checks-<DATE>.md` [VERIFIED: tests/agents/run.sh:14,50-59] |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Egress enforcement (allow/deny per domain) | API/Backend (host proxy) | — | Squid is the only way out; nftables drop-direct already forces traffic through it [VERIFIED: agents/host/files/egress.nft:29-31] |
| Per-agent attribution + logging | Host (Squid logformat `%lp`, Cloud Logging ship) | — | `%lp` listen-port label is the agent identifier [VERIFIED: agents/host/files/squid-hyprn.conf:32-34] |
| Acceptance proof | Host (tests/agents/*.sh, run as root on host) | — | Checks assert live nftables/proxy state; static subset runs anywhere |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Squid forward proxy | host apt (already provisioned) | Domain allow/deny + per-agent logging | Already the fleet's only-egress mechanism per spec §13; enforcement is a config change, not a new component |
| nftables (`inet hyprn_agents` table) | host nft | Force agent UIDs + container subuid ranges through proxy; DNS allowed, direct 80/443 dropped | Already deployed in observe mode [VERIFIED: agents/host/files/egress.nft:16-33] |
| Bash acceptance harness (`tests/agents/run.sh` + `checks/*.sh`) | n/a (repo scripts) | Aggregate gate; each phase appends checks | ACC-08 contract: host-checks first, then every executable `checks/*.sh`, dated record appended [VERIFIED: tests/agents/run.sh:38-62] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `agents/fleet-render` + `agents/fleet-validate` | repo scripts | Derive per-agent proxy ports / check loops from `fleet.yaml` | Enforcement config and checks must stay registry-driven (ada 3128, codd 3129; Boole port added by fleet change) |

No new packages. No `npm/pip/cargo` installs. **Package Legitimacy Audit: not applicable** (no external packages installed; Squid/nftables are host apt packages already provisioned).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Squid `dstdomain` ACLs | nftables set-based domain filtering | nftables cannot do DNS-name policy cleanly; Squid sees CONNECT hostnames — keep enforcement in Squid |
| Squid enforce | Per-container `ALLOWED_HOSTS` env only (runner.sh pattern) | `ALLOWED_HOSTS` is advisory inside the container; proxy deny is the actual control. Keep both (defence in depth), proxy authoritative |
| Hand-rolled log miner | `sort -u` over Cloud Logging export | Correct choice is the trivial one here — see Don't Hand-Roll |

## Architecture Patterns

### System Architecture Diagram

```text
agent user / container ──(http_proxy=127.0.0.1:<own-port>)──▶ Squid :3128/:3129
        │                                                        │ allowlist? ──yes──▶ internet
        │ direct :80/:443                                        │              └──no──▶ 403 + log
        └──── nftables DROP ──(forces proxy path)                │
                                                          access.log (%lp=agent)
                                                                 └─▶ Cloud Logging (per-agent label)
```

Enforced triple (one unit): allowlist file + Squid ACLs + nftables drop-direct. nftables needs no change in this phase (drop-direct already correct for observe and enforce).

### Recommended Project Structure

No new files beyond:
```text
agents/policy/egress-allowlist.txt   # completed: declared + (empty) observed sections
agents/host/files/squid-hyprn.conf   # enforce ACLs generated from allowlist
tests/agents/checks/egress.sh        # +enforcement-on assertions (append, don't rewrite)
runbooks/agents/egress-enforce.md    # flip + rollback + first-observation procedure (or fold into existing egress runbook)
runbooks/agents/checks-<DATE>.md     # final kept record (run.sh appends automatically)
```

### Pattern 1: Squid allowlist enforcement (fail-closed)
**What:** Generate one `acl allowlist dstdomain` from the allowlist file; allow per-agent ports only to those domains; deny the rest explicitly; keep the access log.
**When to use:** This phase — the observe→enforce flip.
**Example:**
```squid
# Source: Squid standard dstdomain + http_access pattern [ASSUMED] applied to
# existing per-port structure [VERIFIED: agents/host/files/squid-hyprn.conf:22-34]
acl allowlist dstdomain "/etc/squid/hyprn-allowlist.acl"
acl ada_port myportname ada
acl codd_port myportname codd

http_access allow ada_port allowlist
http_access allow codd_port allowlist
http_access deny ada_port
http_access deny codd_port
http_access deny all

logformat hyprn %ts.%03tu %6tr %>a %Ss/%03>Hs %<st %rm %ru %lp %un
access_log /var/log/squid/access.log hyprn
```
Provisioning renders `/etc/squid/hyprn-allowlist.acl` from `agents/policy/egress-allowlist.txt` (strip comments/blank lines; fail-closed: render failure = keep old file + abort restart, never an empty allow). Denied CONNECTs return 403 and are logged with `%ru` + `%lp` — satisfying "refused and logged" for EGR-02.

### Pattern 2: One-command rollback to observe
**What:** Keep the previous working Squid config + allowlist ACL on the host (`/etc/squid/conf.d/hyprn.conf.prev`); rollback = copy back + `systemctl reload squid`. The systemd egress unit already applies nftables from a file, so nftables rollback (if ever touched) is `nft -f` the previous file — but this phase does not change nftables.
**When to use:** Owner checkpoint: flip command and rollback command shipped in the same plan; rollback tested by config-syntax check (`squid -k parse`) before any reload.

### Anti-Patterns to Avoid
- **Fail-open on render error:** empty/missing ACL file must never mean "allow all" — abort the reload and keep serving the old config.
- **Rewriting run.sh:** ACC-10 forbids new check domains; append enforcement assertions to `checks/egress.sh`, never restructure the harness.
- **Mining live traffic that doesn't exist:** observe mode never ran live — ship declared destinations + procedure, not fabricated "observed" entries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Domain allow/deny | iptables string-match / custom proxy | Squid `dstdomain` ACLs | TLS SNI/CONNECT parsing, caching, logging already solved |
| Observed-domain mining | Log-analysis service | `sort -u` over Cloud Logging export + human review into allowlist file | One-shot, human-gated; automation adds bypass risk |
| Acceptance aggregation | New test framework | Existing `run.sh` loop over `checks/*.sh` | Contract already proven across 6 phases |

## Allowlist Completion (EGR-02)

Status: **no observed traffic exists** (observe stack never applied live) — the observed section ships empty with the mining procedure documented. Declared destinations assembled read-only from repo sources:

| Domain | Source | Needed by |
|--------|--------|-----------|
| `github.com`, `api.github.com` | allowlist placeholder [VERIFIED: agents/policy/egress-allowlist.txt:8-9]; sandbox policy [VERIFIED: agents/policy/managed-settings.json:47-52]; host checks hit both [VERIFIED: tests/agents/host-checks.sh:29-30] | Ada/Codd git + `gh` |
| `api.anthropic.com` | placeholder + sandbox [same lines] | Claude seat/API path |
| `registry.npmjs.org` | placeholder + sandbox [same lines] | npm toolchain |
| `download.docker.com`, `cli.github.com` | provision.sh apt key fetch [VERIFIED: agents/host/provision.sh:44,52] | provisioning-time only (note: needed at apply, not steady-state) |
| `github.com` releases (`anomalyco/opencode`, `herdrdev/herdr`), `claude.ai` | provision.sh release fetch + Claude install [VERIFIED: agents/host/provision.sh:115,144,231] | provisioning-time only |
| `api.notion.com`, `slack.com` (+ `slack.com/api` paths via `ada-digest`, `wake.py`) | meeting loop allowlist [VERIFIED: agents/loops/meeting.yaml:22-25]; `ada-digest` posts to `https://slack.com/api/`; wake polls `https://slack.com/api/` | Boole loop, digests, wake |
| Fireworks / Anthropic / OpenAI provider endpoints (litellm `fireworks_ai/`, `anthropic/`, `openai/` bindings) | gateway config [VERIFIED: agents/gateway/litellm-config.yaml:4-16] | Gateway→provider (gateway host, not agent egress — record as declared-but-out-of-scope for the agent allowlist unless agents call providers directly) |
| `gateway.internal` | runner + meeting loop [VERIFIED: agents/host/files/hyprn-run-runner:15; agents/loops/meeting.yaml:23] | Operations run containers only (EGR-03 domain; include with comment marking container-only) |

File shape: keep one-domain-per-line; add section comments `# declared (reviewed <date>)` vs `# observed (mined <date>, <record>)`. Subdomain coverage: Squid `dstdomain` with leading-dot semantics covers subdomains — planner must confirm the exact leading-dot form against the Squid version on the host rather than assuming.

**First-live-observation update procedure:** after N days of enforced-with-review (period set by owner), export Cloud Logging per-agent destinations, `sort -u`, diff against allowlist, owner reviews the diff in a PR, provision re-renders + reloads. Deferred tuning stays out of scope per CONTEXT.

## Per-Agent No-Break Drill (dry-run/static)

Design (no live host needed for the static half):
1. **Static:** for each agent (ada/codd via fleet registry; boole via loop definition), assert every declared destination the agent needs is in the allowlist file (grep per domain; fail = missing entry). Asserts Ada/Codd routine set (github, api.github, anthropic, npm) and Boole loop set (gateway.internal, api.notion.com, slack.com).
2. **Dry-run (host, owner-go):** with enforcement loaded, per agent: allowed destination through proxy succeeds; disallowed destination (e.g. `example.com`) through proxy gets 403; direct `--noproxy` still drops (nftables unchanged). Mirror the existing observe-mode live probes in `checks/egress.sh` [VERIFIED: tests/agents/checks/egress.sh:31-41], flipping the expectation for the disallowed case from "succeeds through proxy" to "refused with log entry".
3. **Log proof:** denied request appears in access log with agent port label (`%lp`) — the EGR-02 "refused and logged" evidence.

## Final Aggregate Run (ACC-10)

Shape unchanged: `run.sh` runs `host-checks.sh` then every executable `checks/*.sh` in a guarded loop (one failure never masks later domains) and appends `## Run <STAMP> (checkout <HASH>)` + per-script table + overall to `runbooks/agents/checks-<DATE>.md` [VERIFIED: tests/agents/run.sh:20-62]. This phase adds only:
- enforcement-on assertions in `checks/egress.sh` (config carries per-port allow ACLs + explicit denies; allowlist ACL file non-empty; live 403-on-disallowed + log-entry checks),
- the no-break drill assertions above,
- the kept dated record is the final acceptance artifact (no separate artifact to build).

## Common Pitfalls

### Pitfall 1: Allowlist misses a provisioning-time domain, bricking re-provision
**What goes wrong:** Enforcement blocks `download.docker.com` / release hosts during the next provision. **Why:** steady-state vs apply-time needs conflated. **Avoid:** keep a commented apply-time section; drill includes a provision-path review. **Signs:** first enforced re-provision fails on apt/release fetch.

### Pitfall 2: Subdomain mismatch (slack.com vs subdomains, api hosts)
**What goes wrong:** `slack.com` entry doesn't cover a subdomain the bot actually calls. **Avoid:** verify Squid `dstdomain` subdomain semantics on the host's Squid version; prefer explicit entries for each observed FQDN. **Signs:** 403s for hosts that "look" allowlisted.

### Pitfall 3: Container egress path differs from login path
**What goes wrong:** Login-user probes pass but `host.containers.internal:<port>` container path fails. **Avoid:** drill asserts both paths per agent, mirroring existing container probes [VERIFIED: tests/agents/checks/egress.sh:39-40]. **Signs:** runner dry-run 403s on allowed hosts.

### Pitfall 4: Rollback untested
**What goes wrong:** Flip breaks work and revert is improvised under pressure. **Avoid:** rollback is a reviewed one-liner + `squid -k parse` pre-check, shipped in the same plan as the flip.

## Code Examples

### Render allowlist ACL (provision step)
```bash
# Strip comments/blank lines; fail-closed: empty output aborts, never writes empty ACL
grep -vE '^\s*(#|$)' "$REPO/agents/policy/egress-allowlist.txt" | sort -u > /tmp/hyprn-allowlist.acl
[ -s /tmp/hyprn-allowlist.acl ] || { echo "allowlist render empty; refusing" >&2; exit 1; }
install -m 0644 /tmp/hyprn-allowlist.acl /etc/squid/hyprn-allowlist.acl
squid -k parse && systemctl reload squid
```

### Enforcement assertions (append to checks/egress.sh)
```bash
check "proxy denies non-allowlisted per-agent ports" \
  "grep -v '^#' '$SQUID' | grep -qE '^http_access deny (ada_port|codd_port)'"
check "proxy allow ACL references the rendered file" \
  "grep -v '^#' '$SQUID' | grep -q 'dstdomain'"
check "rendered allowlist non-empty" "[ -s /etc/squid/hyprn-allowlist.acl ]"
# live (host only): disallowed refused + logged
check "disallowed refused with log entry" \
  "run 'https_proxy=... curl -s -o /dev/null -w %{http_code} https://example.com' | grep -q 403"
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Squid `dstdomain` leading-dot form covers subdomains on the host's Squid version | Architecture Patterns | Allowlist misses subdomains → 403s on legit traffic; confirm on host |
| A2 | Exact provider endpoint hostnames for Fireworks/Anthropic/OpenAI calls from agents | Allowlist Completion | Missing entry breaks loop runs; resolve from gateway deploy + first observation |
| A3 | Observation window length before first allowlist tuning | Allowlist Completion | Owner sets at flip checkpoint |

## Open Questions

1. **Boole's proxy port** — `squid-hyprn.conf` declares only ada/codd ports [VERIFIED: agents/host/files/squid-hyprn.conf:22-23]; Boole (operations) enforcement path (own port vs shared, container `PROXY_PORT` default 3128 [VERIFIED: agents/host/files/hyprn-run-runner:17]) must be settled from fleet registry at plan time.
2. **Provisioning-time vs steady-state split** — planner confirms which fetch domains must be in the enforced file vs apply-time exception.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Agent host (root, nft, squid, docker) | flip + live drill + final run | ✗ (research env is not the host) | — | Static assertions anywhere; live steps are owner-go host apply |
| `squid -k parse` | config pre-check | ✗ here | — | Host-time check |
| Cloud Logging (`gcloud logging read`) | observed-mining + log-flow proof | ✗ here | — | Existing egress.sh query pattern [VERIFIED: tests/agents/checks/egress.sh:43] at host time |

No missing dependency blocks planning — all live steps are already owner-gated per CONTEXT.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Bash checks (no test runner; `bash -n` syntax + `check()` helper) |
| Config file | none — convention: executable `tests/agents/checks/*.sh`, run via `run.sh` |
| Quick run command | `bash tests/agents/checks/egress.sh` (static subset passes anywhere; live probes SKIP/FAIL off-host by design) |
| Full suite command | `tests/agents/run.sh` (host, root; appends `runbooks/agents/checks-<DATE>.md`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EGR-02 | Disallowed domain refused + logged; allowed destinations succeed per agent (login + container) | host live (static grep anywhere) | `tests/agents/checks/egress.sh` | ✅ exists, extend (Wave 0: append enforcement assertions) |
| ACC-10 | Full suite green with enforcement on; dated record kept | aggregate host run | `tests/agents/run.sh` | ✅ exists, unchanged |

### Sampling Rate
- **Per task commit:** `bash -n` on touched scripts + relevant `checks/*.sh` static subset
- **Per wave merge:** full `checks/egress.sh` static subset
- **Phase gate:** owner-go host `run.sh` green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/agents/checks/egress.sh` — append enforcement-on + drill assertions (no new file)
- [ ] None — harness, record convention, and per-agent loop patterns already exist

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | n/a (no identity change) |
| V4 Access Control | yes | Squid per-port ACLs bind each port to its agent; default-deny |
| V5 Input Validation | yes | Allowlist file parsed strictly (strip comments/blanks, `sort -u`); loop allowlists remain the only destination source for runs (never trigger payload — runner rule [VERIFIED: agents/host/files/hyprn-run-runner:30-36]) |
| V6 Cryptography | no | No TLS interception (no SSL bump, per observe config); DNS stays allowed |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Allowlist bypass via direct connection | Tampering | nftables drop-direct unchanged (login + container ranges) |
| Fail-open on empty/missing ACL | Tampering | Render gate: empty = abort reload, keep old config |
| Unattributed egress (which agent?) | Repudiation | `%lp` per-port log label + Cloud Logging ship preserved |

## Sources

### Primary (HIGH confidence)
- `agents/host/files/squid-hyprn.conf`, `agents/host/files/egress.nft`, `hyprn-agents-egress.service` — read this session
- `tests/agents/run.sh`, `tests/agents/checks/egress.sh`, `host-checks.sh` — read this session
- `agents/policy/egress-allowlist.txt`, `managed-settings.json` sandbox, `agents/loops/meeting.yaml`, `hyprn-run-runner`, `litellm-config.yaml`, `provision.sh` — read this session
- `docs/specs/agent-fleet.md` §13 — read this session

### Secondary (MEDIUM confidence)
- None (no web fetch needed; all findings repo-grounded)

### Tertiary (LOW confidence)
- Squid `dstdomain` subdomain semantics + `squid -k parse` flag — standard Squid knowledge [ASSUMED], confirm on host

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all components already in repo and read
- Architecture: HIGH - enforcement is a config delta on a proven observe stack
- Pitfalls: MEDIUM - grounded in repo structure; live failure modes unproven until host apply

**Research date:** 2026-10-14
**Valid until:** 30 days (stable domain; host Squid version check at plan time)
