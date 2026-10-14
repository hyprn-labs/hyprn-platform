# 07-01 Summary: Enforcement config (reviewed, no live state)

**Plan:** 07-01 (wave 1, EGR-02) — Completed allowlist, enforce-mode Squid
config with fail-closed render gate, flip/rollback/first-observation runbook,
one static end-to-end assertion slice. No host apply; no live state changed.

## Tasks

1. **Tracer: one declared domain enforced end-to-end (static)** — `github.com`
   under a declared header; Squid generated-ACL reference plus per-port allow
   stanzas and explicit per-port denies; one static enforce-shape check
   appended to `checks/egress.sh`. Verify green.
2. **Complete allowlist from declared destinations** — routine steady-state
   entries, commented provisioning-time section, container-only
   `gateway.internal` (EGR-03, Boole via owning user's port — no dedicated
   Boole Squid port exists), explicitly empty observed section. Verify green.
3. **Enforce render gate, rollback, and runbook** — `runbooks/agents/egress-enforce.md`
   with render gate, one-command rollback, first-observation procedure, and
   host-time A1 confirmation step; Squid header comments name the generated
   ACL path and fail-closed rule; `egress.nft` untouched. Verify green.

## Verify

- `bash -n tests/agents/checks/egress.sh` — clean.
- Tracer greps (allowlist `github.com`, Squid `dstdomain`) — pass.
- `ALLOWLIST-COMPLETE` loop over all six declared domains — pass.
- `RUNBOOK-OK` (rollback + observation procedure + `deny all` tail) — pass.
- One fix during execution: runbook header casing missed the plan's
  case-sensitive `first-observation` grep; added the literal token. No scope change.

## Known transitional state (plan-sequenced, not a defect)

The old observe-mode static assertion in `egress.sh` ("carries no blocking
rules") now fails against the enforce config by design; 07-02 replaces it
with the enforce-mode counterpart. Live probes untouched.

## Blocked

- **Owner-go checkpoint (in 07-02, not executed here):** the observe-to-enforce
  flip — owner follows `runbooks/agents/egress-enforce.md` on the host
  (confirm A1 subdomain form, render, `squid -k parse`, reload, per-agent
  no-break drill with rollback loaded). Agent must never run it.
- **Owner-go checkpoint (in 07-02, not executed here):** final aggregate
  `tests/agents/run.sh` green run with enforcement on and kept dated record
  (ACC-10). Agent must never run it.

## Files

- `agents/policy/egress-allowlist.txt` (modified)
- `agents/host/files/squid-hyprn.conf` (modified)
- `tests/agents/checks/egress.sh` (modified, one appended static check)
- `runbooks/agents/egress-enforce.md` (created)
- `agents/host/files/egress.nft` — deliberately untouched.
