# bootstrap

Company-level Google Cloud resources, applied by a member of `gcp-admins`:

- project `hyprn-bootstrap` and its state bucket `hyprn-bootstrap-tfstate`;
- organization policies: no service-account keys, no default network, OS Login, blocked project SSH keys, no serial port access, Shielded VMs, uniform private buckets, EU locations only, plus Google's secure-by-default set;
- Essential Contacts to `gcp-admins`;
- folder `agents` without external IPs, project `hyprn-agents`, its state bucket and its 100 EUR budget ([ADR-0001](../docs/adr/0001-agent-fleet.md)).

`terraform.tfvars` holds identifiers only.

## Run

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
terraform init
terraform plan -parallelism=1 -out=bootstrap.tfplan
terraform apply -parallelism=1 bootstrap.tfplan
```

`-parallelism=1` is required: the Org Policy API refuses concurrent writes on one organization. State lives in `gs://hyprn-bootstrap-tfstate/bootstrap/` (versioned, locked).

## Prerequisites

Created once by hand ([runbook](../runbooks/agents/gcp.md)):

1. Group `gcp-admins` with Organization Administrator, Folder Admin, Project Creator and Organization Policy Administrator on the organization, and Billing Account Administrator on the billing account.
2. Project `hyprn-bootstrap`, linked to billing; Terraform adopts it.
3. The APIs Terraform calls through `hyprn-bootstrap` as quota project:

   ```bash
   gcloud services enable billingbudgets.googleapis.com cloudasset.googleapis.com cloudbilling.googleapis.com cloudidentity.googleapis.com cloudresourcemanager.googleapis.com essentialcontacts.googleapis.com iam.googleapis.com orgpolicy.googleapis.com serviceusage.googleapis.com storage.googleapis.com --project=hyprn-bootstrap
   ```

4. Application default credentials: `gcloud auth application-default login`.

To rebuild from nothing: comment out the `backend` block, apply, restore it and run `terraform init -migrate-state`.

## Managed elsewhere

- Organization and billing IAM (prerequisite 1) and removals of grants: [runbook](../runbooks/agents/gcp.md).
- APIs enabled by default at project creation and not listed in `bootstrap_project.tf`.
