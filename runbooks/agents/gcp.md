# Runbook: Google Cloud for the agent fleet

Plan steps A1–A4 ([plan](../../docs/plans/agent-fleet.md)). Commands run from the platform owner's workstation with a gcloud configuration dedicated to `hyprn.ai`. Read-only steps run without a separate go; every step that creates, changes or deletes resources, IAM, organization policy or billing runs only after the owner's explicit go for that step, and removals get their own go.

```bash
export ORG=1071176223527          # organization hyprn.ai
export OWNER=<platform owner's hyprn.ai account>
export BILLING=01CF81-DB21A5-2DAFB0  # company billing account
```

## A1. Organization and billing (read-only)

```bash
gcloud organizations list
gcloud billing accounts list
gcloud organizations get-iam-policy "$ORG"
gcloud org-policies describe <constraint> --organization="$ORG" --effective
```

## A2. Organization access

Cloud admin roles are held by the group `gcp-admins@hyprn.ai`, not by a person, so onboarding or a handover is one membership change. Roles are granted only when a step needs them: project and billing-account creation still come from the domain-wide defaults until the project exists; `projectCreator` is granted when staging and prod are created, `cloudasset.viewer` at A5.

1. Workspace admin console (owner):
   - 2-step verification with a security key on the owner's account; backup codes stored offline.
   - Break-glass super admin, role-named (for example `breakglass@hyprn.ai`), with its own security key and backup codes stored offline. Used only for recovery; it holds no standing Google Cloud role, since a super admin can grant itself one when needed.
   - Group `gcp-admins@hyprn.ai`, owner as the only member.
2. Grant the group the roles the bootstrap needs (change):

   ```bash
   for role in resourcemanager.organizationAdmin resourcemanager.folderAdmin resourcemanager.projectCreator orgpolicy.policyAdmin; do
     gcloud organizations add-iam-policy-binding "$ORG" --member="group:gcp-admins@hyprn.ai" --role="roles/$role" --condition=None
   done
   gcloud billing accounts add-iam-policy-binding "$BILLING" --member="group:gcp-admins@hyprn.ai" --role="roles/billing.admin"
   ```

3. Once access through the group is confirmed, remove the owner's direct Organization Administrator binding (removal, own go):

   ```bash
   gcloud organizations remove-iam-policy-binding "$ORG" --member="user:$OWNER" --role="roles/resourcemanager.organizationAdmin"
   ```

4. Create the company billing account in the console (Billing → Create account). Payment details are entered by the owner only. Billing Account Administrator on it is then granted to `gcp-admins` and the owner's direct binding removed.
5. After A3 (project created and linked to billing), remove the domain-wide defaults (removal, own go):

   ```bash
   gcloud organizations remove-iam-policy-binding "$ORG" --member="domain:hyprn.ai" --role="roles/resourcemanager.projectCreator"
   gcloud organizations remove-iam-policy-binding "$ORG" --member="domain:hyprn.ai" --role="roles/billing.creator"
   ```

Check: organization IAM lists named principals only.

## A3. Organization policies, folder and project

Organization-wide, consistent with the platform specification (no service-account keys, no default network, OS Login, Shielded VMs, private uniform buckets, resources in the EU only):

```bash
for c in iam.disableServiceAccountKeyCreation compute.skipDefaultNetworkCreation compute.requireOsLogin compute.requireShieldedVm storage.uniformBucketLevelAccess storage.publicAccessPrevention; do
  printf 'name: organizations/%s/policies/%s\nspec:\n  rules:\n  - enforce: true\n' "$ORG" "$c" > "/tmp/$c.yaml"
  gcloud org-policies set-policy "/tmp/$c.yaml"
done
printf 'name: organizations/%s/policies/gcp.resourceLocations\nspec:\n  rules:\n  - values:\n      allowedValues:\n      - in:eu-locations\n' "$ORG" > /tmp/resourceLocations.yaml
gcloud org-policies set-policy /tmp/resourceLocations.yaml
```

External IPs are denied on the `agents` folder only; the prod host needs a static external IP later.

```bash
gcloud resource-manager folders create --display-name=agents --organization="$ORG"
export FOLDER=<numeric id from the output>
printf 'name: folders/%s/policies/compute.vmExternalIpAccess\nspec:\n  rules:\n  - denyAll: true\n' "$FOLDER" > /tmp/vmExternalIpAccess.yaml
gcloud org-policies set-policy /tmp/vmExternalIpAccess.yaml
```

Project, billing link, APIs and budget: prepared after the billing account exists.

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
