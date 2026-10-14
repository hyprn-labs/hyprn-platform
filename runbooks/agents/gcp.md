# Runbook: Google Cloud organization

Organization access, billing and the bootstrap project for `hyprn.ai`. Everything else at organization level is Terraform in [`bootstrap/`](../../bootstrap/README.md). Commands run with the gcloud configuration dedicated to hyprn.

```bash
export ORG=1071176223527             # organization hyprn.ai
export BILLING=01CF81-DB21A5-2DAFB0  # company billing account
```

## Inspect

```bash
gcloud organizations get-iam-policy "$ORG"
gcloud billing accounts get-iam-policy "$BILLING"
gcloud org-policies list --organization="$ORG"
gcloud org-policies describe <constraint> --organization="$ORG" --effective
```

## Access model

- The group `gcp-admins@hyprn.ai` holds every cloud admin role; membership is the only thing that changes when people join or leave. No person and no domain holds a role directly.
- Organization: Organization Administrator, Folder Admin, Project Creator, Organization Policy Administrator. Billing account: Billing Account Administrator. Projects: Owner.
- Break-glass: a role-named super admin in the Workspace admin console with its own security key and offline backup codes, used only for recovery; it holds no standing Google Cloud role.
- Members use 2-step verification with a security key.

## Grant the group its roles

```bash
for role in resourcemanager.organizationAdmin resourcemanager.folderAdmin resourcemanager.projectCreator orgpolicy.policyAdmin; do
  gcloud organizations add-iam-policy-binding "$ORG" --member="group:gcp-admins@hyprn.ai" --role="roles/$role" --condition=None
done
gcloud billing accounts add-iam-policy-binding "$BILLING" --member="group:gcp-admins@hyprn.ai" --role="roles/billing.admin"
```

## Bootstrap project

```bash
gcloud projects create hyprn-bootstrap --name="hyprn bootstrap" --organization="$ORG" --labels=component=bootstrap,managed_by=terraform
gcloud billing projects link hyprn-bootstrap --billing-account="$BILLING"
```

Then the prerequisites and run in [`bootstrap/`](../../bootstrap/README.md).

## Remove direct grants

After access through the group is confirmed:

```bash
gcloud organizations remove-iam-policy-binding "$ORG" --member="domain:hyprn.ai" --role="roles/resourcemanager.projectCreator"
gcloud organizations remove-iam-policy-binding "$ORG" --member="domain:hyprn.ai" --role="roles/billing.creator"
gcloud organizations remove-iam-policy-binding "$ORG" --member="user:<account>" --role="roles/resourcemanager.organizationAdmin"
gcloud billing accounts remove-iam-policy-binding "$BILLING" --member="user:<account>" --role="roles/billing.admin"
gcloud projects remove-iam-policy-binding <project> --member="user:<account>" --role="roles/owner"
```

Check: organization, billing and project IAM list `gcp-admins` and Google service agents only.

## Misuse detection

`infra/agents/detect.tf` audits Secret Manager reads and emails `gcp-admins` on an unexpected secret read, creation, deletion or reader grant, and on any IAM policy change to the `hyprn-agents` project or the `agents` folder. Apply it like any `infra/agents/` change: plan, review, apply the reviewed plan. Then test each alert once (owner's go for each):

1. **Secret alert:** as the owner, read a secret and count its bytes without displaying it: `gcloud secrets versions access latest --secret=agents-slack-allowed-users --project=hyprn-agents | wc -c`. Expected: an email from "hyprn agents: unexpected secret access" within about 5 minutes.
2. **IAM alert:** add and then remove a harmless binding, for example `roles/viewer` for `gcp-admins@hyprn.ai` on `hyprn-agents`. Expected: an email from "hyprn agents: IAM policy change".

## Account safeguards

- **Break-glass administrator (SEC-01):** a role-named super administrator in the Workspace admin console, with its own security key and printed backup codes kept offline, no Google Cloud role, used only when the owner's account is unavailable.
- **Direct grants:** no person holds a role on the organization, the `agents` folder or `hyprn-agents`; the admins group does. Folder creation grants its creator Folder Admin and Folder Editor; remove them from the owner's account once the group holds its folder roles.
- `tests/agents/owner-checks.sh` checks both, with detection and the GitHub organization settings.

## Record

| Date | Step | Result |
|---|---|---|
| 2026-10-12 | A1 | Organization `hyprn.ai` (`1071176223527`) exists; owner holds Organization Administrator. No billing account visible; no folders or projects. Domain-wide `projectCreator` and `billing.creator` present. Effective policies: automatic default-account grants off (enforced); member domains restricted to the company directory; service-account key creation, default network, OS Login and external IPs not restricted. |
| 2026-10-12 | A2.4 | Billing account `01CF81-DB21A5-2DAFB0` ("My Billing Account") created by the owner in the console. The console also created project `neural-cable-511417-u9` ("My First Project") at the organization root, linked to that billing account, with default APIs enabled (BigQuery family, Datastore, Logging, Monitoring, Storage and others) and the owner as project Owner. Group `gcp-admins` not yet created. |
| 2026-10-12 | A2.1, A2.2 | Group `gcp-admins@hyprn.ai` created by the owner in the admin console; its join and external-member settings are checked in the console, since the Groups API needs a quota project. Owner ran the step 2 grants. Verified: the group holds Organization Administrator, Folder Admin, Project Creator and Organization Policy Administrator on the organization and Billing Account Administrator on the billing account. The owner's direct Organization Administrator and Billing Account Administrator bindings and the domain-wide defaults remain, to be removed in later steps. |
| 2026-10-12 | Bootstrap project | Project IDs use plain names, with a random suffix only when an ID is taken. Created `hyprn-bootstrap` (number `398807288756`) at the organization root with labels `component=bootstrap`, `managed_by=terraform`, linked to the company billing account. Creation enabled the default API set (BigQuery family, Datastore, Storage and others); the bootstrap Terraform keeps only what it needs. The creator holds Owner until Terraform hands ownership to `gcp-admins`. |
| 2026-10-12 | Cleanup | Console-created project `neural-cable-511417-u9` deleted (state `DELETE_REQUESTED`, recoverable for 30 days with `gcloud projects undelete`). |
| 2026-10-12 | Bootstrap APIs | Enabled on `hyprn-bootstrap`: Billing Budgets, Cloud Asset, Cloud Billing, Cloud Identity, Resource Manager, Essential Contacts, IAM, Org Policy, Service Usage, Storage. |
| 2026-10-12 | Bootstrap apply | `bootstrap/` applied after plan review (8 imported, 36 added, 1 label-only change, 0 destroyed). First run hit `CONCURRENT_POLICY_CHANGES` on two organization policies; the remaining 16 resources were re-planned (subset of the reviewed plan) and applied with `-parallelism=1`. Result: folder `agents` (`86446816109`) denying external IPs; project `hyprn-agents` (`605123398847`) with no default network; buckets `hyprn-bootstrap-tfstate` and `hyprn-agents-tfstate`; 14 organization policies; Essential Contacts to `gcp-admins`; budget 100 EUR on `hyprn-agents`; `gcp-admins` Owner on both projects alongside the owner's direct Owner role. A fresh plan shows no changes. State still local. |
| 2026-10-12 | Bootstrap state | State migrated to `gs://hyprn-bootstrap-tfstate/bootstrap/default.tfstate`; plan against remote state shows no changes; local state files deleted. |
| 2026-10-12 | A2 removals | Verified `gcp-admins` membership (owner as only member, security label set). Removed the domain-wide Project Creator and Billing Account Creator grants, the owner's direct Organization Administrator and Billing Account Administrator bindings, and the owner's direct Owner role on `hyprn-bootstrap` and `hyprn-agents`. Organization, billing and project IAM now list `gcp-admins` and Google service agents only; Terraform plan through the group shows no changes. |
| 2026-10-14 | Misuse detection | `infra/agents/` apply of `detect.tf` (reviewed plan, 6 to add): email channel, both alerts and Secret Manager data-read audit logs created; the folder sink failed (`logging.sinks.create` denied on the `agents` folder: the admins group held no logging role there) and its writer grant was not created. `bootstrap/` grants `gcp-admins` Logs Configuration Writer on the `agents` folder (plan: 1 to add) before the remaining 2 are applied. |
