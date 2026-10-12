# Runbook: agent host

The agent host `hyprn-agents-host-01` runs on demand ([ADR-0002](../../docs/adr/0002-agent-host-on-demand.md)): the wake service starts it from Slack and it powers off after 30 idle minutes. Infrastructure: [`infra/agents/`](../../infra/agents/README.md); provisioning: [`agents/host/`](../../agents/host/README.md).

## Access

```bash
gcloud compute instances start hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents
gcloud compute ssh hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents --tunnel-through-iap
gcloud compute instances stop hyprn-agents-host-01 --zone=europe-west1-b --project=hyprn-agents
```

The first `gcloud compute ssh` creates a key pair and registers its public key in the administrator's OS Login profile. Administrators log in as their OS Login user and act as an agent with `sudo -iu <agent>`; an open SSH session keeps the host on.

## Provision

```bash
agents/host/apply.sh
```

It reloads secrets, restarts agent sessions (each resumes its conversation) and ends with the host checks.

## Record

| Date | Step | Result |
|---|---|---|
| 2026-10-12 | B1, B2 | `infra/agents/` applied after plan review (19 added). `hyprn-agents-host-01` (`t2d-standard-8`, 10.10.0.3) and `hyprn-agents-wake-01` (`e2-micro`, 10.10.0.2), no external IPs. IAP SSH as OS Login user works; Debian 12, 8 cores, 31 GB, 99 GB disk; outbound HTTPS through Cloud NAT works. Plan shows no changes. Host stopped until provisioning (B3). |
| 2026-10-12 | B3 | Host started; `agents/host/apply.sh` run. First run: DNS for agent users was blocked with the metadata server (same address on Google Cloud), so the Claude Code installer failed silently, and the OS Login admin home was readable by others. Fixed: DNS on port 53 allowed for agent users, pipe failures stop provisioning, `HOME_MODE 0700` and private existing homes. Second run: all 13 host checks pass (metadata unreachable for `ada`, DNS and HTTPS work, rootless Docker, private homes, no rootful Docker daemon, Claude Code 2.1.287, idle-stop timer active, no key files). Docker and GitHub CLI signing keys match the published fingerprints and are now enforced. Ada not yet signed in. |
| 2026-10-12 | B4, B5 | Owner signed Ada in with `/login` (email code, Ada's browser profile); credentials file owned by `ada`, mode 600. `apply.sh` re-run: all host checks pass and `hyprn-agent@ada` started. First start asked for workspace trust of `/home/ada/work` (empty, provisioned folder), accepted once through tmux. Session shows Claude Code 2.1.287, Opus 5.5, Claude Team. After a reboot the session, the metadata block and the idle-stop timer were active again within a minute. |

