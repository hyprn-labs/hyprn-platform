# hyprn-platform

hyprn's cloud platform on Google Cloud: the organization and its guardrails, environments and identities, the deployment contract between products and hosts, the host reconciler, the agent fleet, and the runbooks that operate them. Products ship from their own repositories; the first is HYPRN MVP (`hyprn-mvp`).

**In service:** the organization baseline ([`bootstrap/`](bootstrap/README.md)) and the agent fleet ([`infra/agents/`](infra/agents/README.md), [`agents/`](agents/README.md)): Ada, a coding agent steered from Slack, on an on-demand host with no public address. Staging and prod follow the [platform specification](docs/specs/cloud-platform.md).

## Ownership

Products own their scientific and API contracts, data schema migrations, health behaviour and images. The platform owns allowed deployment classes, cloud bindings, trust policy, host templates and the desired release per environment. Terraform owns cloud resources; the host reconciler owns the rendered runtime; neither rewrites the other's artifacts.

## Layout

| Path | Contents |
|---|---|
| [`bootstrap/`](bootstrap/README.md) | Organization baseline: bootstrap project and state, organization policies, Essential Contacts, the `agents` folder and project |
| [`infra/agents/`](infra/agents/README.md) | Agent fleet infrastructure: network, IAP access, Cloud NAT, host and wake VMs, agent secrets |
| [`infra/modules/`](infra/modules/environment/README.md), [`infra/environments/`](infra/environments/staging/README.md) | Environment module, host module and the `staging` and `prod` roots |
| [`environments/`](environments/staging/README.md) | Runtime bindings and desired release per environment |
| [`contracts/v1/`](contracts/v1/README.md) | Deployment schemas: workload, runtime, desired state |
| [`host/`](host/README.md) | Host reconciler, renderer, systemd units and firewall templates |
| [`agents/`](agents/README.md) | Agent fleet: roster, roles, host provisioning, Slack channel plugin, wake service, measurement |
| [`governance/`](governance/README.md) | Groups, IAM bindings, repository protections, workload identity federation |
| [`policies/`](policies/README.md) | Policy checks on rendered configuration |
| [`conventions/`](conventions/README.md) | Naming and ownership rules |
| [`catalog/`](catalog/README.md) | Inventory of environments, components and owners |
| [`tests/`](tests/README.md) | Schema, render, policy, IAM, lifecycle and host checks |
| [`runbooks/`](runbooks/README.md) | Operating procedures and records of what was done |
| [`docs/`](docs/README.md) | Platform specification and decision records |

## Working here

- Infrastructure is Terraform. Each root has its own state; every apply uses a reviewed plan.
- Manual operations follow [`runbooks/`](runbooks/README.md), which record each run.
- Decisions are MADR records in [`docs/adr/`](docs/adr/README.md).
