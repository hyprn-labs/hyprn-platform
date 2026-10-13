---
last_mapped_commit: a393bda2510b521148d626a02e4a5aef58dae1d6
last_mapped_at: 2026-10-13
---

# External Integrations

**Analysis Date:** 2026-10-13

## APIs & External Services

**Google Cloud (primary platform):**
- Organization guardrails via Org Policy API - 10 enforced policies plus domain/location constraints in `bootstrap/org_policies.tf` (secure-boot, OS Login, no default network, EU locations `in:eu-locations`, member domain allowlist)
- Compute Engine API - Host `hyprn-agents-host-01` in `infra/agents/host.tf` and wake `hyprn-agents-wake-01` in `infra/agents/wake.tf`; wake service calls `compute.instances.get/start/stop` over HTTPS with the VM service-account token (`agents/wake/wake.py:45-53,121`)
- Secret Manager API - All agent credentials read at runtime via `secretmanager.googleapis.com/v1/.../versions/latest:access` (`agents/wake/wake.py:56-58`); secret containers provisioned in `infra/agents/secrets.tf`
- Enabled API surface, agents project - `compute`, `iam`, `iap`, `logging`, `monitoring`, `oslogin`, `secretmanager`, `serviceusage`, `storage`, `cloudresourcemanager` in `bootstrap/agents.tf:41-53`; bootstrap project APIs in `bootstrap/bootstrap_project.tf:21-32`
- Cloud Billing Budgets API - Monthly EUR budget with 50/80/100% alert thresholds, alerts only, no cap (`bootstrap/agents.tf:103-127`; default 100 EUR in `bootstrap/variables.tf:39-43`)
- Essential Contacts API - Org-wide `ALL` notification subscription to the admins group (`bootstrap/org_policies.tf:108-114`)
- Cloud Identity (directory customer ID) - Constrains IAM policy members to the company directory (`bootstrap/org_policies.tf:47-58`, `bootstrap/variables.tf:6-9`)
  - SDK/Client: Terraform `hashicorp/google` provider `~> 8.6` (`bootstrap/versions.tf`, `infra/agents/versions.tf`); runtime calls use `urllib.request` with metadata-server tokens, no Google SDK (`agents/wake/wake.py:36-53`)
  - Auth: VM service accounts `hyprn-agents-host` (`infra/agents/iam.tf`) and `hyprn-agents-wake` (`infra/agents/wake.tf`); human access via `CLOUDSDK_CONFIG` / `GOOGLE_APPLICATION_CREDENTIALS` (`AGENTS.md:33`)

**Slack (agent control plane):**
- Per-agent Slack app over Socket Mode (`apps.connections.open` WebSocket; no public endpoint) - Wake service holds one connection per agent while the host is stopped (`agents/wake/wake.py:84-94`); channel server reconnects with backoff after disconnects (`agents/marketplace/plugins/slack/server.py:151-166`)
- Web API methods used: `apps.connections.open`, `chat.postMessage`, `auth.test`, `conversations.open`, `conversations.history`, `reactions.add` - See `agents/wake/wake.py:61-72` and `agents/marketplace/plugins/slack/server.py:97-111`
- App manifest (scopes `app_mentions:read`, `chat:write`, `im:history`, `im:write`, `reactions:write`; events `app_mention`, `message.im`; `socket_mode_enabled: true`) - `agents/marketplace/plugins/slack/slack-app-manifest.yaml`
- Channel plugin speaks MCP-over-stdio JSON-RPC to the harness (`initialize`, `tools/list`, `tools/call` with a `reply` tool, `notifications/claude/channel/permission_request`) - `agents/marketplace/plugins/slack/server.py:282-325`, launched via `agents/marketplace/plugins/slack/.mcp.json`
- Permission relay: agent permission requests posted to Slack; only allowlisted `yes <id>` / `no <id>` replies become verdicts - `agents/marketplace/plugins/slack/server.py:260-279`
  - SDK/Client: none; raw `urllib.request` + Debian `python3-websocket` (`agents/wake/wake.py:20`, `agents/marketplace/plugins/slack/server.py:26`)
  - Auth: `SLACK_APP_TOKEN` (`xapp-…`, `connections:write`) and `SLACK_BOT_TOKEN` (`xoxb-…`) from Secret Manager / tmpfs; allowlist `agents-slack-allowed-users` (JSON list of `U…`/`W…` IDs)

**GitHub (agent code access):**
- One GitHub App per agent owned by `hyprn-labs` (Ada: `ada-agent-hyprn` on all org repos; Codd: `codd-agent-hyprn` on `hyprn-platform` only), permissions Contents + Pull requests read/write, Metadata read, webhook inactive - `docs/adr/0005-agent-github-app.md:28`, `agents/host/agents.txt`, `runbooks/agents/github.md`
- Root-only broker on the host signs a JWT with the App private key (memory only) and mints one-hour installation tokens every 30 minutes into agent-private tmpfs - `docs/adr/0005-agent-github-app.md:30`; token freshness enforced by `tests/agents/host-checks.sh:41`
- Agent surface: `gh` wrapper injecting `GH_TOKEN` from tmpfs (`agents/host/files/bin/gh`) and git credential helper (`agents/host/files/hyprn-git-credential`); commits as `<app>[bot]@users.noreply.github.com` (`agents/host/provision.sh:141-143`)
  - SDK/Client: `gh` CLI (APT, fingerprint-pinned in `agents/host/provision.sh:12,34-44`) plus `git`
  - Auth: App private key in Secret Manager (`<name>-agent-github-app-key`, host-identity read-only per `infra/agents/secrets.tf:46-70`); agents never see the key

**AI model providers:**
- Anthropic Claude via Claude Code `2.1.287` (harness `claude`: Ada) - Per-user install, autoupdate disabled, Slack channel plugin from the local marketplace (`agents/host/provision.sh:156-176`); org-level Claude settings pin `channelsEnabled` + allowlisted `hyprn-agents/slack` plugin (`runbooks/agents/slack.md`)
- OpenCode with provider `opencode` only, model `opencode/muse-spark-1.3-contributor-free` (harness `opencode`: Codd) - Pinned tarball + SHA in `agents/host/provision.sh:10-11`, policy in `agents/host/files/opencode.json`
  - Auth: Claude seat sign-in per agent (session starts only once `~/.claude/.credentials.json` exists, `agents/host/provision.sh:179-185`); OpenCode provider auth via agent-side config, never in repo

**Package / OS mirrors (outbound through Cloud NAT):**
- `download.docker.com` (Docker CE APT repo, GPG-checked), `cli.github.com` (gh APT repo, fingerprint-checked), `claude.ai/install.sh`, `github.com/anomalyco/opencode/releases` (SHA-checked tarball) - `agents/host/provision.sh:25-44,95-101,158`
- Debian APT mirrors and `unattended-upgrades` for security updates - `agents/host/provision.sh:22,48`, `agents/wake/provision.sh`

## Data Storage

**Databases:**
- None. No database, ORM, or migration tooling detected in the repo. Product data schemas live in product repositories per `README.md:11`.

**File Storage:**
- GCS buckets for Terraform state only: `hyprn-bootstrap-tfstate` (`bootstrap/bootstrap_project.tf:49-80`) and `hyprn-agents-tfstate` (`bootstrap/agents.tf:70-101`); both versioned, uniform access, public-access-prevention enforced, `prevent_destroy`
- Agent homes are local VM disks (`/home/<name>`, mode `0700`); no shared/cloud filesystem

**Caching:**
- None. Wake polls instance status every 15 s (`agents/wake/wake.py:29,143`); channel server keeps in-memory deques (500 events/seen) plus a local `seen.json` for dedup (`agents/marketplace/plugins/slack/server.py:123-145`); GCP tokens cached in-process until expiry (`agents/wake/wake.py:42-49`)

## Authentication & Identity

**Auth Provider:**
- Google IAM + OS Login + IAP TCP forwarding - The only human path to VMs
  - Implementation: firewall `hyprn-agents-allow-iap-ssh` allows TCP/22 solely from `35.235.240.0/20` to the host/wake service accounts (`infra/agents/network.tf:17-32`); VMs set `enable-oslogin=TRUE`, `block-project-ssh-keys=TRUE` (`infra/agents/host.tf:28-31`, `infra/agents/wake.tf:71-74`); admins group gets `roles/iap.tunnelResourceAccessor` + `roles/compute.osAdminLogin` + `serviceAccountUser` on the host identity (`infra/agents/iam.tf:21-36`, `infra/agents/wake.tf:40-44`)
- Google Workspace group `gcp-admins@hyprn.ai` (default `var.admins_group`) - Holds owner/admin bindings (`bootstrap/bootstrap_project.tf:43-47`, `bootstrap/agents.tf:63-67`, `infra/agents/variables.tf:17-21`)
- Slack allowlist (`agents-slack-allowed-users` secret) - Only listed user IDs can instruct agents or approve actions; enforced identically in wake (`agents/wake/wake.py:113,130`) and channel server (`agents/marketplace/plugins/slack/server.py:194-198`)
- GitHub Apps per agent - Identity without seat/email/2FA; short-lived installation tokens; agent-scoped repository access (`docs/adr/0005-agent-github-app.md`, `runbooks/agents/github.md`)
- Workload Identity Federation conditions and GitHub repository protections (rulesets, required checks, CODEOWNERS) are specified for `governance/` but no workflow files exist in this repo yet (`governance/README.md`)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Bugsnag-style service detected)

**Logs:**
- Cloud Logging via `roles/logging.logWriter` on both VM identities (`infra/agents/iam.tf:10-18`, `infra/agents/wake.tf:11-20`); wake logs to stderr as `hyprn-wake:` (`agents/wake/wake.py:32-33`); channel server logs to stderr plus `~/.local/state/hyprn-slack/server.log` with rotation at 200 KB (`agents/marketplace/plugins/slack/server.py:64-74`)
- Cloud Monitoring metric-writer role granted (`roles/monitoring.metricWriter`); NAT logs errors only (`infra/agents/network.tf:49-52`)
- Operational records kept as runbook entries (`runbooks/`, `runbooks/agents/`)

## CI/CD & Deployment

**Hosting:**
- Google Compute Engine, region `europe-west1` / zone `europe-west1-b`, EU residency constraint (`infra/agents/variables.tf:7-15`, `bootstrap/org_policies.tf:95-107`)
- Network: `hyprn-agents-vpc` + `hyprn-agents-subnet` (`10.10.0.0/24`, private Google access) with no external IPs (`infra/agents/network.tf`, folder-level `compute.vmExternalIpAccess` deny in `bootstrap/agents.tf:9-18`); outbound via Cloud NAT; shielded VMs with secure boot + vTPM + integrity monitoring
- Product staging/prod hosting is specified (`docs/specs/cloud-platform.md`) with environment roots under `infra/environments/` and runtime bindings under `environments/`; Terraform owns cloud resources, the host reconciler owns the rendered runtime (`README.md:11`)

**CI Pipeline:**
- None detected (no `.github/workflows/`, `cloudbuild.yaml`, or equivalent in repo). Quality gates are the host checks (`tests/agents/host-checks.sh`), contract/policy fixtures (`tests/`, `policies/`), and reviewed Terraform plans (`README.md:34`, `AGENTS.md:28`)

## Environment Configuration

**Required env vars:**
- Terraform inputs, not process env: `org_id`, `directory_customer_id`, `billing_account`, `admins_group` (no defaults, `bootstrap/variables.tf:1-24`); everything else has defaults in `bootstrap/variables.tf` and `infra/agents/variables.tf`
- Operator shell identity routing: `CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`, `GH_CONFIG_DIR` must point at the HYPRN-dedicated configs (`AGENTS.md:33`)
- `GH_TOKEN` is derived at runtime from tmpfs by `agents/host/files/bin/gh`, never set by hand

**Secrets location:**
- Master copy: company password manager; runtime copy: Secret Manager in `hyprn-agents` (`AGENTS.md:33`, `infra/agents/secrets.tf:1-4`)
- Secret IDs follow `<name>-agent-<purpose>` (`conventions/README.md:13`): per-agent `<name>-agent-slack-app-token`, `<name>-agent-slack-bot-token`, `<name>-agent-github-app-key`, plus shared `agents-slack-allowed-users`
- Read access is per-secret to the host and/or wake identities only, never project-wide (`infra/agents/secrets.tf:34-42,65-70,91-99`); Terraform creates containers, values are loaded by the owner via `gcloud secrets versions add` (`runbooks/agents/slack.md`, `runbooks/agents/github.md`)
- On-host layout is root-owned tmpfs: `/run/hyprn-agents/secrets/<agent>/slack.env` (`<agent>:400`), `github-token` (`<agent>:400`), `slack-allowed-users.json` (`root:644`) - enforced by `tests/agents/host-checks.sh:16,38-39`
- Forbidden in repo: `*.tfstate`, `*.tfplan`, `secrets.tfvars`, `*.auto.tfvars`, `*.json.key`, `credentials/`, `.env*` (`.gitignore`)

## Webhooks & Callbacks

**Incoming:**
- None with a public endpoint. Slack arrives over outbound Socket Mode WebSockets; GitHub Apps have webhooks disabled (`docs/adr/0005-agent-github-app.md:28`); both VMs have no public IPs and ingress allows only IAP SSH (`infra/agents/network.tf:15-32`, `bootstrap/agents.tf:9-18`)

**Outgoing:**
- Slack Web API (`chat.postMessage` wake notice and replies, `reactions.add`, `conversations.open/history` catch-up) - `agents/wake/wake.py:115-119`, `agents/marketplace/plugins/slack/server.py:253-279`
- Compute Engine `instances.start` from the wake VM on an allowlisted DM/mention (`agents/wake/wake.py:120-126`)
- Secret Manager `versions:latest:access` reads for tokens and the allowlist (`agents/wake/wake.py:56-58`)
- GitHub `installation/repositories` reads and token-authenticated git/gh operations from agent sessions (`tests/agents/host-checks.sh:36,42`)

---

*Integration audit: 2026-10-13*
