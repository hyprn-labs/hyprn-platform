# bootstrap

One-time bootstrap of company-level Google Cloud resources: the bootstrap project and its state bucket, baseline organization policies, Essential Contacts, and the `agents` folder with the `hyprn-agents` project, its state bucket and budget ([ADR-0001](../docs/adr/0001-agent-fleet.md)). Staging and prod roots come later under `infra/environments/`. No credentials are committed; `terraform.tfvars` holds identifiers only.

Run by a member of `gcp-admins` with application default credentials, from a gcloud configuration dedicated to `hyprn.ai`. Every apply follows a reviewed plan and the owner's explicit go.

## Prerequisites (manual, recorded in [runbooks/agents/gcp.md](../runbooks/agents/gcp.md))

1. Group `gcp-admins` with Organization Administrator, Folder Admin, Project Creator and Organization Policy Administrator on the organization, and Billing Account Administrator on the billing account.
2. Project `hyprn-bootstrap` created with gcloud and linked to billing; Terraform adopts it.
3. The APIs Terraform calls through the bootstrap project as quota project, enabled once:

   ```bash
   gcloud services enable billingbudgets.googleapis.com cloudasset.googleapis.com cloudbilling.googleapis.com cloudidentity.googleapis.com cloudresourcemanager.googleapis.com essentialcontacts.googleapis.com iam.googleapis.com orgpolicy.googleapis.com serviceusage.googleapis.com storage.googleapis.com --project=hyprn-bootstrap
   ```

4. Application default credentials: `gcloud auth application-default login`.

## Run

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
terraform init
terraform plan -parallelism=1 -out=bootstrap.tfplan
terraform apply -parallelism=1 bootstrap.tfplan
```

`GOOGLE_APPLICATION_CREDENTIALS` pins the credentials to the dedicated gcloud configuration. `-parallelism=1` avoids `CONCURRENT_POLICY_CHANGES`: the Org Policy API refuses parallel writes on one organization.

State lives in `gs://hyprn-bootstrap-tfstate/bootstrap/` (versioned, GCS state locking). The first apply used local state, since the bucket is created here; it was then migrated with `terraform init -migrate-state`, confirmed by a no-change plan, and the local files deleted. To rebuild from nothing: comment out the `backend` block, apply, restore it and migrate again.

## Not managed here

- Removing the domain-wide Project Creator and Billing Account Creator grants and the owner's direct bindings: manual removals, each with its own go.
- APIs enabled by default at project creation and not listed in `bootstrap_project.tf` stay as they are.
