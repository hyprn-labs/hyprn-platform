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

## Phase 1 safeguards (owner-go checklists, 2026-10-13)

Every item below is an owner-hand step per D-08: requested here, executed by
the owner with owner credentials, never automated. Each carries its console
path, expected end-state, and sign-off row.

### 1. Review and apply detect.tf

- Review the exact file revision of `infra/agents/detect.tf` (audit config,
  two alert policies, one email channel, one folder sink; no secret values).
- Console path: terminal with the HYPRN gcloud configuration
  (`CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`).
- Commands (owner runs after explicit go for this exact plan):
  ```bash
  terraform -chdir=infra/agents plan   # reviewed; expect only the detect.tf additions
  terraform -chdir=infra/agents apply  # the reviewed plan, nothing else
  ```
- Expected end-state: apply succeeds; a fresh plan shows no changes.
- Reversibility: reversible (plan-reviewed, destroyable).

### 2. Break-glass admin confirmation (SEC-01)

- Console path: Workspace admin console → Users → the role-named super
  admin; security keys and printed backup codes stored offline, away from
  daily keys.
- Expected end-state: the account exists with its own hardware key plus
  offline backup codes, holds no standing Google Cloud role, and its use is
  documented here. No key material is ever printed or pasted.

### 3. Organization-wide 2FA requirement (SEC-02) — decision gate

- Console path: GitHub org `hyprn-labs` → Settings → Authentication
  security → require two-factor authentication.
- **Decision (one-way): members without 2FA lose access until enrolled —
  the owner approves the member notice before toggling.** Send the notice
  first, then enable.
- Expected end-state: 2FA required for all members; notice sent beforehand.

### 4. Canary secret read → admin email (DET-01 live test)

- Action (owner go): read a canary secret version as an unexpected
  principal (not the host or wake identity).
- Expected end-state: an alert email arrives at `gcp-admins@hyprn.ai`
  from the unexpected-access policy.

### 5. Canary IAM change → admin email (DET-02 live test)

- Action (owner go): make a canary IAM grant change in `hyprn-agents`
  (reverted afterwards under its own go).
- Expected end-state: an alert email arrives at `gcp-admins@hyprn.ai`
  from the IAM-change policy.

### 6. Org-wide IAM search with owner credentials (ACC-04)

- Command (owner runs):
  ```bash
  gcloud organizations get-iam-policy 1071176223527
  ```
- Expected end-state: exactly the declared roles — `gcp-admins@hyprn.ai`
  holds the admin roles, no person or domain holds roles directly, and
  nothing exists outside the projects the access model names.

## Safeguard sign-off

| Date | Item | Result |
|---|---|---|
| 2026-10-13 | detect.tf apply (§1) | Awaiting owner go |
| 2026-10-13 | Break-glass (§2) | Awaiting owner confirmation |
| 2026-10-13 | 2FA + member notice (§3) | Awaiting owner decision + go |
| 2026-10-13 | Canary secret read (§4) | Awaiting owner go + mail arrival |
| 2026-10-13 | Canary IAM change (§5) | Awaiting owner go + mail arrival |
| 2026-10-13 | Org-wide IAM search (§6) | Awaiting owner run + role match |

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
