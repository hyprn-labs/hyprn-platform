---
last_mapped_commit: a393bda2510b521148d626a02e4a5aef58dae1d6
last_mapped_at: 2026-10-13
---

# Technology Stack

**Analysis Date:** 2026-10-13

## Languages

**Primary:**
- HCL (Terraform configuration) - All cloud infrastructure in `bootstrap/`, `infra/agents/`, `infra/modules/`, `infra/environments/`
- Bash (`set -euo pipefail` scripts) - Host provisioning and verification: `agents/host/provision.sh`, `agents/host/apply.sh`, `agents/wake/provision.sh`, `agents/wake/apply.sh`, `agents/host/files/bin/gh`, `agents/host/files/bin/opencode`, `agents/host/files/bin/opencode-task`, `tests/agents/host-checks.sh`
- Python 3 (standard library only + one Debian package) - Wake service `agents/wake/wake.py` and Slack channel server `agents/marketplace/plugins/slack/server.py`
- YAML - Environment intents (`environments/staging/`, `environments/prod/`), Slack app manifest `agents/marketplace/plugins/slack/slack-app-manifest.yaml`, systemd units under `agents/host/files/` and `agents/wake/`
- JSON - Deployment contracts `contracts/v1/`, wake config `agents/wake/wake.json`, OpenCode policy `agents/host/files/opencode.json`, MCP manifest `agents/marketplace/plugins/slack/.mcp.json`

**Secondary:**
- Markdown (MADR decision records, specifications, runbooks) - `docs/adr/`, `docs/specs/`, `runbooks/`, per-directory `README.md` files
- nftables ruleset - Host egress firewall `agents/host/files/egress.nft`
- systemd unit syntax - `agents/host/files/*.service`, `agents/host/files/*.timer`, `agents/wake/hyprn-agents-wake.service`

**Not present:** No `package.json`, `go.mod`, `requirements.txt`, `Cargo.toml`, or `pyproject.toml` exist in the repo. Product code is intentionally excluded from this repository (`README.md`, `AGENTS.md`).

## Runtime

**Environment:**
- Terraform `>= 1.9` - Pinned floor in `bootstrap/versions.tf` and `infra/agents/versions.tf`
- Python 3 on Debian 12 (bookworm) - Both Python programs declare "Python 3 standard library and Debian's python3-websocket" in their module docstrings (`agents/wake/wake.py:10`, `agents/marketplace/plugins/slack/server.py:13`)
- Pinned Debian 12 image `debian-12-bookworm-v20261006` - Default for `host_image` in `infra/agents/variables.tf:49`; updated only by reviewed change, never by family lookup
- Google Compute Engine VMs - `hyprn-agents-host-01` (`t2d-standard-8`, 100 GB `pd-balanced`) and `hyprn-agents-wake-01` (`e2-micro`, 10 GB `pd-standard`) defined in `infra/agents/host.tf` and `infra/agents/wake.tf`

**Package Manager:**
- APT (Debian packages) on provisioned VMs - `apt-get` installs in `agents/host/provision.sh:21-44` and `agents/wake/provision.sh`
- Terraform provider registry - Single provider `hashicorp/google` (see Frameworks)
- No language-level package manager (no pip/npm/go modules); Python dependency `python3-websocket` comes from APT, not pip
- Lockfile: missing (no `.terraform.lock.hcl` committed; provider version is constrained by `~> 8.6` range instead)

## Frameworks

**Core:**
- Terraform with `hashicorp/google` provider `~> 8.6` - Owns all cloud resources (`bootstrap/versions.tf:7`, `infra/agents/versions.tf:7`); GCS backends `hyprn-bootstrap-tfstate` and `hyprn-agents-tfstate`
- systemd (user + system) - Agent sessions `agents/host/files/hyprn-agent@.service`, secret loader `agents/host/files/hyprn-agent-secrets@.service`, GitHub token broker `agents/host/files/hyprn-agent-github-token@.service`, egress `agents/host/files/hyprn-agents-egress.service`, idle-stop `agents/host/files/hyprn-idle-stop.*`, wake `agents/wake/hyprn-agents-wake.service`
- nftables - Host metadata/egress isolation loaded from `agents/host/files/egress.nft` (verified by `tests/agents/host-checks.sh:14`)
- Rootless Docker per agent - Installed in `agents/host/provision.sh:130-133`; rootful daemon explicitly disabled (`agents/host/provision.sh:47`)

**Testing:**
- Bash assertion script (no test runner framework) - `tests/agents/host-checks.sh` uses a `check` helper (`tests/agents/host-checks.sh:8`) and exits non-zero on any failure; run as root on the host
- Contract/policy test fixtures - Golden fixtures must render stable, unsafe fixtures must fail (`tests/README.md`); policy rules described in `policies/README.md`

**Build/Dev:**
- `gcloud` CLI - SSH (`infra/agents/outputs.tf:14`), secret loading (`runbooks/agents/slack.md`, `runbooks/agents/github.md`), operated with dedicated `CLOUDSDK_CONFIG` / `GOOGLE_APPLICATION_CREDENTIALS` / `GH_CONFIG_DIR` (`AGENTS.md:33`)
- `gh` (GitHub CLI, APT install with signing-key fingerprint pin) - `agents/host/provision.sh:12,34-44`; agents use the wrapper `agents/host/files/bin/gh` that injects the current App token
- Claude Code `2.1.287` (pinned, per-user install) - `agents/host/provision.sh:8,157`; harness `claude` in `agents/host/agents.txt`
- OpenCode `1.19.0` pinned tarball with SHA-256 checksum - `agents/host/provision.sh:10-11,90-106`; harness `opencode` in `agents/host/agents.txt`; root-owned policy `agents/host/files/opencode.json`
- `jq` - Used in host checks (`tests/agents/host-checks.sh:18,36`) and installed as a base package (`agents/host/provision.sh:21`)

## Key Dependencies

**Critical:**
- `hashicorp/google` Terraform provider `~> 8.6` - Every `google_*` resource in `bootstrap/*.tf` and `infra/agents/*.tf` depends on it
- Debian package `python3-websocket` - WebSocket client for Slack Socket Mode in `agents/wake/wake.py:20` and `agents/marketplace/plugins/slack/server.py:26`
- GitHub App per agent (`ada-agent-hyprn`, `codd-agent-hyprn`) - Minted installation tokens are the agents' only GitHub credential (`agents/host/agents.txt`, `docs/adr/0005-agent-github-app.md`)
- Slack per-agent app tokens (`xapp-…` app-level, `xoxb-…` bot token) - Read from Secret Manager by wake (`agents/wake/wake.py:79-80`) and from tmpfs by the channel server (`agents/marketplace/plugins/slack/server.py:116-120`)

**Infrastructure:**
- Docker CE + plugins (`docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-ce-rootless-extras`, `docker-compose-plugin`, `docker-buildx-plugin`) with GPG fingerprint pin `9DC858229FC7DD38854AE2D88D81803C0EBFCD88` - `agents/host/provision.sh:9,25-47`
- GitHub CLI APT repo with fingerprint allowlist - `agents/host/provision.sh:12,37-38`
- Base APT set: `ca-certificates curl gnupg git tmux jq nftables uidmap dbus-user-session slirp4netns fuse-overlayfs bubblewrap socat build-essential python3-venv python3-websocket unattended-upgrades` - `agents/host/provision.sh:21-23`
- Cloud NAT + Cloud Router (`google_compute_router_nat.agents`) - Outbound internet without public IPs (`infra/agents/network.tf:36-53`)

## Configuration

**Environment:**
- Terraform input variables, never committed secrets - `bootstrap/variables.tf` (`org_id`, `directory_customer_id`, `billing_account`, `admins_group`, regions/project IDs) and `infra/agents/variables.tf` (`project_id=hyprn-agents`, `region=europe-west1`, `zone=europe-west1-b`, machine types, `agents`, `slack_agents`)
- `bootstrap/terraform.tfvars` file present - Supplies the secret-adjacent IDs above; values are deployment-specific and must not be quoted (`.gitignore` excludes `*.auto.tfvars` and `secrets.tfvars`)
- Agent roster `agents/host/agents.txt` - One line per agent: name, UID, harness (`claude`|`opencode`), GitHub App slug/IDs, display name
- Wake static config `agents/wake/wake.json` - Project, zone, host name, Slack-steered agent list (`["ada"]`)
- OpenCode policy `agents/host/files/opencode.json` - Model `opencode/muse-spark-1.3-contributor-free`, providers limited to `["opencode"]`, denies pushes to `main`/force-pushes/merges
- MCP manifest `agents/marketplace/plugins/slack/.mcp.json` - Runs the channel server via `/usr/bin/python3 -I ${CLAUDE_PLUGIN_ROOT}/server.py`
- Slack app manifest `agents/marketplace/plugins/slack/slack-app-manifest.yaml` - Scopes, events (`app_mention`, `message.im`), Socket Mode enabled

**Build:**
- `bootstrap/versions.tf`, `infra/agents/versions.tf` - Terraform floor + provider pin + GCS backend
- `bootstrap/providers.tf`, `infra/agents/providers.tf` - Provider billing/quota wiring
- Pinned tool versions in `agents/host/provision.sh:8-12` (`CLAUDE_CODE_VERSION`, `OPENCODE_VERSION` + SHA, key fingerprints)

## Platform Requirements

**Development:**
- Terraform `>= 1.9` with application-default credentials of the bootstrap administrator; quota/billing routed to `hyprn-bootstrap` (`bootstrap/providers.tf`)
- `gcloud`, `gh`, `jq`, `curl` for runbook operations (`runbooks/agents/github.md`, `runbooks/agents/slack.md`)
- Dedicated identity configs `CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`, `GH_CONFIG_DIR` so commands run as the HYPRN identity, not a personal one (`AGENTS.md:33`)
- Root on the target VM to run `agents/host/provision.sh` / `agents/wake/provision.sh` (both abort otherwise)

**Production:**
- Google Cloud organization `hyprn.ai` with EU-only resource locations (`bootstrap/org_policies.tf:95-107`, region `europe-west1`)
- Projects `hyprn-bootstrap` (state/quota) and `hyprn-agents` (fleet) with GCS tfstate buckets `hyprn-bootstrap-tfstate`, `hyprn-agents-tfstate` (`bootstrap/bootstrap_project.tf`, `bootstrap/agents.tf`)
- Separate Terraform state per root; every apply uses a reviewed plan; staging and prod have separate state and authority (`README.md`, `AGENTS.md`)
- Company password manager (master copy of secret values) + Secret Manager (runtime copy); secret values never enter Terraform or Git (`infra/agents/secrets.tf:1-4`, `AGENTS.md:33`)

---

*Stack analysis: 2026-10-13*
