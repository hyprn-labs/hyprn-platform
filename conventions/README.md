# conventions

Naming and ownership rules: company namespace `hyprn`, each hosted product under its own product codename (`hyprn-mvp` for the first product), environments `local`, `staging`, `prod`, components `app`, `modeling`, `execution`, `worker`. Physical names `hyprn-<environment>-<role>[-<instance>]`. Never a person's name, a partner or a phase number in durable identities.

Agent personas (for example Ada) appear in per-agent identities only, never in cloud resources, which stay role-named ([ADR-0001](../docs/adr/0001-agent-fleet.md)):

| Identity | Pattern | Ada |
|---|---|---|
| Email (Google Group) | `<name>@agents.hyprn.ai` | `ada@agents.hyprn.ai` |
| Display name (Claude, Slack, GitHub, Git) | `<Name> (AI agent)` | Ada (AI agent) |
| GitHub machine account | `<name>-agent-hyprn` | `ada-agent-hyprn` |
| Linux user on the agent host | `<name>` | `ada` |
| Secrets | `agent-<name>-<purpose>` | `agent-ada-github-token` |
| Git branches | `agent/<name>/<slug>` | `agent/ada/fix-readme` |
