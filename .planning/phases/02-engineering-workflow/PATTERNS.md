# Phase 2: Engineering workflow - Pattern Map

**Mapped:** 2026-10-13
**Files analyzed:** 10
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `agents/host/files/bin/opencode-task` successor (shared worktree helper, e.g. `ada-task`) | utility (shell helper) | file-I/O (git worktree) + request-response (session exec) | `agents/host/files/bin/opencode-task` | exact |
| `agents/marketplace/plugins/slack/server.py` (task-tag extension) | service | event-driven (Socket Mode inbound) | `agents/marketplace/plugins/slack/server.py` (self) | exact |
| `agents/host/files/bin/gh` usage in GH-01 PR flow (no change or thin extension) | utility | request-response (GitHub API via wrapper) | `agents/host/files/bin/gh` (self) | exact |
| `agents/host/files/herdr-session` + `herdr@.service` (new; replace tmux wrapper) | service runtime / config | streaming (long-lived session) | `agents/host/files/hyprn-agent-session` + `agents/host/files/hyprn-agent@.service` | role-match |
| `agents/host/provision.sh` + `agents/host/apply.sh` (toolchain/herdr/collector/unit deltas) | config (provisioning) | batch | `agents/host/provision.sh` (self) | exact |
| `tests/agents/checks/worktree.sh` (new, GH-02) | test | file-I/O + integration | `tests/agents/checks/codd.sh` + `runbooks/agents/opencode.md:40-44` | role-match |
| `tests/agents/checks/github.sh` (extend, GH-01/GH-03) | test | request-response (live API) + static | `tests/agents/checks/github.sh` (self) | exact |
| `tests/agents/checks/herdr.sh` (new, COK-02) | test | streaming + integration | `tests/agents/host-checks.sh` + `tests/agents/checks/session.sh` | role-match |
| `tests/agents/checks/eff.sh` (new, EFF-01/02) | test | batch + file-I/O | `tests/agents/host-checks.sh:17-18,29-36` | role-match |
| `tests/agents/checks/obs.sh` (new, OBS-01/CODD-03) | test | event-driven + batch (cron digest) | `tests/agents/checks/session.sh` (live-marker pattern) | role-match |
| `runbooks/agents/engineering-workflow.md` (new) | config (docs/runbook) | request-response (operator procedure) | `runbooks/agents/opencode.md` + `runbooks/agents/github.md` + `runbooks/agents/slack.md` | role-match |

## Pattern Assignments

### Worktree helper successor (utility, file-I/O)

**Analog:** `agents/host/files/bin/opencode-task` (22 lines, whole file is the pattern)

**Imports/shell preamble pattern** (lines 1-9):
```bash
#!/usr/bin/env bash
# One task = one branch agent/<agent>/<task> = one worktree ~/work/<task>:
# creates them from the latest hyprn-platform main if needed, then runs OpenCode
# there in a tmux session named after the task, which survives disconnects and is
# reattached by running the same command again.
set -euo pipefail
task="${1:?usage: opencode-task <task-name>}"
[[ "$task" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] && [ "$task" != hyprn-platform ] \
  || { echo "opencode-task: use lowercase letters, digits and dashes" >&2; exit 1; }
```

**Core worktree pattern** (lines 10-22) — copy verbatim, then add env-derivation + session-exec swap:
```bash
base="$HOME/work/hyprn-platform"
branch="agent/$(id -un)/$task"
dir="$HOME/work/$task"
[ -d "$base" ] || git clone -q https://github.com/hyprn-labs/hyprn-platform "$base"
git -C "$base" fetch -q --prune origin
if [ ! -d "$dir" ]; then
  if git -C "$base" show-ref --quiet --verify "refs/heads/$branch"; then
    git -C "$base" worktree add -q "$dir" "$branch"
  else
    git -C "$base" worktree add -q "$dir" -b "$branch" origin/main
  fi
fi
exec tmux new-session -A -s "$task" -c "$dir" opencode
```

**Cleanup pattern** (from `runbooks/agents/opencode.md:40-44`):
```bash
sudo -u codd -H bash -lc "git -C ~/work/hyprn-platform worktree remove ~/work/<task>"
# Phase 2 adds: && git -C <base> branch -d "agent/<name>/<slug>"
# + per-worktree Compose volume/DB removal (COMPOSE_PROJECT_NAME-keyed)
```
**Phase 2 delta:** keep slug regex + fetch/prune + reopen-if-exists; insert index-derived env (port block, `COMPOSE_PROJECT_NAME`, `TEST_DB` per RESEARCH Pattern 1) between worktree-add and exec; swap final `exec tmux ...` for herdr/tmux session exec; `${VAR:-default}` on every product env read (Pitfall 6).

---

### `agents/marketplace/plugins/slack/server.py` task-tag extension (service, event-driven)

**Analog:** `agents/marketplace/plugins/slack/server.py` (self-extend)

**Routing pattern** (lines 185-223) — add TASK_TAG alongside VERDICT, do not touch transport:
```python
def _on_event(self, event):
    kind = event.get("type")
    if kind == "message":
        if event.get("channel_type") != "im" or event.get("subtype") or event.get("bot_id"):
            return
    elif kind != "app_mention":
        return
    self._deliver(event)
```
```python
def _deliver(self, event):
    user = event.get("user", "")
    if user not in self.allowed:
        log("dropped message from a sender not on the allowlist")
        return 0
    channel, ts = event.get("channel", ""), event.get("ts", "")
    if not self._mark_seen(f"{channel}:{ts}"):
        return 0
```

**Allowlist + dedupe to preserve** (lines 35-37, 130-146):
```python
VERDICT = re.compile(r"^\s*(y|yes|n|no)\s+([a-km-z]{5})\s*$", re.IGNORECASE)
CATCH_UP_SECONDS = 900
CATCH_UP_DELAYS = (5, 30, 90)  # repeated: harmless, delivered messages are skipped
```
```python
def _mark_seen(self, key):
    with self.lock:
        if key in self.seen:
            return False
        self.seen.append(key)
        os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
        with open(SEEN_FILE, "w", encoding="utf-8") as handle:
            json.dump(list(self.seen), handle)
        return True
```

**Reply path for digest + task ack** (lines 253-258, `REPLY_TOOL` lines 47-59):
```python
def reply(self, chat_id, text, thread_ts=None):
    payload = {"channel": chat_id, "text": text, "unfurl_links": False, "unfurl_media": False}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    result = slack_api("chat.postMessage", self.bot_token, payload)
    return result.get("ok", False), result.get("error", "")
```
**Phase 2 delta:** `TASK_TAG = re.compile(r"^\s*task:\s*([a-z0-9][a-z0-9-]{0,40})\s+(.+)$", re.IGNORECASE | re.DOTALL)` checked in `_deliver` after the VERDICT block; on match `notify("notifications/hyprn/task", {...})` alongside existing channel notify. Constraints: stdlib-only (no new imports beyond `re`), never include secrets in replies (INSTRUCTIONS lines 39-45), keep 5/30/90 s catch-up + `seen.json` dedupe (Pitfall 2).

---

### `gh` wrapper + draft-PR flow (utility, request-response)

**Analog:** `agents/host/files/bin/gh` (whole file, lines 1-5) + `agents/host/files/hyprn-agent-github-token` (broker)
```bash
#!/usr/bin/env bash
# gh for agent users: always the current GitHub App token from tmpfs (ADR-0005).
token_file="/run/hyprn-agents/secrets/$(id -un)/github-token"
[ -r "$token_file" ] && GH_TOKEN="$(cat "$token_file")" && export GH_TOKEN
exec /usr/bin/gh "$@"
```

**Token-mint pattern** (`agents/host/files/hyprn-agent-github-token:34-43`) — no change, GH-01 relies on it:
```bash
dir="/run/hyprn-agents/secrets/$AGENT"
install -d -m 0711 /run/hyprn-agents/secrets
install -d -m 0500 -o "$AGENT" -g "$AGENT" "$dir"
umask 0377
tmp="$dir/.github-token.tmp"
rm -f "$tmp"
printf '%s\n' "$token" > "$tmp"
chown "$AGENT:$AGENT" "$tmp"
mv "$tmp" "$dir/github-token"
```

**PR body contract** (from `runbooks/agents/opencode.md:36` + RESEARCH): `gh pr create --draft --title "<slug>: <goal>"` with `## What changed` + `## How verified` body; never `gh pr merge` (deny-refused). Git identity is the bot (`user.email ...[bot]@users.noreply.github.com`, cf. `provision.sh:141-142`).
**Phase 2 delta:** no new auth code; helper/docs emit the fixed body shape; `checks/github.sh` asserts it statically.

---

### herdr units: `herdr-session` + `herdr@.service` (service runtime, streaming)

**Analog:** `agents/host/files/hyprn-agent-session` (23 lines) + `agents/host/files/hyprn-agent@.service` (18 lines)

**Session-loop pattern** (`hyprn-agent-session:1-9,16-23`) — copy structure, swap tmux/claude resume for herdr server start:
```bash
#!/usr/bin/env bash
# Long-lived Claude Code session for one agent, run inside tmux by
# hyprn-agent@<name>.service. Resumes the previous conversation after a boot.
set -uo pipefail
. /etc/profile.d/hyprn-agents.sh
export DISABLE_AUTOUPDATER=1
# Channel servers must use the pre-2026 MCP handshake (channels reference).
export MCP_PROTOCOL_NEGOTIATION=legacy
cd "$HOME/work"
```
```bash
while true; do
  if compgen -G "$PROJECT_DIR/*.jsonl" >/dev/null; then
    claude --continue "${ARGS[@]}"
  else
    claude "${ARGS[@]}"
  fi
  sleep 10
done
```
Keep: `set -uo pipefail`, profile sourcing, `ARGS_FILE` read (`hyprn-agent-session:11-13`), restart loop with backoff.

**Unit pattern** (`hyprn-agent@.service:1-18`):
```ini
[Unit]
Description=hyprn agents: Claude Code session for %i
After=network-online.target hyprn-agents-egress.service hyprn-agent-secrets@%i.service user@.service
Wants=network-online.target hyprn-agent-secrets@%i.service
Requires=hyprn-agents-egress.service

[Service]
Type=forking
User=%i
Group=%i
WorkingDirectory=~
ExecStart=/usr/bin/tmux new-session -d -s agent /usr/local/libexec/hyprn-agent-session
ExecStop=/usr/bin/tmux kill-session -t agent
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```
Keep: `%i` per-agent instantiation, `User=%i`/`Group=%i`, ordering after egress + secrets + `user@.service`, `Restart=on-failure`. Swap `ExecStart/ExecStop` to herdr server launch; keep old unit disabled-but-present as fallback (CONTEXT lock). Linger stays: `loginctl enable-linger "$name"` (`provision.sh:124`).

---

### `provision.sh` / `apply.sh` toolchain + herdr + collector deltas (config, batch)

**Analog:** `agents/host/provision.sh` (self-extend)

**Pinned-binary pattern** (lines 8-12, 90-106) — template for herdr pin + checksum:
```bash
CLAUDE_CODE_VERSION="2.1.287"
DOCKER_KEY_FPR="9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
OPENCODE_VERSION="1.19.0"
OPENCODE_SHA256="7bb9e61ad6feacf2e89c10a6a2c1840e3de4220bb50ba1fc7110f31806076aec"  # opencode-linux-x64.tar.gz
```
```bash
install_opencode() {
  log "OpenCode $OPENCODE_VERSION"
  local dest=/usr/local/lib/opencode tmp
  if ! "$dest/opencode" --version 2>/dev/null | grep -qF "$OPENCODE_VERSION"; then
    tmp="$(mktemp -d)"
    curl -fsSL -o "$tmp/opencode.tar.gz" \
      "https://github.com/anomalyco/opencode/releases/download/v$OPENCODE_VERSION/opencode-linux-x64.tar.gz"
    echo "$OPENCODE_SHA256  $tmp/opencode.tar.gz" | sha256sum -c --quiet
    tar -xzf "$tmp/opencode.tar.gz" -C "$tmp"
    install -d -m 0755 "$dest"
    install -m 0755 -o root -g root "$(find "$tmp" -type f -name opencode | head -1)" "$dest/opencode"
    rm -rf "$tmp"
  fi
```

**Signing-key gate pattern** (lines 25-40):
```bash
  install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.asc ]; then
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  fi
  gpg --show-keys --with-colons /etc/apt/keyrings/docker.asc | grep -q "^fpr:::::::::${DOCKER_KEY_FPR}:" \
    || { echo "unexpected Docker signing key" >&2; exit 1; }
```

**Per-agent setup pattern** (lines 108-133): `add_agent` case-dispatch on harness, 0700 home, subuid/subgid, linger + bus-wait, rootless-docker ensure:
```bash
  loginctl enable-linger "$name"
  for _ in $(seq 1 30); do [ -S "/run/user/$uid/bus" ] && break; sleep 1; done
```

**Ship pattern** (`agents/host/apply.sh:1-14`):
```bash
set -euo pipefail
: "${CLOUDSDK_CONFIG:?set CLOUDSDK_CONFIG to the gcloud configuration dedicated to hyprn.ai}"
cd "$(git rev-parse --show-toplevel)"
tar -czf - agents/host agents/roles agents/marketplace tests/agents |
  gcloud compute ssh "$HOST" --zone="$ZONE" --project="$PROJECT" --tunnel-through-iap --quiet --command \
    'set -e; rm -rf ~/hyprn-provision; mkdir ~/hyprn-provision; tar -C ~/hyprn-provision -xzf -;
     sudo bash ~/hyprn-provision/agents/host/provision.sh;
     sudo bash ~/hyprn-provision/tests/agents/host-checks.sh'
```
**Phase 2 delta:** new `install_herdr()` mirroring `install_opencode()` (pinned version var + SHA var + root-owned dest); toolchain additions inside `install_base()` with key-fingerprint gates; per-agent cache dirs + OTEL env + digest cron inside `add_agent()`; extend the `apply.sh` tar list only if new top-level dirs appear.

---

### `tests/agents/checks/worktree.sh` (new, GH-02 — test, file-I/O)

**Analog:** `tests/agents/checks/codd.sh` (check-script style) + `runbooks/agents/opencode.md:40-44` (cleanup semantics)

**Check-script style** (`codd.sh:1-15`):
```bash
#!/usr/bin/env bash
# Codd scope checks (CODD-01, D-03/D-04): ...
# Host-executed portions run as root on the agent host.
# Exits non-zero if any check fails.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
MANAGED="$REPO_ROOT/agents/host/files/opencode.json"
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
```

**Live/static split** (`github.sh:35-47`):
```bash
# Live per-agent installation assertions (agent host only): ...
# Off-host (no such local user) the checks SKIP so the script stays runnable
# for static review anywhere; on the host they are strict.
while read -r name uid harness _; do
  if ! id "$name" >/dev/null 2>&1; then
    skip "$name: App installation covers both repositories" "no local user $name (not on agent host)"
    continue
  fi
```
with `skip() { echo "SKIP $1 ($2)"; }` (`github.sh:16`).

**Runner contract** (`tests/agents/run.sh:41-46`): every executable `checks/*.sh` auto-runs; each must be executable, print `PASS/FAIL/SKIP` lines, exit non-zero on failure; `run.sh` appends dated row to `runbooks/agents/checks-<date>.md`.
**Phase 2 coverage:** two concurrent worktrees (ports/Compose/DB isolated per RESEARCH Pattern 1); cleanup leaves no worktree (`git worktree list`), branch, volume, or DB; static greps (helper has index-derivation, `${VAR:-default}`, `*_TEST` fail-fast guard). `bash -n` + `shellcheck` per-commit gate.

---

### `tests/agents/checks/github.sh` extension (GH-01/GH-03 — test, request-response)

**Analog:** `tests/agents/checks/github.sh` (self-extend)

**Static JSON/policy pattern** (lines 18-33):
```bash
check "ruleset file is valid JSON" "python3 -m json.tool '$RULESET'"
check "ruleset bypass actor list is empty (no App bypass)" "[ \"\$(jq -r '.bypass_actors | length' '$RULESET')\" = 0 ]"
check "no ruleset write/apply call in this plan's files" "! grep -rqE 'gh api .*repos/.*rule""sets.*(--method|-X) *(POST|PUT|PATCH)|rule""sets --input' '$REPO_ROOT/agents/github' '$HERE/github.sh'"
```

**Live installation pattern** (lines 44-46):
```bash
check "$name: App installation covers both repositories" "run 'gh api installation/repositories --jq .repositories[].full_name' | sort | diff - <(printf 'hyprn-labs/hyprn-mvp\nhyprn-labs/hyprn-platform\n')"
check "$name: App installation total count is 2" "[ \"\$(run 'gh api installation/repositories --jq .total_count')\" = 2 ]"
```
**Phase 2 delta:** add GH-01 static greps (PR body template has `## What changed` + `## How verified`; helper creates `agent/<name>/<slug>`; no `gh pr merge` in helper/server — mirror deny rule `Bash(gh pr merge*)` in `managed-settings.json:11`); live bot-author + draft assertion marked **gated on Phase 1 green** (RESEARCH Ordering §); add GH-03 negative grep (no `hyprn-ada` account refs, no `ada-agent-github-token` secret).

---

### `tests/agents/checks/herdr.sh` (new, COK-02 — test, streaming)

**Analog:** `tests/agents/host-checks.sh` (per-agent loop + service assertions) + `tests/agents/checks/session.sh` (live markers)

**Per-agent loop pattern** (`host-checks.sh:21-22,29-42`):
```bash
while read -r name uid harness _; do
  run() { runuser -l "$name" -c "$1" </dev/null; }
  check "$name: home is private" "[ \"\$(stat -c %a /home/$name)\" = 700 ]"
  ...
  check "$name: Slack tokens private to the agent" "[ ! -e /run/hyprn-agents/secrets/$name/slack.env ] || [ \"\$(stat -c %U:%a /run/hyprn-agents/secrets/$name/slack.env)\" = $name:400 ]"
```

**Service-active + version-pin pattern** (`host-checks.sh:15-18`):
```bash
check "idle-stop timer active" "systemctl is-active --quiet hyprn-idle-stop.timer"
check "OpenCode at the pinned version" "/usr/local/lib/opencode/opencode --version | grep -qF $OPENCODE_VERSION"
```
where `OPENCODE_VERSION="$(sed -n 's/^OPENCODE_VERSION="\(.*\)"/\1/p' ...provision.sh)"` (line 9) — herdr check derives `HERDR_VERSION` the same way.

**Live-marker pattern** (`session.sh:16-18`) for owner-laptop steps that cannot automate (COK-01 `machine status` reachable):
```bash
live() { [ -f "$LIVE/$1.ok" ] && head -1 "$LIVE/$1.ok" | grep -qE '^20[0-9]{2}-[0-9]{2}-[0-9]{2}' && sed -n '2p' "$LIVE/$1.ok" | grep -qE '^owner: .'; }
```
**Phase 2 coverage:** unit active (`systemctl --user is-active` via `runuser`), herdr version pin + checksum recorded, p2p/agent-prompting off, hooks allowlisted in policy (grep POL-01), tmux fallback unit present-but-disabled, regression = full `run.sh` pass after switch.

---

### `tests/agents/checks/eff.sh` (new, EFF-01/02 — test, batch)

**Analog:** `tests/agents/host-checks.sh:17,29-36`

```bash
check "OpenCode at the pinned version" "/usr/local/lib/opencode/opencode --version | grep -qF $OPENCODE_VERSION"
```
```bash
  if [ "$harness" = claude ]; then
    check "$name: Claude Code installed" "run 'claude --version'"
```
```bash
  else
    check "$name: OpenCode runs" "run 'opencode --version' | grep -qF $OPENCODE_VERSION"
```
**Phase 2 coverage:** EFF-01 = fresh-worktree `--version` pins match product pins (same `grep -qF $PIN` shape, pin vars read from `provision.sh` like line 9); EFF-02 = cache-marker persistence (write marker to per-agent cache vol, run helper cycle + best-effort reboot check, marker survives; static grep that cache paths are sibling dirs keyed by worktree, never inside the worktree — anti-pattern RESEARCH §).

---

### `tests/agents/checks/obs.sh` (new, OBS-01/CODD-03 — test, event-driven/batch)

**Analog:** `tests/agents/checks/session.sh` (live-marker + allowlist-precondition shape)

```bash
check "relay precondition: allowlist root-owned, owner only" "[ \"\$(stat -c %U:%a '$ALLOWLIST_FILE')\" = root:644 ]"
check "relay: owner yes proceeds" "live relay-owner-yes"
```

**Digest-delivery path** reuses `server.py:253-258` `reply()` via bot token (OBS-01 posts through the existing reply path, not a new bot).
**Phase 2 coverage:** collector reachability (OTEL endpoint `http://localhost:4317` from seat env — RESEARCH Code Examples telemetry block), digest dry-run exit 0, digest states lower-bound (Pitfall 4 flush loss), CODD-03 staleness grep (dated runbook row ≤ 31 days) mirroring `live()` date-first-line shape; real daily post observed = manual `live` marker.

---

### `runbooks/agents/engineering-workflow.md` (new — docs/runbook, request-response)

**Analog:** `runbooks/agents/opencode.md` (procedure + record table) + `runbooks/agents/github.md` (owner-go checklists) + `runbooks/agents/slack.md` (secret-shape discipline)

**Procedure + contract pattern** (`opencode.md:28-44`):
```markdown
## Use
From the laptop, one terminal or herdr pane per task (...):
\```bash
CLOUDSDK_CONFIG=... gcloud compute ssh ... -- -t 'sudo -u codd -H bash -lc "opencode-task <task>"'
\```
`opencode-task` clones ... creates the worktree ... Codd opens a draft pull request; the owner reviews and merges.
...
After merge, remove the worktree:
\```bash
sudo -u codd -H bash -lc "git -C ~/work/hyprn-platform worktree remove ~/work/<task>"
\```
```

**Owner-go step pattern** (`github.md:17-24`, `slack.md:12-25`): numbered console/secret steps with `pbpaste | ... --data-file=-` (value never on screen), shape-only verification (`xapp-`/`xoxb-` prefixes), then `agents/host/apply.sh`.

**Dated-record pattern** (`opencode.md:58-65`, `github.md:34-44`, `slack.md:52-66`): `| Date | Action/Step | Result |` table, one row per run, host-check counts as evidence.
**Phase 2 sections:** helper use + env contract, PR body contract (shared by Ada + Codd), cockpit owner checklist (COK-01: laptop install, per-seat config dirs, Remote Control, `machine add` over IAP SSH — all `checkpoint:human-verify`, never automated), digest/CODD-03 cycle. Must state: agent never merges; laptop/host applies are owner-go; secrets by shape only.

---

## Shared Patterns

### Shell-script preamble (all `agents/host/files/bin/*`, `provision.sh`, `checks/*.sh`, `host-checks.sh`)
**Source:** `agents/host/files/bin/opencode-task:6`, `agents/host/provision.sh:4`, `tests/agents/run.sh:7`
```bash
set -euo pipefail   # checks use `set -uo pipefail` (github.sh:8, codd.sh:9, session.sh:9, host-checks.sh:4) — no `-e` because fail-accumulating `check()` must continue
```
Helpers/provision use `set -euo pipefail`; checks use `set -uo pipefail` + `fail=0` accumulator + `exit $fail`. Path resolution: `HERE="$(cd "$(dirname "$0")" && pwd)"`, `REPO_ROOT="$(cd "$HERE/../../.." && pwd)"`.

### Check-function idiom (all `checks/*.sh`, `host-checks.sh`)
**Source:** `tests/agents/checks/github.sh:15-16`, `tests/agents/host-checks.sh:8`
```bash
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }
skip() { echo "SKIP $1 ($2)"; }
# ...
exit $fail
```
Per-agent live sections: `run() { runuser -l "$name" -c "$1" </dev/null; }` (`codd.sh:19`, `github.sh:44`, `host-checks.sh:22`) guarded by `if ! id "$name" >/dev/null 2>&1; then SKIP (not on agent host)`. Owner-laptop truths use `live()` markers (`session.sh:18`).

### Authentication / secrets (broker + tmpfs + shape-only)
**Source:** `agents/host/files/hyprn-agent-github-token:34-43`, `agents/host/files/bin/gh:3-4`, `runbooks/agents/slack.md:58`
- GitHub: root broker mints 1-hour App tokens → `$AGENT:400` tmpfs file → `gh` wrapper injects `GH_TOKEN`. Never long-lived tokens, never machine accounts (GH-03 negative grep).
- Slack: `xapp-`/`xoxb-` in Secret Manager → tmpfs `slack.env`; allowlist is member IDs (`U`/`W`, never `A` app IDs); server never writes secrets (`server.py:9-11`).
- Discipline: check tokens by shape only, never print values (AGENTS.md:31-36).

### Authorization backstop (deny rules → ruleset)
**Source:** `agents/policy/managed-settings.json:4-15,28`
```json
"deny": ["Bash(git push *main*)", "Bash(git push *:main*)", "Bash(git push *+*)", "Bash(git push *--force*)", "Bash(git push * -f*)", "Bash(git -C * push *)", "Bash(gh pr merge*)", "Bash(gh pr merge *--admin*)", "Bash(gh api repos/*/branches/main/protection*)", "Bash(gh api *merge*)"],
"disableBypassPermissionsMode": "disable"
```
Every Phase 2 helper/check that touches git/GitHub must keep these families green; `checks/github.sh:19` asserts empty `bypass_actors`; plans never include an agent merge step.

### Slug validation (helper + server tag)
**Source:** `agents/host/files/bin/opencode-task:8`
```bash
[[ "$task" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] && [ "$task" != hyprn-platform ] \
```
Server-side TASK_TAG reuses the same `([a-z0-9][a-z0-9-]{0,40})` group; quote every slug interpolation (STRIDE tampering mitigation, RESEARCH Security Domain).

### Harness runner + records (ACC-08)
**Source:** `tests/agents/run.sh:1-14,41-62`
`run.sh` runs `host-checks.sh` then every executable `checks/*.sh` in a guarded invocation (one domain never masks the next), exits non-zero on any failure, appends `| Script | Result |` + `Overall:` row to `runbooks/agents/checks-<date>.md`. New Phase 2 scripts need only be executable with that PASS/FAIL contract — no runner change.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Host OTEL collector config + digest aggregator internals | service | event-driven → batch | No collector/aggregator exists in-repo; RESEARCH Pattern 4 (OTEL env + `claude_code.*` metrics) is the source. Planner spikes collector-vs-direct-scrape (Wave 0 Q3) with digest-script-only fallback |
| herdr laptop cockpit config (per-seat dirs, `machine add` over IAP) | config | streaming | Laptop-side herdr has no in-repo precedent; spec §4 + `herdr machine add/status` CLI docs are the source; COK-01 is owner-checklist + `live` marker, not automation |
| Per-worktree port/Compose/DB index-derivation values | utility fragment | file-I/O | Community pattern (RESEARCH Pattern 1, henrietteharmse/wkoorts citations); no in-repo port-stride precedent — helper adds it fresh with `${VAR:-default}` + `*_TEST` fail-fast guards |

## Metadata

**Analog search scope:** `agents/host/`, `agents/marketplace/plugins/slack/`, `agents/policy/`, `tests/agents/`, `runbooks/agents/`
**Files scanned:** 15 tracked files (all `git ls-files`-verified; no mirror paths)
**Pattern extraction date:** 2026-10-13
