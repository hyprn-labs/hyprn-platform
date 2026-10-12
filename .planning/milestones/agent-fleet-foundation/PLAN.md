# Plan: agent fleet

Decision: [ADR-0001](../../../docs/adr/0001-agent-fleet.md). First agent: Ada (email, Claude seat and Slack app done).

**Owner** steps are run by the platform owner after an explicit go for that step; the exact commands and console steps are prepared in the linked runbook first, and the runbook records what was actually done, without secrets. **Repo** steps are files in this repository, reviewed before use.

Execution order: 0 → A → B → D → E; C waits for the repositories to be published on GitHub. E needs B and D; pull-request metrics need C.

## 0. Groundwork

| # | Who | Task | Done when |
|---|---|---|---|
| 0.1 | Repo | Folders with READMEs, ADR-0001, this plan | Committed; listed in `docs/adr/README.md` |

## A. Project `hyprn-agents` ([runbook](../../../runbooks/agents/README.md))

| # | Who | Task | Done when |
|---|---|---|---|
| A1 | Owner | Check whether a Google Cloud organization exists for `hyprn.ai` (`gcloud organizations list`, `gcloud billing accounts list`, read-only) | Organization and billing account IDs recorded in the runbook |
| A2 | Owner | Security key on the owner's account; break-glass super admin with an offline key; group `gcp-admins` holds the cloud admin roles; billing account created; domain-wide Project Creator and Billing Account Creator grants removed after A3 | Organization and billing IAM list groups and service accounts only |
| A3 | Owner | Organization policies: no service-account keys, no default network, OS Login, Shielded VMs, private uniform buckets, EU locations only; folder `agents` without external IPs; project `hyprn-agents` linked to billing; budget 100 EUR with alerts at 50/80/100 %; enable Compute, IAP, OS Login, Secret Manager, Logging, Monitoring, IAM only | Policies effective; no Editor or Owner binding for any service account; budget visible |
| A4 | Owner | Service account `hyprn-agents-host`: log and metric writer, `secretAccessor` on named secrets only | Its roles are exactly that list |
| A5 | Repo + Owner | Isolation check in `tests/agents/`: organization-wide IAM search for project principals | They appear only inside `hyprn-agents`; re-run scheduled for when staging and prod exist |
| A6 | Repo | Terraform root `infra/agents/`, state in the project's own bucket, import of A3–A4 and B1–B2 | `terraform plan` shows no changes (plan reviewed, nothing applied without a go) |

## B. Agent host ([`agents/host/`](../../../agents/host/README.md))

| # | Who | Task | Done when |
|---|---|---|---|
| B1 | Owner | VPC and subnet (no default network); ingress TCP 22 from `35.235.240.0/20` only; Cloud NAT; Private Google Access | Firewall list shows only that ingress rule |
| B2 | Owner | VM `hyprn-agents-host-01`: `t2d-standard-8` on demand ([ADR-0002](../../../docs/adr/0002-agent-host-on-demand.md)), 100 GB balanced disk, Debian 12, Shielded VM, no public IP, OS Login, project SSH keys blocked, VM identity `hyprn-agents-host` | `gcloud compute ssh --tunnel-through-iap` works; no external IP exists |
| B3 | Repo | Provisioning: Linux user per agent (private home, no sudo), rootless Docker per user, metadata server blocked for agent users, root-owned secret helper, pinned Claude Code at 2.1.234 or later | As `ada`: metadata request fails, other homes unreadable, `docker run` works rootless |
| B4 | Owner | Sign in as `ada` with `/login` (emailed code); role instructions from `agents/roles/` installed | `/status` shows Ada's seat; Ada reads the working repository's `AGENTS.md` |
| B5 | Repo | Persistent session in tmux under a systemd unit | Session returns after a reboot |
| B6 | Repo | Worktree helper: branch `agent/<name>/<slug>`, its own worktree, its own port block, Compose project name and test database name as environment variables | Two worktrees run tests side by side without collisions (limited until the product reads these overrides) |
| B8 | Repo | Idle auto-stop on the host (30 minutes without agent work or SSH); wake service in `agents/wake/` on `hyprn-agents-wake-01` | Host stops when idle and keeps its disk; a Slack message from the owner starts it and the agent answers |
| B7 | Repo | No-production-credentials check | No user cloud credentials, key files, or staging/prod roles on the host |

## D. Slack control ([`agents/marketplace/`](../../../agents/marketplace/README.md), [`agents/policy/`](../../../agents/policy/README.md))

| # | Who | Task | Done when |
|---|---|---|---|
| D1 | Repo | Shortlist and audit a community Slack channel plugin: Socket Mode only; sender allowlist by Slack user ID, also for permission replies; tokens read from files; outbound only to Slack; pinned dependencies; licence allows vendoring | Audit record written; source vendored with upstream commit |
| D2 | Repo | Marketplace `.claude-plugin/marketplace.json`; installed on the host as a root-owned local directory | The agent user lists the plugin from the local marketplace |
| D3 | Owner | Admin console, organization-wide: enable channels; `allowedChannelPlugins`, `strictKnownMarketplaces`, `disableBypassPermissionsMode`, permission and sandbox rules as in `agents/policy/` | Ada starts with `--channels` without the development flag; bypass mode is refused |
| D4 | Owner | Ada's Slack tokens from the password manager into Secret Manager; owner's Slack user ID in the allowlist (secret store, not Git); invite Ada only to working channels | Tokens reach Ada only through the helper |
| D5 | Repo + Owner | Acceptance | Owner's instruction acts; other senders ignored; a risky action asks in Slack; an approval from anyone else is rejected |

## C. GitHub (after publication)

| # | Who | Task | Done when |
|---|---|---|---|
| C1 | Owner | GitHub organization on the Team plan; human team for code owners | Plan active; team exists |
| C2 | Owner | App `hyprn-ada`: Contents RW, Pull requests RW, Metadata R, no Workflows or Administration, selected repositories; private key into the password manager and Secret Manager | App installed on the working repositories only |
| C3 | Repo | Token helper: one-hour installation tokens for git and `gh`; author `hyprn-ada[bot]` | Ada pushes `agent/ada/*` and opens a draft pull request |
| C4 | Owner | Ruleset on `main`: pull request, code-owner approval (human teams only), stale approvals dismissed, no force push, no App bypass | Ruleset active on every working repository |
| C5 | Repo + Owner | Acceptance | Merge by the App refused; push to `main` refused; App-only approval does not satisfy the rule |

## E. Measurement, first week with Ada ([`agents/measurement/`](../../../agents/measurement/README.md))

| # | Who | Task | Done when |
|---|---|---|---|
| E1 | Repo | OpenTelemetry export per agent to a collector on the host; daily report of tokens, estimated API-equivalent cost and seat-limit hits; Team admin analytics read daily | Day-one report exists |
| E2 | Owner + Repo | One week of real tasks; extra usage off, so limit hits are visible | Seven daily reports |
| E3 | Repo | Summary: limit hits per day and window, API-equivalent cost against the seat price, queue wait | Owner decides Standard or Premium, seats or API keys, and when to add agent #2; recorded in a follow-up ADR |

## Gates

- Agent #2 waits for Anthropic's human answer on agent seats (ADR-0001, section 1).
- Part C waits for the repositories to exist on GitHub.
- Per-worktree isolation is complete only once the product reads port, Compose project and database overrides from the environment (product work, not planned here).
