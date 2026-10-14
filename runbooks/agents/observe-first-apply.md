# Observe-first apply manifest: Phase 1 staged host apply (EGR-01)

Owner direction: observe-first — the proxy ALLOWS all destinations and LOGS
per agent; enforcement comes later (Phase 7, EGR-02). This is the exact file
list for the FIRST host apply (Phase 1 only). The apply itself is an owner-go
host step per AGENTS.md; no step here runs from agent automation.

## In scope: exact host files (FIRST apply)

| # | Repo file | Host destination | Purpose |
|---|-----------|------------------|---------|
| 1 | `agents/host/files/egress.nft` | `/etc/hyprn-agents/egress.nft` | nftables observe rules: DNS allowed first, proxy ports accepted, direct 80/443 dropped for login + container UIDs |
| 2 | `agents/host/files/squid-hyprn.conf` | `/etc/squid/conf.d/hyprn.conf` | Squid observe config: allow-all on 3128 ada / 3129 codd with `%lp` per-agent logging; no deny, no allowlist reference |
| 3 | `agents/host/files/hyprn-agents-egress.service` | `/etc/systemd/system/` | Oneshot unit loading `/etc/hyprn-agents/egress.nft` at boot |

Provisioning additionally installs Squid itself (`apt-get install -y squid` —
owner-go), then runs `squid -k parse` before every reload and enables the
egress unit. `agents/host/provision.sh` does not render the Squid conf yet;
the conf install above is a manual owner-go step until provisioning covers it.

## Explicitly out of scope (not in this apply)

- `agents/policy/egress-allowlist.txt`: the future Phase 7 list (declared
  destinations complete; observed section intentionally empty). It is
  UNENFORCED in observe mode — provisioning must not render it to
  `/etc/squid/hyprn-allowlist.acl` until the Phase 7 flip
  (`runbooks/agents/egress-enforce.md`).
- Anything from Phases 2–7: telemetry collector, herdr units, OpenCode policy
  changes, the enforce-variant Squid config, container-only gateway scoping.
- Secret/token units (`hyprn-agent-secrets@`, `hyprn-agent-github-token@`):
  pre-existing, not Phase 1 — no change in this apply.
- Alerts (DET-01/02): Terraform (`infra/agents/detect.tf`, plan 01-04), a
  separate reviewed plan/apply, not a host-file apply.

## Static walk-through: egress.nft is correct for observe (no edit needed)

File order proves DNS-before-drop and proxy-forcing (verified by grep at
correction time; re-run before the apply):

1. Lines 22–23: `skuid 20000-20999 ... dport 53 accept` (TCP+UDP) precede
   every drop rule (lines 30–31) — DNS stays allowed and first (D-05).
2. Lines 27–28: proxy ports `{3128, 3129}` accepted for login UIDs
   (20000–20999) and container subordinate ranges (100000–231071).
3. Lines 30–31: direct outbound `{80, 443}` dropped for the same two UID
   ranges — traffic is forced via the proxy; the drops are firewall-level,
   not proxy blocking, so observe mode still logs everything.
4. Container DNS needs no explicit rule: the table default policy is accept,
   so subordinate-UID port-53 traffic not matching any rule is allowed.
5. Metadata block (lines 24–25) preserved ahead of the new rules.

## Verify after apply (owner-go, on the host)

```bash
sudo tests/agents/checks/egress.sh
```

Proves per-agent DNS, direct-drop (user + container), proxied success
including an arbitrary allow-all destination, per-port log entries, and the
Cloud Logging flow query. Roadmap success criterion 4 in observe mode.
