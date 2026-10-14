# Phase 5: Learning - Research

**Researched:** 2026-10-14
**Domain:** Learning loop for the Boole meeting loop — feedback capture, eval set + runner, improvement PRs, promotion rule, Boole's GitHub App declaration
**Confidence:** HIGH (all structural findings read from repo sources this session)

## User Constraints (from CONTEXT.md)

### Locked Decisions

- Build the eval machinery (runner on host through gateway path with fakes, regression suite shape, 20-case minimum structure) seeded from Phase 4 fixtures and trial-shaped synthetic cases clearly marked as seeds. Real-run cases replace seeds as the trial produces them; the runner accepts both.
- No fabricated "real" results: seeds are labeled seeds everywhere (files, reports, PR bodies).
- Reactions, replies, approval decisions stored with their run (schema + writer path with fakes); Slack shape follows the channel-server event model. Live wiring waits for Boole's bot (owner vendor step).
- Improvement runs propose prompt/skill changes as draft PRs; the eval runner posts results on the PR; only passing changes reach the owner, who merges. Prove the flow with a fixture improvement (seed evals) end to end.
- Promotion A1→A2 ships as a reviewed-change template (rule check: ≥90% over last 10 + <1 correction/meeting), not an executed promotion.
- OPS-03: App manifest + install-scope declaration (`hyprn-platform` only) + broker path, creation itself an owner checklist. No App creation, no keys in this phase's execution.

### The agent's Discretion

All Phase 5 answers at agent discretion under the autonomous-run direction.

### Deferred Ideas (OUT OF SCOPE)

- Real-run eval cases (arrive with the trial).
- Executed A1→A2 promotion (needs 10 real runs + owner merge).
- Second loops' eval sets.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPS-03 | Boole's GitHub App `boole-agent-hyprn` installed on `hyprn-platform` only, contents + PR access; tokens from credential broker | App declaration pattern (§Boole App); broker already mints installation tokens |
| LRN-01 | Reactions, replies, approval decisions in Slack stored with their run as feedback | Feedback schema + writer path; channel-server event model |
| LRN-02 | Meeting loop eval set ≥20 cases from real runs + feedback, regression suite; runner on host through gateway | Eval-set JSONL shape, runner design with fixture seam |
| LRN-03 | Improvement run opens draft PR with prompt/skill changes; eval runner posts result; only passing reach owner, who merges | Improvement-PR flow mirroring GH-01 contract + broker token path |
| LRN-04 | Meeting loop moves A1→A2 by reviewed change once ≥90% over last 10 runs and <1 correction/meeting | Promotion-rule check template reading run + feedback state |

## Summary

Phase 5 adds the learning half of the meeting loop on top of the Phase 3/4 control plane without inventing any new infrastructure style: every new piece follows an established repo pattern. The run-state database (`controller/schema.sql`) gains a `feedback` table beside `runs`/`approvals`, written through a `Dispatcher.record_feedback` method tested with the same in-memory-sqlite fakes as the existing suite. The eval set is a JSONL file at the path the loop registry already declares (`eval_set: agents/loops/meeting-eval.jsonl`), seeded with ≥20 trial-shaped cases marked `"origin": "seed"`. The eval runner is a host script with a `--fixture` offline mode (the exact seam `hyprn-credential-broker --fixture` and `hyprn-meeting-workflow --fixture` already use), posting a seed-labeled report on the PR via `gh` with the broker-minted token. Improvement PRs reuse the GH-01 draft-PR contract (`## What changed` / `## How verified`, branch `agent/boole/<slug>`, bot author, never self-merge). The promotion check is a small script evaluating the rule the registry already declares (`min_pass_rate: 0.9`, `last_runs: 10`, `max_corrections_per_run: 1`), shipped as a template, not executed. Boole's App is declaration + owner checklist only: the secret container already exists in Terraform, and no key material is touched in this phase.

**Primary recommendation:** Implement Phase 5 as five thin slices that each extend one existing file/pattern (schema.sql + dispatcher.py; meeting-eval.jsonl; eval runner script; improvement-PR path; promotion-check script), plus the Boole App declaration docs — no new services, no new dependencies, no external packages.

## Project Constraints (from AGENTS.md)

- Product code never enters this repository; platform infrastructure never enters a product repository.
- Every step creating/changing cloud resources, IAM, org policy, billing, or GitHub/Slack org settings runs only after the platform owner's explicit go. Terraform: plan, review, apply exactly the reviewed plan. Staging/prod have separate state and authority.
- Never commit credentials, Terraform state/plan files, tfvars with secret values, service-account keys, or session data. Never print a secret value.
- Record what was done in the relevant runbook.
- No `gcloud`, Terraform applies, or cloud-changing actions in this phase's execution (consistent with declared-not-created App + owner checklists).
- Read-only inspection needs no approval.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Feedback storage (reactions/replies/approvals with runs) | API / Backend (controller run-state DB) | — | Spec §8: "Runs, approvals, budgets, feedback records" are control-plane run state [VERIFIED: docs/specs/agent-fleet.md:114-123] |
| Eval runner execution | Agent host (run runner container, gateway path) | — | LRN-02 requires host-through-gateway; runner pattern exists in `hyprn-run-runner` |
| Eval result posting on PR | Agent host (gh CLI with broker token) | — | Same token path as GH-01 draft PRs; broker mints installation tokens |
| Improvement proposal (prompt/skill diff) | Repo (draft PR against `agents/loops/meeting/`) | — | Spec §1: playbook changes by pull request [VERIFIED: docs/specs/agent-fleet.md:9-15] |
| Promotion rule evaluation | Agent host (check script over run state) | — | Reads run + feedback rows; no new service |
| Boole App declaration | Repo (docs + Terraform secret container) | Owner vendor console | Creation is an owner checklist per CONTEXT |

## Standard Stack

### Core

No new libraries. The phase is Python 3 stdlib + bash, matching every existing component:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python 3 stdlib (`sqlite3`, `json`, `urllib`, `unittest`) | 3.11.2 on this machine [VERIFIED: runtime probe] | Feedback writer, eval-set parsing, eval runner, unit tests | `dispatcher.py` and `poll_notion.py` already declare "Python 3 standard library only" [VERIFIED: controller/dispatcher.py:17, controller/poll_notion.py:19]; `python3-yaml` available (Debian `python3-yaml`) [VERIFIED: runtime probe] |
| bash + `gh` CLI | host-provided | Eval-result PR comments, improvement-PR creation | GH-01 contract already uses `gh pr` via agent users [VERIFIED: tests/agents/checks/github.sh:64-68] |
| Existing check harness | `tests/agents/run.sh` + `checks/*.sh` | Eval + learning checks join the one-command run (ACC-08) | Phase 4 precedent: `meeting.sh` auto-discovered as executable [VERIFIED: tests/agents/checks/meeting.sh:75] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML (Debian `python3-yaml`) | system | Reading loop YAML in eval/promotion scripts | Same as `validate.py` and workflow helpers [VERIFIED: agents/loops/validate.py:8] |
| `jq` | system | JSONL/case handling in shell checks | Precedent in `github.sh` ruleset assertions [VERIFIED: tests/agents/checks/github.sh:19-31] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONL eval file in repo | Cloud SQL table for eval cases | DB adds migration + apply ceremony; file is reviewable by PR, matches `eval_set` registry field which is a path [VERIFIED: agents/loops/meeting.yaml:29] |
| Host script eval runner | LiteLLM batch / external eval service | External service is a new vendor + egress allowlist change; host script reuses gateway path and fakes |
| New feedback service | `feedback` table in run-state DB | Spec §8 already names feedback records as control-plane run state |

**Installation:**
```bash
# Nothing to install. Stdlib + system bash/jq/yaml only.
```

**Version verification:** No external packages; `python3 --version` → `Python 3.11.2`, `python3 -c "import yaml"` → ok (probed 2026-10-14 on this machine).

## Package Legitimacy Audit

Not required: this phase installs zero external packages. Standard stack is Python stdlib + host-provided bash/`gh`/PyYAML, all already used by Phases 3–4. Planner must not add any `pip`/`npm` install task; if a plan proposes one, that is a scope violation.

**Packages removed due to SLOP verdict:** none (no packages proposed).
**Packages flagged as suspicious (SUS):** none.

## Architecture Patterns

### System Architecture Diagram

```text
owner feedback in Slack (reaction / reply yes|no / approval answer)
        │
        ▼ (live wiring DEFERRED — waits for Boole's bot, owner vendor step)
controller Socket-Mode path (Phase 3 pattern: Dispatcher.resume, sender==owner)
        │  Phase 5: Dispatcher.record_feedback(run_id, kind, payload, sender)
        ▼
run-state DB: runs + approvals + NEW feedback table  (schema.sql, SQLite now → Cloud SQL at apply)
        │
        ├─► eval-set builder: feedback rows → real cases replace "origin":"seed" cases
        │
agents/loops/meeting-eval.jsonl  (≥20 cases, seed-labeled; regression:true subset)
        │
        ▼
eval runner (host, gateway path; --fixture offline mode with fakes)
        │  posts seed-labeled report on the PR under test
        ▼
improvement run → draft PR agent/boole/<slug> (prompt/skill diff)
        │  eval gate: PASS → owner review queue; FAIL → stays draft, never shown
        ▼
owner merges  (ruleset + human approval; agents never merge)
        │
        ▼
promotion-check script: last-10 pass rate ≥90% + corrections <1/meeting
        → A1→A2 as reviewed change to meeting.yaml (template, not executed)
```

Entry point is owner feedback and the improvement proposal; processing flows feedback-store → eval-set → runner → PR gate → owner merge → promotion check. The GitHub App (`boole-agent-hyprn`, `hyprn-platform` only) is the identity boundary for all PR writes; its tokens come from the credential broker.

### Recommended Project Structure

```text
agents/loops/
├── meeting.yaml                 # unchanged shape; eval_set already points at meeting-eval.jsonl
├── meeting-eval.jsonl           # NEW: ≥20 seed cases, "origin":"seed", regression subset
├── meeting/
│   ├── prompts.md               # improvement target (diffed by improvement PRs)
│   └── skills/notion-slack-shapes.md  # improvement target
├── eval-runner.py (or agents/eval/run.py)  # NEW: host runner, --fixture mode, PR posting
└── promotion-check.py (or agents/eval/promotion.py)  # NEW: rule-check template
controller/
├── schema.sql                   # ADD feedback table
├── dispatcher.py                # ADD record_feedback + feedback query helpers
└── test_feedback.py             # NEW: fake-backed unit tests (in-memory sqlite)
tests/agents/checks/
└── learning.sh                  # NEW: executable, auto-discovered by run.sh
runbooks/agents/
├── learning.md (or evals.md)    # NEW: seed-label rule, improvement flow, promotion template use
└── github.md                    # APPEND Boole App row (declaration, not creation)
```

### Pattern 1: Fake-seam scripts with `--fixture` offline mode

**What:** Every host-touching script runs fully offline with fakes: broker `--fixture <dir>` creates placeholder run dirs with no network [VERIFIED: agents/host/files/hyprn-credential-broker:52-59]; meeting workflow `--fixture <dir> --page <id>` copies fixture pages instead of calling Notion [VERIFIED: agents/host/files/hyprn-meeting-workflow:66-92]; poller `--fixture` scans a directory of page JSON [VERIFIED: controller/poll_notion.py:125-134].
**When to use:** The eval runner MUST follow this pattern: `--fixture` runs all cases against canned model outputs / the local extract function, no gateway, no tokens — so `learning.sh` passes anywhere and the live path is a strict superset.
**Example:**
```bash
# Shape precedent (broker fixture mode) [VERIFIED: agents/host/files/hyprn-credential-broker:52-59]:
#   dir="$FIXTURE_DIR/$RUN_ID"
#   install -d -m 0700 "$dir"
eval-runner --fixture agents/loops/testdata/eval-fixtures --eval agents/loops/meeting-eval.jsonl
eval-runner --run <run-id> --eval agents/loops/meeting-eval.jsonl   # live: gateway path
```

### Pattern 2: Registry-gated, idempotent queue writes

**What:** `Dispatcher.enqueue` records the idempotency key BEFORE dispatch and refuses unknown loops BEFORE touching credentials/compute [VERIFIED: controller/dispatcher.py:61-86]. Poller persists the cursor AFTER successful enqueue; restart re-polls dedupe on `notion-page-<page-id>` [VERIFIED: controller/poll_notion.py:15-17].
**When to use:** Feedback writes follow the same discipline: `record_feedback` validates `run_id` exists and `kind` is in a closed set before inserting; duplicate deliveries (Socket-Mode retries) dedupe on a caller-supplied dedupe key.

### Pattern 3: Park-then-exit approvals with owner-only resume

**What:** Workflow parks via `Dispatcher.park(run_id, question)` holding only a DB row, exits immediately (no sleep-with-container), and applies the PATCH only when `Dispatcher.resume` returns true for the loop owner [VERIFIED: agents/host/files/hyprn-meeting-workflow:167-179, agents/host/files/hyprn-meeting-workflow:181-200]. Stranger answers keep the run parked [VERIFIED: controller/dispatcher.py:116-128]. Summary posts carry run id + page id so a yes cannot replay onto another run [VERIFIED: agents/loops/meeting/skills/notion-slack-shapes.md:29-42].
**When to use:** Approval-decision feedback (LRN-01) is recorded in the same `resume` path: owner yes/no is both the resume verdict AND a feedback row (`kind:"approval"`), so LRN-01 approval capture costs one extra INSERT, not a new listener.

### Pattern 4: Draft-PR contract with bot authorship, owner-only merge

**What:** GH-01: branch `agent/<name>/<slug>`, draft PR authored by `<name>-agent-hyprn[bot]`, body carries `## What changed` + `## How verified`, no self-merge path (`gh pr merge` absent from helper/intake) [VERIFIED: tests/agents/checks/github.sh:39-45]. Ruleset requires PR + human code-owner approval, stale dismissal, no App bypass [VERIFIED: tests/agents/checks/github.sh:18-33].
**When to use:** Improvement PRs MUST reuse this contract verbatim with `agent/boole/<slug>` branches; eval report is a PR comment (or `## Eval result` body section) labeled seeds. Spec §10 requires the change pass evals before owner review and owner-only merge [VERIFIED: docs/specs/agent-fleet.md:137-142].

### Anti-Patterns to Avoid

- **Fabricated "real" results:** any seed output presented as a real run. CONTEXT forbids it; label `seed` in filenames, JSONL `origin` field, runner reports, and PR bodies.
- **Live-first scripts:** a runner/check that needs gateway/tokens to pass. meeting.sh precedent: fake-backed probes run anywhere, live parts SKIP with reason [VERIFIED: tests/agents/checks/runner.sh:45-53].
- **Secrets in eval fixtures or PR bodies:** meeting.sh already guards meeting declarations against `xox[baprs]-`/`ntn_`/`sk-` patterns [VERIFIED: tests/agents/checks/meeting.sh:71]; extend the guard to the eval file and runner output.
- **Executing the A1→A2 promotion:** CONTEXT defers it (needs 10 real runs). Ship the check as a template; a plan that flips `autonomy` in meeting.yaml is out of scope.
- **Creating the App or minting real keys in-phase:** OPS-03 is declared-not-created. Any task calling App-create APIs or writing key material fails the phase's own checks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub App JWT + installation-token minting | Custom signing code in eval runner | Existing `hyprn-credential-broker` / `hyprn-agent-github-token` flow (RS256, 1-hour tokens) [VERIFIED: agents/host/files/hyprn-credential-broker:105-132] | Key handling, expiry math, permission scoping (`contents:write, pull_requests:write, metadata:read`) already reviewed |
| Run queue, idempotency, resume semantics | New queue for eval/improvement runs | `Dispatcher` (enqueue/dispatch/park/resume/record_cost) | Idempotency-before-dispatch and owner-only resume are the audited invariants |
| Slack event intake | New Slack listener for feedback | Channel server `server.py` model (Socket Mode, allowlist, `reply` tool) + controller-held ops connections per spec §5 | Spec already assigns ops Socket-Mode connections to the controller [VERIFIED: docs/specs/agent-fleet.md:83-87] |
| Notion API shapes | New Notion client | `notion-slack-shapes.md` pinned header `Notion-Version: 2026-03-11` + workflow fetch/patch functions | Property-schema-id rule and draft-before-apply already encoded |
| Eval statistics | Custom aggregation service | `record_cost`-style ledger reads + promotion-check script over sqlite | `record_cost` accumulates per-run cost in one UPDATE [VERIFIED: controller/dispatcher.py:135-140]; same shape serves pass-rate/correction counts |

**Key insight:** Phase 5 is a data-and-gates phase, not a services phase. Every capability (identity, queue, approvals, secrets, PR shape) already exists and is check-covered; the work is one new table, one new JSONL file, two small scripts, and one check file — all reusing the fake-seam and draft-PR patterns.

## Common Pitfalls

### Pitfall 1: Seeds leaking into "real" metrics
**What goes wrong:** Promotion check or eval report counts seed cases as real runs, manufacturing the ≥90% pass rate.
**Why it happens:** Runner accepts both seeds and real cases (by design), and a naive `SELECT AVG(pass)` blends them.
**How to avoid:** `origin` is a REQUIRED case field; runner report prints seed and real tallies on separate lines; promotion check counts only `origin:"real"` runs (zero real runs → `INSUFFICIENT DATA`, never PASS).
**Warning signs:** Pass-rate denominator exceeds the number of rows in `runs`; report lacks the word "seed".

### Pitfall 2: Feedback listener scope creep into bot behavior
**What goes wrong:** Feedback capture changes what the bot posts (extra reactions, altered reply shapes), breaking meeting.sh assertions.
**Why it happens:** The Slack manifest already grants `reactions:write` and the server adds `eyes`/`white_check_mark` acknowledgments [VERIFIED: agents/marketplace/plugins/slack/slack-app-manifest.yaml:17-21; agent-fleet §11 channel behavior per server.py greetings at lines 216/244 per grep].
**How to avoid:** Feedback capture is read-side only (store what arrived: reaction/reply/approval + run id). No new bot scopes, no new events (`app_mention`, `message.im` already subscribed) [VERIFIED: agents/marketplace/plugins/slack/slack-app-manifest.yaml:23-26]. Live wiring waits for Boole's bot per CONTEXT.

### Pitfall 3: Eval runner that only passes on the host
**What goes wrong:** `learning.sh` fails off-host (CI/review), blocking every later phase's green run.
**Why it happens:** Runner shells to gateway/`gh` unconditionally.
**How to avoid:** `--fixture` default in checks; live path guarded by tool presence with `SKIP <reason>` (runner.sh dry-run precedent) [VERIFIED: tests/agents/checks/runner.sh:45-53]. Static assertions (JSONL parses, ≥20 cases, all seeds labeled, regression subset non-empty) run anywhere.

### Pitfall 4: Improvement PR touching autonomy levels
**What goes wrong:** A prompt/skill improvement silently includes an `autonomy:` change (e.g., notion-write A1→A2), executing the deferred promotion by accident.
**Why it happens:** Prompts and loop YAML live side by side; a broad diff looks harmless.
**How to avoid:** Eval-gate check asserts the improvement diff touches only `agents/loops/meeting/prompts.md` and `agents/loops/meeting/skills/*`; any `meeting.yaml` change (especially `autonomy`/`promotion_rule`) fails the gate. Validator already rejects bad autonomy levels [VERIFIED: agents/loops/validate.py:40-43].

### Pitfall 5: Undeclared-secret reads from the eval/improvement path
**What goes wrong:** Runner or improvement script reads a secret not in the loop's declared tools, violating the reviewed-YAML-only authority.
**Why it happens:** Copy-paste from workflow code without the `declared_secrets()` guard.
**How to avoid:** Reuse the exact guard: secret names come ONLY from the reviewed loop file, never trigger payload [VERIFIED: agents/host/files/hyprn-meeting-workflow:46-60]; meeting.sh asserts the marker comment [VERIFIED: tests/agents/checks/meeting.sh:33]. Same assertion in learning.sh.

## Code Examples

Verified patterns from repo sources read this session:

### Feedback table (extend schema.sql)

```sql
-- Precedent: runs + approvals [VERIFIED: controller/schema.sql:4-21]
--   "CREATE TABLE IF NOT EXISTS runs(
--     id TEXT PRIMARY KEY,
--     loop TEXT NOT NULL,
--     ...
--     idempotency_key TEXT NOT NULL UNIQUE, ..."
--   "CREATE TABLE IF NOT EXISTS approvals(
--     run_id TEXT NOT NULL REFERENCES runs(id),
--     question TEXT NOT NULL,
--     answer TEXT,
--     decided_at TEXT
--   );"
CREATE TABLE IF NOT EXISTS feedback(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES runs(id),
  kind TEXT NOT NULL,            -- 'reaction' | 'reply' | 'approval' (closed set, enforced in writer)
  payload TEXT NOT NULL,         -- JSON: emoji / reply text+sender / answer+sender
  sender TEXT NOT NULL DEFAULT '',
  dedupe_key TEXT NOT NULL UNIQUE, -- caller-supplied idempotency (Socket-Mode retries)
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Feedback writer (extend dispatcher.py)

```python
# Precedent: park holds a DB row, resume is owner-gated [VERIFIED: controller/dispatcher.py:107-128]
#   "def park(self, run_id, question):"
#   "def resume(self, run_id, answer, sender, owner):"
#   "    if sender != owner: ... return False"
FEEDBACK_KINDS = ("reaction", "reply", "approval")

def record_feedback(self, run_id, kind, payload, sender="", dedupe_key=""):
    if kind not in FEEDBACK_KINDS:
        return None
    # ... verify run_id exists, INSERT OR IGNORE on dedupe_key ...
```

### Approval answer doubles as feedback (LRN-01 cheapest path)

Approval decisions already flow through `Dispatcher.resume(run_id, answer, sender, owner)` with the sender==owner gate [VERIFIED: controller/dispatcher.py:116-128]; the caller records `kind:"approval"` with `{answer, sender}` in the same transaction path. Reactions/replies arrive via the channel-server event model (`app_mention`, `message.im` subscriptions; threaded replies via `thread_ts`) [VERIFIED: agents/marketplace/plugins/slack/slack-app-manifest.yaml:23-26] and are stored with the run id parsed from the bot's scoped summary text (`[meeting <run-id> page <page-id>]`) [VERIFIED: agents/loops/meeting/skills/notion-slack-shapes.md:29-42].

### Eval case shape (JSONL, one object per line)

```json
{"id": "seed-001", "origin": "seed", "regression": true, "page": {"title": "Weekly sync 2026-10-13", "body": "DECISION: Ship the beta to five pilot customers by Nov 1. ..."}, "expect": {"min_decisions": 1, "min_actions": 1, "must_quote_source": true, "propose_nothing": false}}
```

Page text mirrors the Phase 4 fixture (`new.json`: title + DECISION/ACTION/Open-question body) [VERIFIED: agents/loops/testdata/meeting-pages/new.json:1]; expectations mirror the rubric contract (`decisions`/`actions`/`open_questions`/`patch` + quote-the-source rule + propose-nothing degrade) [VERIFIED: agents/loops/meeting/prompts.md:12-44]. `origin` accepts only `seed`|`real`; `regression:true` marks the always-run subset.

### Promotion rule source of truth (meeting.yaml)

```yaml
# [VERIFIED: agents/loops/meeting.yaml:29-33]
eval_set: agents/loops/meeting-eval.jsonl
promotion_rule:
  min_pass_rate: 0.9
  last_runs: 10
  max_corrections_per_run: 1
```

The check script reads these three values from the registry file (never hard-codes thresholds) and evaluates: pass rate over last 10 `origin:"real"` runs ≥ `min_pass_rate` AND corrections/run < `max_corrections_per_run`. Fewer than 10 real runs → `INSUFFICIENT DATA (seeds excluded)`, exit non-zero with that message — never a false PASS.

### Unit-test fake pattern (extend, don't invent)

```python
# [VERIFIED: controller/test_dispatcher.py:16-28]
# "def fresh_db():
#       connection = sqlite3.connect(":memory:")
#       ...connection.executescript(open(SCHEMA).read())..."
# "def registry_of(*names):
#       return lambda: {name: {"name": name} for name in names}"
```

`test_feedback.py` uses `fresh_db()` + `Dispatcher(db, registry=registry_of("meeting"))`: closed-kind enforcement, dedupe-key idempotency, unknown-run refusal, approval-feedback pairing. Runs via `python3 -m unittest discover -s controller` inside the existing `controller.sh` assertion [VERIFIED: tests/agents/checks/controller.sh:14].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Machine account + 90-day token for agent GitHub access | Per-agent GitHub App + 1-hour broker tokens | 2026-10-13, ADR-0005 | Boole's App follows the App pattern; no long-lived tokens anywhere |
| tmux session wrapper | herdr session runtime (tmux fallback) | Phase 2 scope | Irrelevant to Phase 5 (ops runs use containers, not sessions) |
| No evals (Phase 4 ships loop without learning) | Seed-labeled JSONL evals + fixture runner, real cases replace seeds | This phase | Trial can start learning machinery before real runs exist |

**Deprecated/outdated:**
- `hyprn-ada` machine account + `ada-agent-github-token` secret: removed; guard in github.sh forbids return [VERIFIED: tests/agents/checks/github.sh:51-52]. Boole MUST NOT get a machine account — App only.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `gh` CLI with `pr comment` + draft-PR creation works under the broker-minted Boole token on the host | Improvement-PR flow | Runner cannot post results; fallback: write report to run dir + log, owner reads from host (still proves gate logic statically) |
| A2 | Gateway path reachable from eval-run container under `boole` via `ALLOWED_HOSTS` + `MODEL_BINDING` env (runner.sh pattern) | Eval runner live path | Live evals blocked; fixture mode still proves everything off-host; confirm at trial go-checkpoint |
| A3 | Controller holds Boole's Socket-Mode connection at trial time so reactions/replies are observable (spec §5) | Feedback live wiring | Live feedback capture waits; schema + writer + approval-path capture still land this phase (CONTEXT already gates live wiring on Boole's bot) |
| A4 | LiteLLM gateway model-list change is config-only for eval traffic (no new provider key for evals) | Eval runner | If evals need a distinct model/key, add a `loop_keys` entry at the owner-go step; no code change |

## Open Questions

1. **Who authors the 20 seed cases — hand-written fixtures or generator script?**
   - What we know: Phase 4 fixtures (`new.json`, `updated.json`, `malformed.json`) + rubric give 3+ shapes; need ≥20 covering decisions/actions/questions/malformed/injection-guard cases.
   - What's unclear: Whether planner prefers a checked-in generator (reproducible, reviewable seed) or 20 hand-written JSONL lines.
   - Recommendation: Hand-write ~8 anchor cases from fixtures, generate the rest by small matrix script (kept in repo, seed-pinned) — planner decides; either satisfies "labeled seeds".

2. **Eval verdict mechanics — exact-match on contract vs. rubric-graded?**
   - What we know: Rubric emits fixed JSON contract with quote-the-source rule; deterministic checks (valid JSON, required keys, every item has non-empty `source` quoting a meeting line, malformed→propose-nothing) cover most of it without an LLM judge.
   - What's unclear: Whether extraction quality (right decisions, not just shaped ones) needs a model-graded check through the gateway.
   - Recommendation: Deterministic checks are the gate (fast, offline-capable); add one gateway-graded quality score as advisory-only in this phase, promotable to gate later with real runs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 + stdlib sqlite3/json/unittest | Feedback writer, eval runner, unit tests | ✓ | 3.11.2 (probed) | — |
| PyYAML (`python3-yaml`) | Loop YAML reads | ✓ (probed `import yaml` ok) | system | — |
| bash + jq | Check scripts, JSONL handling | ✓ (this shell) | — | python3 one-liners |
| `gh` CLI | PR result posting, improvement PRs | [ASSUMED] host-provided (used by Phase 2 GH-01 path) | — | Report-to-file fallback (A1) |
| docker + `boole` user | Host live runs | ✗ here (review machine, not agent host) | — | `--fixture` offline mode; live proves at owner-go |
| Gateway / Cloud SQL | Live eval path, feedback persistence | ✗ here (declared-not-applied until Phase 3 go) | — | sqlite file + fixture mode |
| Boole's Slack bot / GitHub App | Live feedback + PR writes | ✗ (owner vendor steps, CONTEXT-gated) | — | Schema/writer/manifest-declaration land now |

**Missing dependencies with no fallback:**
- None blocking: every Phase 5 deliverable has a static/fixture proof per CONTEXT (seeds, fakes, declared-not-created).

**Missing dependencies with fallback:**
- Gateway, `boole` user/docker, Boole's bot + App → fixture mode + owner checklists (A1–A3).

## Validation Architecture

| Property | Value |
|----------|-------|
| Framework | bash check scripts (`check()`/`skip()` helpers) + Python stdlib `unittest` — no third-party framework, per repo precedent [VERIFIED: tests/agents/checks/controller.sh:1-21, controller/test_dispatcher.py:1-12] |
| Config file | none — `tests/agents/run.sh` auto-discovers every executable `tests/agents/checks/*.sh` [VERIFIED: tests/agents/run.sh:41-46] |
| Quick run command | `tests/agents/run.sh` (full one-command run; each domain <30s statically) |
| Full suite command | `tests/agents/run.sh` (same; appends dated record to `runbooks/agents/`) [VERIFIED: tests/agents/run.sh:48-62] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPS-03 | Boole App declared `hyprn-platform`-only, contents+PR perms; secret container exists; no creation/keys in-phase | static (file assertions) | `tests/agents/checks/learning.sh` | ❌ Wave 0 |
| LRN-01 | Feedback rows stored with run; kinds closed; dedupe; approval answer recorded | unit (in-memory sqlite fakes) | `python3 -m unittest discover -s controller` | ❌ Wave 0 (`test_feedback.py`) |
| LRN-02 | Eval file: ≥20 cases, all `origin`-labeled, regression subset non-empty; runner `--fixture` green offline | static + fixture probe | `tests/agents/checks/learning.sh` | ❌ Wave 0 (`meeting-eval.jsonl`, runner, `learning.sh`) |
| LRN-03 | Improvement PR follows draft-PR contract; eval report posted + seed-labeled; failing fixture improvement never reaches owner | fixture end-to-end (seed evals, file-backed PR-shape proof) | `tests/agents/checks/learning.sh` | ❌ Wave 0 |
| LRN-04 | Promotion check reads registry thresholds; <10 real runs → INSUFFICIENT DATA; no `autonomy` flip in-phase | static + unit | `tests/agents/checks/learning.sh` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `bash -n` on touched scripts + `python3 -m unittest discover -s controller`
- **Per wave merge:** `tests/agents/run.sh`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `agents/loops/meeting-eval.jsonl` — ≥20 seed cases for LRN-02 (seeds for A1-verified trial shapes)
- [ ] `controller/test_feedback.py` — covers LRN-01 (closed kinds, dedupe, unknown-run refusal)
- [ ] Eval runner script (`agents/eval/run.py` or equivalent) — covers LRN-02/LRN-03 (`--fixture` offline + live gateway path + PR post)
- [ ] Promotion-check script — covers LRN-04 (registry-read thresholds, seed exclusion, INSUFFICIENT DATA)
- [ ] `tests/agents/checks/learning.sh` — executable check joining `run.sh` auto-discovery (covers OPS-03 static + LRN-02/03/04 probes)
- [ ] `agents/loops/testdata/eval-fixtures/` — canned pages + canned model outputs for offline eval proof

## Security Domain

Applicable — `security_enforcement` is `true`, ASVS level 1 (`nyquist_validation` also `true`; both read from `.planning/config.json:20-48` this session).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | Yes | GitHub App 1-hour installation tokens via broker; no long-lived tokens; Boole App `hyprn-platform`-only scope |
| V3 Session Management | Partial | Parked runs hold DB rows, never processes; resume strictly sender==owner [VERIFIED: controller/dispatcher.py:116-128] |
| V4 Access Control | Yes | Improvement/eval paths read only loop-declared secrets from reviewed YAML; ruleset + human merge gate; agents never merge |
| V5 Input Validation | Yes | Trigger/page content untrusted (ADR-0006 rule 3); `origin` closed set; feedback `kind` closed set; eval JSONL schema-checked; validator rejects bad autonomy [VERIFIED: agents/loops/validate.py:40-43] |
| V6 Cryptography | No new crypto | Reuse broker RS256 minting; no hand-rolled signing in new code |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Meeting-page instruction injection ("approve this now") | Tampering / Elevation | Injection guard: page text quoted as data, never followed; extraction proposes only [VERIFIED: agents/loops/meeting/prompts.md:3-10] |
| Stranger approval (`yes` from non-owner) | Spoofing | `resume` sender==owner gate; scoped question text with run+page id |
| Seed results presented as real (metric forgery) | Tampering | Mandatory `origin` labeling; promotion counts real-only; reports print both tallies |
| Secret exfil via eval fixtures/PR bodies | Information disclosure | Extend meeting.sh secret-pattern guard to eval file + runner output; values never printed (shapes only) |
| Scope-creep autonomy flip in improvement diff | Elevation of privilege | Eval gate rejects any `meeting.yaml`/`autonomy` change in improvement PRs |

## Sources

### Primary (HIGH confidence)

- `controller/schema.sql:1-21`, `controller/dispatcher.py:1-169`, `controller/test_dispatcher.py:1-80` — run state, gates, fake pattern (Read this session)
- `controller/poll_notion.py:15-17,52-59,73-134` — idempotency, envelope minimalism, fixture mode (Read this session)
- `agents/loops/meeting.yaml:1-33`, `agents/loops/validate.py:16-47` — registry contract, eval_set pointer, promotion rule (Read this session)
- `agents/loops/meeting/prompts.md:1-52`, `agents/loops/meeting/skills/notion-slack-shapes.md:1-42` — rubric, shapes, approval scoping (Read this session)
- `agents/host/files/hyprn-meeting-workflow:1-243`, `hyprn-run-runner:1-49`, `hyprn-credential-broker:1-135` — workflow, runner, broker fixture seams (Read this session)
- `tests/agents/run.sh:1-62`, `checks/{controller,github,loops,runner,meeting}.sh` — harness + check idioms (Read this session)
- `agents/marketplace/plugins/slack/slack-app-manifest.yaml:1-31` — scopes + subscribed events (Read this session)
- `docs/specs/agent-fleet.md §8/§9/§10` (lines 114-142) — feedback/eval/promotion normative requirements (Read this session)
- `runbooks/agents/github.md:1-44`, `infra/agents/boole.tf:1-73` — App creation flow + Boole secret declaration (Read this session)

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` OPS-03/LRN-01..04 + `.planning/ROADMAP.md` Phase 5 + `05-CONTEXT.md` — scope bindings (Read this session; planning docs, not code)

### Tertiary (LOW confidence)

- A1–A4 assumptions (gh-under-broker-token, gateway reachability, Socket-Mode timing, eval model binding) — marked `[ASSUMED]`, each with a fallback; confirm at trial go-checkpoint, not in-phase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; everything probed or read in-repo this session.
- Architecture: HIGH — all five capabilities map to existing check-covered patterns with verbatim quotes.
- Pitfalls: HIGH — each grounded in an existing guard or an explicit CONTEXT constraint.

**Research date:** 2026-10-14
**Valid until:** 30 days (stable domain: repo-internal patterns; only external drift is vendor consoles, which are owner steps)
