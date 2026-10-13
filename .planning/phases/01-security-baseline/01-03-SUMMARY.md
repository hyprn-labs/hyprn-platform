# 01-03 Summary: egress observation (firewall + proxy + checks)

**Status:** done-with-blockers (3 host-side items need the agent host)
**Date:** 2026-10-13

## Tasks done

1. **Extend the firewall to drop direct egress** — extended
   `agents/host/files/egress.nft` in observe mode per D-05: existing
   metadata block and DNS port-53 allowances untouched and first; added
   proxy-port accepts (3128/3129) and direct 80/443 drops for both the
   agent login UID range (20000-20999) and the subordinate container
   ranges (union 100000-231071, read from the host `/etc/subuid`
   allocation: ada 100000:65536, codd 165536:65536). Header records the
   wake-placement finding (below). Service unit description updated to
   cover egress observation; oneshot load/unload shape kept.
2. **Configure the explicit proxy with per-agent attribution** — created
   `agents/host/files/squid-hyprn.conf` (ports 3128 ada / 3129 codd,
   per-port ACLs, `hyprn` log format with `%lp` local-port agent
   identifier, no blocking rules per D-06). Header documents the Cloud
   Logging ship path, proxy-env delivery, and D-05.
3. **Add the egress check script with live drop tests** — created
   `tests/agents/checks/egress.sh` (table state, drop rules for login +
   container ranges, DNS-first ordering, metadata block, proxy ports,
   proxy listen state, per-user DNS/drop/proxy trio, per-container
   drop/proxy pair, Cloud Logging flow query). Standalone-runnable,
   picked up by the `run.sh` glob.

## Verify results

- `EGRESS_CHECKS_OK` (bash -n clean, ≥5 named checks — 13 defined)
- `SQUID_CONF_OK` (listen-port + access-log directives present)
- `nft --check`: **could not run** — no `nft` binary in this worktree
  (see Blocked 1). File reviewed line-by-line against the existing
  table idiom instead.
- DNS port-53 allowances (file lines 10-11) precede every drop rule
  (lines 30-31) in file order — confirmed by diff.
- `tests/agents/host-checks.sh` re-run after commit: fails
  environmentally (needs root), as before.

## Deviations

- **Wake-placement finding (plan-directed discovery):** the wake service
  runs on `hyprn-agents-wake-01`, a separate always-on VM (ADR-0002,
  `agents/wake/README.md`) — wake traffic never traverses the agent host.
  Recorded in the `egress.nft` header per the plan; host scope not
  silently extended. Wake-side observation is a follow-up.
- **Shipper unconfirmed:** no ops-agent reference exists in the repo, so
  the Squid header documents ops-agent tail as primary with host-syslog
  fallback and requires confirmation at provisioning (RESEARCH open
  question 2).
- **Container proxy address assumes `host.containers.internal`**
  resolves from rootless containers; flagged in `checks/egress.sh` for
  the host run to prove or correct.

## Blocked

1. **`nft --check -f agents/host/files/egress.nft` must run on the agent
   host** (no `nft` binary in this worktree; loading the table additionally
   needs root). Who: owner/host hands. Go needed: owner go per AGENTS.md
   for the exact host step; the table load itself (`systemctl restart
   hyprn-agents-egress`) is a host change under the same go.
2. **Live drop tests (user + container) and proxy-listen checks must run
   as root on the agent host:** `sudo tests/agents/checks/egress.sh`.
   Needs root (`runuser`, `nft`, `ss`), Squid installed + rendered config,
   and proxy env delivered. Squid install (`apt-get install -y squid`,
   RESEARCH) is an owner-go provisioning step — terraform is not involved.
3. **Cloud Logging flow query needs the host identity + ops-agent:**
   `gcloud logging read ... --project=hyprn-agents` from the host after
   log shipping is confirmed. Owner-go; proves roadmap criterion 4 with
   the drop tests.
