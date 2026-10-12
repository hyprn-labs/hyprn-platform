# conventions

Naming and ownership rules: company namespace `hyprn`, each hosted product under its own product codename (`hyprn-mvp` for the first product), environments `local`, `staging`, `prod`, components `app`, `modeling`, `execution`, `worker`. Physical names `hyprn-<environment>-<role>[-<instance>]`. Never a person's name, a partner or a phase number in durable identities.

Exception: agent personas (for example Ada) may appear in per-agent identities only — Linux user, Slack app, GitHub App, secret names — never in cloud resources, which stay role-named ([ADR-0001](../docs/adr/0001-agent-fleet.md)).
