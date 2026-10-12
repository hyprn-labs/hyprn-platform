# infra/agents

Contents of the `hyprn-agents` project ([ADR-0001](../../docs/adr/0001-agent-fleet.md), [ADR-0002](../../docs/adr/0002-agent-host-on-demand.md)); the project itself, its folder, budget and state bucket come from [`bootstrap/`](../../bootstrap/README.md).

- VPC `hyprn-agents-vpc` with Private Google Access; SSH only from IAP's range `35.235.240.0/20` with OS Login; outbound through Cloud NAT; no public IPs.
- Host `hyprn-agents-host-01`: `t2d-standard-8`, 100 GB balanced disk, pinned Debian 12, Shielded VM, deletion protection; runs on demand.
- Wake VM `hyprn-agents-wake-01`: `e2-micro`, always on; its identity can only get, start and stop the host.
- Identities: `hyprn-agents-host` (logs, metrics, named secrets) and `hyprn-agents-wake` (logs, metrics, host power, Slack secrets). `gcp-admins` holds IAP tunnel access, OS Admin Login and use of both identities.
- Secrets per agent: `agent-<name>-slack-app-token`, `agent-<name>-slack-bot-token`, `agent-<name>-github-token`, and `agents-slack-allowed-users`; values are added from the password manager ([runbook](../../runbooks/agents/slack.md)).
- The boot image is pinned; updating it is a reviewed change that replaces the VM. Provisioning on the VMs comes from [`agents/host/`](../../agents/host/README.md) and [`agents/wake/`](../../agents/wake/README.md).

## Run

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
terraform init
terraform plan -out=agents.tfplan
terraform apply agents.tfplan
```

State: `gs://hyprn-agents-tfstate/agents/`.
