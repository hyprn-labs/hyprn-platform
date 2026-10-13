# Engineering workflow: tasks, draft PRs, cockpit, telemetry

How Ada turns Slack tasks into draft pull requests, how Codd works from the
terminal, and how the owner sees every session in one cockpit. Laptop install,
seat sign-in and host apply are owner-go steps and are never automated.

## One task, one worktree, one draft PR

Ada (Slack-driven) and Codd (terminal-driven) share one contract:

1. Create the worktree on branch `agent/<name>/<slug>`:
   - Ada: `WORKTREE_INDEX=<n> ada-task <slug>` (shared helper in
     `agents/host/files/bin/`; index-derived ports, Compose project and test
     DB, so two concurrent tasks never collide).
   - Codd: `opencode-task <slug>` (unchanged; Codd keeps its own helper).
2. Work in the worktree. Product-side overrides (port, Compose project,
   database from environment) are deferred to `hyprn-mvp`; the helper works
   without them and picks them up via `PRODUCT_*` env when provided.
3. Open a **draft** pull request whose body carries both headings, then stop.
   The agent never merges (managed-policy deny rules plus the `main` ruleset
   backstop per Phase 1 D-01/D-02):

   ```markdown
   ## What changed
   - <one line per change>

   ## How verified
   - <command and result, e.g. tests/agents/run.sh: PASS>
   ```

   Codd's App covers both repositories (`hyprn-platform` and `hyprn-mvp` per
   Phase 1 D-03/D-04); product tasks use the product checkout worktree.
4. After the owner merges or closes: `ada-task cleanup <slug>` (same
   `WORKTREE_INDEX`) removes the worktree, the local branch, the
   Compose-project volumes, the test database and the sibling env file.
   Codd: `git worktree remove` as in `runbooks/agents/opencode.md`.

Env contract per worktree (written to sibling file `~/work/<slug>.env`, never
inside the worktree): `WORKTREE_INDEX`, `APP_PORT` (`20000 + index*100`),
`APP_PORT_TEST` (port + 1), `COMPOSE_PROJECT_NAME`
(`hyprn-wt-<index>-<slug>`), `TEST_DB` (`hyprn_test_wt<index>`).

## Cockpit (COK-01): laptop plus host in herdr — owner checklist

The laptop runs herdr as the cockpit; the host runs one herdr server per agent
(`herdr@<name>.service`, pinned release, checksum-verified). The tmux wrapper
(`hyprn-agent@.service`) stays installed but disabled as fallback.

### A. Laptop herdr install (owner hands, once per laptop)

- [ ] Install herdr `0.9.4` (must equal `HERDR_VERSION` in
      `agents/host/provision.sh`; same pin on laptop and host or attach fails
      with version skew). Verify: `herdr --version` prints `herdr 0.9.4`.
- [ ] One Claude Code config dir per seat (`~/.config/claude-<seat>` with
      `GH_CONFIG_DIR`/`CLOUDSDK_CONFIG` equivalents per seat); seats sign in
      with their own Claude Team Standard seat, never a shared login.
- [ ] Remote Control on the **owner seat only**; agent seats never enable it.
- [ ] `herdr machine add hyprn-agents-host-01 -- over IAP SSH` (same
      `gcloud compute ssh ... --tunnel-through-iap` shape as the runbooks),
      then proof: `herdr machine status hyprn-agents-host-01` prints
      `reachable` (or the established reachable wording — paste it verbatim).

### B. Host herdr apply (owner go, per reviewed plan)

Authority rule: apply exactly the reviewed provision plus units plus policy
diff, never more. Removals get their own go.

- [ ] Review `git diff` for `agents/host/provision.sh`,
      `agents/host/files/herdr-session`, `agents/host/files/herdr@.service`,
      `agents/policy/managed-settings.json` (deny entries unchanged).
- [ ] Approve and run `agents/host/apply.sh` on the host.
- [ ] Post-apply: `tests/agents/run.sh` on the host shows no FAIL.
- [ ] Reboot proof: `herdr` sessions return after boot
      (`herdr session list` shows the agent sessions; Slack/wake/checks green).
- [ ] On failure: re-enable the tmux fallback
      (`systemctl enable --now hyprn-agent@<name>.service`) and record it below.

### C. Seat harness panes (owner, once per agent after apply)

- [ ] Start the seat harness inside herdr (`herdr agent start` in the agent's
      pane with its channel args from
      `/etc/hyprn-agents/agents/<name>.args`); agent-to-agent prompting stays
      off — never run `herdr agent prompt` from a seat pane (denied by policy).

## Telemetry and terms (OBS-01, CODD-03)

Seat Claude Code sessions export OTEL metrics and logs to the host-local
collector (`OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`, export
intervals lowered to 10 s / 2 s against batch loss). The collector config lives
in `agents/host/files/telemetry-collector.conf` (loopback only, per-agent
per-day buckets); the collector binary itself installs at apply time (pinned
release plus checksum gate, herdr treatment).

Collector-vs-scrape decision (spike 2026-10-13): a trivial local OTLP listener
on 127.0.0.1:4317 received a seat-shaped http/protobuf batch without loss, so
the host-local collector is viable. Until the owner-go apply installs it,
`ada-digest` runs in fallback aggregate-file mode: zeros with the lower-bound
caveat, never invented numbers.

`agents/host/files/bin/ada-digest` posts the daily per-agent digest
(`cron 15 7 * * *`, holds the host via `/run/hyprn-agents/hold` while posting).
Every post states the lower-bound caveat and attributes cost instead of
estimating it (Ada: Team seat subscription; Codd: free tier — no metered price
table exists to multiply by). The post carries tokens, limit hits and cost
attribution only — never prompts, goals or token values.

CODD-03 monthly re-check: `ada-digest --zen-check` compares the configured
Codd model against the Zen model list and prints the terms verdict; the owner
confirms and records the dated row below (stale after 31 days, `checks/obs.sh`
fails honestly). Protective-terms swap on the company move is configuration
(`model`/`small_model` in `agents/host/files/opencode.json` plus apply), never
retirement.

Apply-time migrations (owner, with the provision apply): existing seats keep
their old `~/.claude/settings.json` (provision only writes it when missing) —
merge the OTEL env block in by hand; resolve the hyprn-mvp toolchain pins
(gap: no checkout was readable when EFF-01 was written, host set stands as
fallback) and replace the `*_PIN` floor values with product pins; install the
pinned collector binary.

## Record

| Date | Action | Result |
|---|---|---|
| | | |
