# infra/agents

Terraform root for the contents of the `hyprn-agents` project ([ADR-0001](../../docs/adr/0001-agent-fleet.md)): network, IAP-only SSH, Cloud NAT, the host identity and the agent host VM. The project, its folder, budget and state bucket come from [`bootstrap/`](../../bootstrap/README.md). Not an environment: no product workload, data or deployment authority, and nothing shared with staging or prod.

- No public IP; SSH only from IAP's range `35.235.240.0/20` with OS Login; outbound through Cloud NAT.
- Host identity `hyprn-agents-host`: log and metric writer; secret access is granted per secret when secrets are added.
- `gcp-admins` holds IAP tunnel access, OS Admin Login and use of the host identity explicitly.
- Host `t2d-standard-8`, on demand; wake VM `hyprn-agents-wake-01` (`e2-micro`, always on) whose identity can only get, start and stop the host ([ADR-0002](../../docs/adr/0002-agent-host-on-demand.md)).
- The boot image is pinned; updating it is a reviewed change that replaces the VM.
- The VM is bare; agent users, rootless Docker and Claude Code come from [`agents/host/`](../../agents/host/README.md).

## Run

Same credentials as `bootstrap/` (a `gcp-admins` member, dedicated gcloud configuration). State: `gs://hyprn-agents-tfstate/agents/`.

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
terraform init
terraform plan -out=agents.tfplan
terraform apply agents.tfplan
```

Every apply follows a reviewed plan and the owner's explicit go.
