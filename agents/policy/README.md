# agents/policy

Reviewed copies of the policies that govern agents ([agent fleet specification](../../docs/specs/agent-fleet.md), section 13). A change is made here first, by pull request, then applied; the host checks compare what is live with these files.

- `managed-settings.json` — the Claude Code organization policy, pasted unchanged into the Claude admin console by the Team Owner ([runbook](../../runbooks/agents/claude.md)). It applies to every Claude Code session of the organization, the owner's included: Slack channels with only our Slack plugin, plugins only from the root-owned marketplace on the agent host, Anthropic's official marketplace and skills-directory plugins (plugins synced from claude.ai are not marketplace plugins and are unaffected), bypass mode disabled, and deny rules on pushing to `main`, force pushing, deleting branches, merging and changing repository protection.

Deny rules match the command text an agent writes; another spelling of the same action is not stopped. The ruleset on `main` (`agents/github/`) is the control GitHub enforces.
