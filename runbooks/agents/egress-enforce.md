# Egress enforcement: flip, rollback, first observation (EGR-02)

Reviewed enforcement procedures for the observe-to-enforce flip. The flip
itself is an owner-go host apply; this runbook is the reviewed procedure the
owner follows. No step here runs from agent automation.

## Render and flip (owner-go)

Render runs on the host at provisioning/apply time. It strips comment lines
(starting with `#`) and blank lines from `agents/policy/egress-allowlist.txt`,
sorts unique, and installs the result as the generated ACL:

```bash
REPO=<checkout of hyprn-platform>
grep -vE '^\s*(#|$)' "$REPO/agents/policy/egress-allowlist.txt" | sort -u > /tmp/hyprn-allowlist.acl
# Fail-closed render gate: empty output aborts and keeps the old ACL file.
[ -s /tmp/hyprn-allowlist.acl ] || { echo "allowlist render empty; refusing" >&2; exit 1; }
cp -a /etc/squid/hyprn-allowlist.acl /etc/squid/hyprn-allowlist.acl.prev 2>/dev/null || true
cp -a /etc/squid/conf.d/hyprn.conf /etc/squid/conf.d/hyprn.conf.prev 2>/dev/null || true
install -m 0644 /tmp/hyprn-allowlist.acl /etc/squid/hyprn-allowlist.acl
install -m 0644 "$REPO/agents/host/files/squid-hyprn.conf" /etc/squid/conf.d/hyprn.conf
```

Host-time confirmations before reload (RESEARCH A1 and open questions):

1. Confirm the leading-dot `dstdomain` subdomain form against the host Squid
   version (`squid -v`). Safe fallback: explicit per-FQDN entries for each
   observed hostname instead of relying on subdomain coverage.
2. Confirm which log shipper is present (ops-agent tailing
   `/var/log/squid/access.log` with the local-port field as agent label, else
   the host syslog shipper fallback).

Then pre-check and reload only on success:

```bash
squid -k parse && systemctl reload squid
```

Verify with the per-agent no-break drill: for ada, codd, and the Boole loop
path (shared container path via the owning user's port), an allowed
destination succeeds via login and container, a disallowed destination is
refused (HTTP 403) with a log entry under the agent port label, and direct
bypass (`curl --noproxy '*'`) still drops. See `tests/agents/checks/egress.sh`
for the drill assertions.

## One-command rollback to observe mode

If any drill probe fails, restore the saved previous config plus ACL and
reload. The rollback is reviewed and shipped with the flip (not improvised):

```bash
cp -a /etc/squid/conf.d/hyprn.conf.prev /etc/squid/conf.d/hyprn.conf \
  && cp -a /etc/squid/hyprn-allowlist.acl.prev /etc/squid/hyprn-allowlist.acl \
  && squid -k parse && systemctl reload squid
```

The rollback changes no other system state. nftables needs no rollback: the
drop-direct rules were never changed (they force traffic through the proxy in
both modes).

## First live observation update procedure (first-observation)

Observe mode never ran live, so the allowlist's observed section ships empty.
After the owner-set observation window of enforced-with-review operation:

1. Export per-agent destinations from Cloud Logging (same query shape as the
   log-flow check in `tests/agents/checks/egress.sh`, widened to destination
   fields and the full window).
2. `sort -u` the export and diff against `agents/policy/egress-allowlist.txt`.
3. Owner reviews the diff in a PR; legitimate routine destinations are added
   under the observed section header with mined date and record reference.
4. Provisioning re-renders and reloads per the render-and-flip procedure above.
5. Post-acceptance tuning stays out of scope (deferred per Phase 7 CONTEXT).
