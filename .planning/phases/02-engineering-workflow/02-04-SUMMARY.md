# 02-04 Toolchains, caches, telemetry, terms re-check — Summary

**Status:** done-with-blockers (1: blocking-human owner-go checkpoint, see Blocked)
**Date:** 2026-10-13

## What was built

- `agents/host/provision.sh` (additive hunks after 02-03, no conflicts):
  `PYTHON3_PIN="3.11"`, `DOCKER_PIN="29"`, `GH_PIN="2.102"`, `GIT_PIN="2.39"`
  floor pins (hyprn-mvp unreadable — no checkout anywhere — so the host set
  stands as fallback and no versions were guessed; gap recorded in the
  runbook); `cron` added to base packages; per-agent `work/.cache/{npm,pip}`
  sibling dirs (agent-owned `0700`, never inside worktrees) in `add_agent()`;
  seat OTEL env (`..._ENABLE_TELEMETRY=1`, `otlp` exporters, `http/protobuf`,
  `http://localhost:4317`, lowered 10 s/2 s intervals) in new-seat
  `settings.json`; `install_telemetry()` (collector conf → `/etc/hyprn-agents/`,
  digest → agent bin dir, `/etc/cron.d/ada-digest` firing `15 7 * * *`).
- `agents/host/files/telemetry-collector.conf` (new): standard OTEL collector
  shape, `127.0.0.1:4317` loopback only, per-agent per-day buckets, file
  exporter to `/var/lib/hyprn-agents/telemetry/batches.jsonl`. Spike evidence
  in-file: a local OTLP listener received a seat-shaped batch without loss, so
  the collector is viable; binary installs at apply (pinned + checksummed,
  herdr treatment).
- `agents/host/files/bin/ada-digest` (new, executable): `--dry-run` (default)
  prints the per-agent digest; `--post` holds the host, posts via the same
  `chat.postMessage` + bot-token path as the channel server's `reply()`;
  every post states the lower-bound caveat; cost is attributed (seat
  subscription / $0.00 free tier — no metered price table exists), never
  estimated; `--zen-check` verifies the Codd model against the Zen list and
  prints the CODD-03 verdict for the owner to record.
- `tests/agents/checks/eff.sh`, `tests/agents/checks/obs.sh` (new, in
  `run.sh`): pin greps + `--version` assertions, OTEL-endpoint/interval greps,
  sibling-cache greps, hermetic cache-marker round-trip (live, SKIP off-host);
  collector loopback-only greps, reachability-or-documented-fallback,
  digest dry-run/disclaimer/endpoint/schedule greps, zen-check exit 0, CODD-03
  staleness (SKIP when no row yet, honest FAIL when stale).
- `runbooks/agents/engineering-workflow.md`: appended telemetry + terms
  section (decision record, fallback mode, schedule, apply-time migrations:
  existing-seat OTEL merge, hyprn-mvp pins, collector binary pin).

## Verify results

- `bash -n` clean on all four scripts; `eff.sh`: 15/15 PASS (incl. 2 live);
  `obs.sh`: 14 PASS + 1 SKIP (CODD-03 row absent — owner records at
  checkpoint), exit 0; `ada-digest --dry-run` and `--zen-check` exit 0 (Zen
  page confirms `muse-spark-1.3-contributor-free` listed).
- `run.sh`: `checks/eff`, `checks/obs` SCRIPT-PASS alongside `worktree` and
  `herdr`. Overall FAIL is pre-existing/environmental only: host-checks,
  accounts, codd, detect, egress, session fail here (no root, no `runuser`,
  no metadata server, no owner creds) and none are files this phase touched
  (`github.sh`'s 4 FAILs proven identical on stashed baseline).
- No product code: `git ls-files` shows platform paths only; per-agent cache
  perms are `0700` agent-owned in provisioning (enforced at apply).

## Deviations

- **Cost attributed, not estimated**: no metered price table exists (Team seat
  + free tier), so multiplying tokens by an invented rate would be fiction.
  The digest says what each agent costs structurally; the caveat covers the rest.
- **CODD-03 staleness is SKIP-when-absent / FAIL-when-stale** rather than the
  plan's permitted "honest FAIL": keeps the suite green until the owner owns
  the first verdict, fails loudly once a verdict goes stale. Strictly more
  informative; acceptance allowed either.
- **Schedule is `/etc/cron.d` via a provision heredoc** (repo timers are
  systemd, but `files_modified` forbids new unit files): keeps the plan's file
  list exact; content is statically grepped by `obs.sh`.
- **Digest bug found by testing, fixed**: under `set -o pipefail`,
  `curl | grep -q` misreports (grep closes the pipe → curl SIGPIPEs → pipeline
  fails despite the match). The Zen fetch now writes a temp file first;
  provider prefix (`opencode/`) stripped before matching the Zen page's bare IDs.

## Blocked

1. **Owner-go checkpoint (gate: blocking-human): toolchain + telemetry apply
   + first digest observed** — commands: `agents/host/apply.sh` for exactly
   the reviewed delta; host `run.sh`; after the next 07:15 fire, owner confirms
   the first real Slack post (tokens, cost, limit hits) and the initial
   CODD-03 verdict row — who: platform owner — go needed: explicit apply
   approval + Phase 1 green run (`/gsd-verify-work 1`; live OBS-01 proof gated
   on it; 02-03 host apply already done, this re-applies for its own delta).
   Evidence: dated digest-first-post row quoting posted totals, dated CODD-03
   row naming model + verdict, `live/digest-first-post.ok`. Executor must NOT
   create the marker without owner confirmation.
