# agents/policy

Reviewed copies of the policies that govern agents ([agent fleet specification](../../docs/specs/agent-fleet.md), section 13):

- `managed-settings.json` — the Claude Code organization policy the Team Owner applies in the admin console: channels and allowed channel plugins, known marketplaces, allow, ask and deny permission rules, sandbox settings, the pinned herdr hooks and `disableBypassPermissionsMode`. The console enforces it; each change is reviewed here first and recorded in `runbooks/agents/claude.md`.
- `egress-allowlist.txt` — the domains the egress proxy allows, built from observed traffic and enforced in milestone M3.
