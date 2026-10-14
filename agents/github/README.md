# agents/github

Repository protection for `hyprn-labs` repositories ([agent fleet specification](../../docs/specs/agent-fleet.md), section 13).

- `main-ruleset.json` — the ruleset on `main` in every repository: no deletion, no force push, changes only through a pull request approved by a code owner (`CODEOWNERS`), with stale approvals dismissed and the last push approved by someone else. Organization admins may merge their own pull requests (bypass in pull-request mode only); agents' GitHub Apps have no bypass. Applied once `hyprn-labs` is on the GitHub Team plan ([runbook](../../runbooks/agents/github.md)).
