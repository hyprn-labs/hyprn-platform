# 08-04C checkpoint — 2026-10-20

Status: isolated bootstrap implementation and real saved plan complete.
No apply, remote state initialization, cloud resource/IAM/secret write or deletion
was performed. Full 08-04 and staging activation remain incomplete.

## Source and exact plan

- Branch: codex/platform-contract.
- Tests-first commit: 1785159.
- Tested implementation and plan source: 8a5ca936e60560132e227eff1c2163757cc55359.
- Private scope: /private/tmp/hyprn-staging-inventory-3k0g1h31/bootstrap-plan-_cqdqeea
  (0700; regular evidence files and saved plan 0600).
- Plan: bootstrap.tfplan.
- SHA256: 59066c7fc6605638b252861d588c33c6fbee77c9e0f59b3a7453e864a52676dc.
- Inputs bootstrap.tfvars.json SHA256:
  5fe4b64c255dbef4f2d60e06952ac5bd91698e335001206c964149222bfb4693.
- Backend local.backend.hcl SHA256:
  43ff6677da4b11c8a1511d3aa7eea7de680a0405b636bcbf6378a8dd5acc4405.
- Full plan JSON show-json.stdout SHA256:
  7c2daae5ba4ed7ff72172c4a63b98a534458de1dff005a6067c9edf936f5c667.
- Exact invocation record: commands.json; structured review: plan-summary.json.

The source snapshot is copied from Git at the recorded commit. The root explicitly
declares its initial local backend; its configured state path is
`<private-scope>/bootstrap.tfstate`. That file does not yet exist.
This is an actual provider plan against empty local state, not a mock plan or a
remote-backend plan. Existing-resource reads and globally unique names remain
subject to recheck immediately before approved apply.

| Action | Address | Proposed resource |
|---|---|---|
| create | google_storage_bucket.staging_state | hyprn-staging-tfstate in hyprn-bootstrap, EUROPE-WEST1, STANDARD |

**1 create / 0 update / 0 delete.** Uniform bucket-level access, public-access
prevention enforced, versioning enabled, force_destroy=false, and Terraform
prevent_destroy. No project, IAM, fleet, organization policy or workload resource.
No object expiry policy; historical state storage remains billable. Soft-delete
settings are provider-computed and are shown as unknown in the saved plan.
The bucket's cost belongs to the bootstrap project; parent approval presentation
owns the current cost estimate and excludes activation from this initial step.

## Checks and failures

1. Tests first: `HYPRN_TF_PROVIDER_DIR="$PWD/bootstrap/.terraform/providers"
   python3 -B -m unittest discover -s tests/platform -p test_state_bootstrap.py -v`
   → 0 passed / 2 failed because the new root did not exist.
2. First implementation: `HYPRN_TF_PROVIDER_DIR="$PWD/bootstrap/.terraform/providers"
   tests/platform/run.sh state-bootstrap` → 1 passed / 1 failed.
   A mock provider does not implement the real provider's replacement decision,
   so changing the bucket name did not exercise prevent_destroy.
3. Corrected replacement test uses a mocked initial state, then the real pinned
   Google provider with refresh=false and an invalid offline access token.
   It asserts Terraform's actual "Instance cannot be destroyed" diagnostic.
   The same group → 2 passed / 0 failed, 2.386 seconds.
4. On committed 8a5ca93, the same group → 2 passed / 0 failed, 2.353 seconds.
   Four evaluated policy/negative-input plans; one mocked seed apply and one
   intentionally rejected real-provider offline replacement plan. The private
   policy plan is inspected to require exactly one create and no IAM resources.
5. `terraform fmt -check infra/bootstrap/staging-state` and
   `git diff --check` → exit 0.
6. Actual provider validation for the private live plan → valid, 0 errors,
   0 warnings. `plan -detailed-exitcode` → 2 (changes); `show -json` → 0.
7. A metadata-display helper initially assumed a computed soft_delete_policy key
   was present and raised KeyError. Corrected to display "known after apply";
   this did not change source, artifacts or plan.

Offline tests use scoped TemporaryDirectory copies, no real credentials, no
backend/cloud writes and no dependency downloads. Those scopes auto-cleaned.
The private plan scope is intentionally retained for review and possible apply;
do not delete it while its plan or local state is needed. No Docker used.
Existing Terraform 1.16.5 and Google 8.6.0 cache/lock reused; provenance and hashes
remain in runbooks/product-staging.md. No new dependencies installed.

## Read-only plan commands

All commands used the dedicated CLOUDSDK_CONFIG and GH_CONFIG_DIR and
GOOGLE_APPLICATION_CREDENTIALS within the dedicated HYPRN gcloud configuration.
TF_DATA_DIR and TF_CLI_CONFIG_FILE point inside the private scope; checkpoint
telemetry disabled. Identity values and credentials are not printed or committed.
`commands.json` contains the exact expanded arguments.

```sh
gcloud storage buckets describe gs://hyprn-bootstrap-tfstate --format=json
gcloud storage objects describe gs://hyprn-bootstrap-tfstate/staging-state-bootstrap/default.tfstate --format=json
gcloud storage buckets describe gs://hyprn-staging-tfstate --format=json
terraform -chdir="$PRIVATE_SCOPE/root" init -input=false -lockfile=readonly \
  -backend-config="$PRIVATE_SCOPE/local.backend.hcl" \
  -plugin-dir="$PLATFORM_ROOT/bootstrap/.terraform/providers"
terraform -chdir="$PRIVATE_SCOPE/root" validate -json
terraform -chdir="$PRIVATE_SCOPE/root" plan -input=false -lock=false \
  -parallelism=1 -detailed-exitcode \
  -var-file="$PRIVATE_SCOPE/bootstrap.tfvars.json" \
  -out="$PRIVATE_SCOPE/bootstrap.tfplan"
terraform -chdir="$PRIVATE_SCOPE/root" show -json "$PRIVATE_SCOPE/bootstrap.tfplan"
```

Existing bootstrap bucket lookup succeeded. Proposed bootstrap prefix state
object and staging bucket lookups returned explicit 404, not authorization
errors. Their stderr and exit codes are retained. These read-only probes reserve
neither name nor prefix. No token, state object contents or secret values read.

## Required sequential approvals — not executed

1. Review the exact source, saved local-backend plan/hash, one-bucket scope and
   cost. With explicit approval only, recheck target absence and source/plan
   hashes and apply that exact saved file with normal local locking. Preserve
   resulting private local state and backup.
2. Separately review the bootstrap backend transition: change only its declared
   backend from local to gcs and set bucket=hyprn-bootstrap-tfstate,
   prefix=staging-state-bootstrap. Review/commit that source change, then use
   `terraform init -migrate-state` from the existing initialized private scope,
   passing only the reviewed GCS backend configuration. This writes the isolated
   remote state and temporary lock; retain the local recovery copy. Verify the
   remote state owns only the new bucket and the subsequent plan is no-op.
   Never adopt the existing bootstrap or fleet state/root.
3. Initialize each main/Access backend in the new staging bucket under its
   reviewed distinct prefix. First initialization also writes empty state and
   locks and therefore must be explicitly included in authorization.
4. Produce actual saved main/Access plans with exact reviewed private inputs,
   record source/hash/actions/cost, and return for approval before any apply.
   No main/Access saved plan is claimed by this task. Their backend bucket is
   absent today; no fake local substitution or mock output was presented as one.

Backend amendment rationale: upstream Terraform 1.16.5 GCS StateMgr writes an
empty state under a newly used prefix and takes a lock, even if the later plan
uses -lock=false. This was discovered before running live init. Parent accepted
the explicit local-first bootstrap sequence so the first exact resource plan
can be reviewed without any cloud write.

Official references checked:
- [Terraform 1.16.5 GCS initialization source](https://github.com/hashicorp/terraform/blob/v1.16.5/internal/backend/remote-state/gcs/backend_state.go)
- [GCS backend](https://developer.hashicorp.com/terraform/language/backend/gcs)
- [Google 8.6 bucket schema](https://github.com/hashicorp/terraform-provider-google/blob/v8.6.0/website/docs/r/storage_bucket.html.markdown)

## Remaining ownership

Parent owns STATE/ROADMAP/requirements reconciliation, the user-facing approval
and cost presentation, relevant staging runbook linkage, and integrated rerun.
Shared planning files were already dirty and were not staged. No requirement is
marked complete by this bootstrap slice; host qualification, publisher controls,
monitoring, migration, live admission and staging product acceptance remain with
their existing plans. No unwired stubs or skipped bootstrap acceptance checks.

## Concrete transition bundle — proposed, not executed

Private directory: `<private-scope>/backend-transition/`.
`proposed-commands.json` contains exact Terraform argv, private paths, per-root
TF_DATA_DIR, dedicated HYPRN identity environment, expected exits and stop rules.
Parent owns in-memory Cloudflare token injection; no credential is in this bundle.

- bootstrap-backend.patch changes only backend "local" to backend "gcs".
  SHA256: 60f8d2827f3ede39e0e22aad2fd996ca31ecb77e517a3a7f94d5650890ed2f97.
- versions.tf.after SHA256:
  936d68c949449192eb463b7e688e09131a8f0c8a13bc1c0b67a2e427a47138cf.
  Required before SHA256:
  c1d2e11ef1371e5ed346e0804c74bc9a6f16b53cae2930daa2aafd3a55b35501.
- bootstrap.backend.hcl SHA256:
  d2b7f2f63ca601d30a9b3e70b6f5b38d1e34ffd0225974bf8bee7801af31658d.
- staging.backend.hcl SHA256:
  f74e567c1bdef6c624eb23280ae05db4359bb2af2625c6c7a0d8dc72abc59ca9.
- access.backend.hcl SHA256:
  a3f29c7f0f93e9df920c2647be928492d6622ce4f7a895aa923edade2a862e09.
- proposed-commands.json SHA256:
  3e0af50885f5425588918665978845b360c794e1adce00c3a5997b230bd84f4c.
- source-manifest.json SHA256:
  e3f87dba2fd538b99a0e6bb10f48f9deb20c31acab8a11c8d8602c71dcec5182.
  It pins 20 Terraform/lock files from 8a5ca93 in the main/Access snapshot.
- staging.tfvars.json SHA256:
  5a98eb9dfe79af23706d8dfc97b7b2ec6b730e691ca8eafc7e10dd5295a41aa0.
- access.tfvars.json SHA256:
  557d8fd712446316bd53f610f4269090413bc1cb12aa5d18817d8ef05bac0f68.

The Access origin is proposed loopback port 8080; host lifecycle must bind it
before activation. These inputs support plan review, not live host acceptance.

| Operation | State object writes | Temporary lock create/delete |
|---|---|---|
| Bootstrap migration | gs://hyprn-bootstrap-tfstate/staging-state-bootstrap/default.tfstate (initialization and migrated one-bucket state) | Same prefix/default.tflock |
| Main initialization | gs://hyprn-staging-tfstate/product-staging/terraform/default.tfstate (empty state) | Same prefix/default.tflock |
| Access initialization | gs://hyprn-staging-tfstate/product-staging/access/default.tfstate (empty state) | Same prefix/default.tflock |

These are the only proposed remote state namespaces. Existing bootstrap/fleet
state is untouched. Lock cleanup deletes only temporary lock objects created by
these operations. Preserve private local state/backup. The exact migration
command uses -migrate-state -force-copy after the reviewed source change and
successful bucket apply; a refreshed no-op bootstrap plan is required afterwards.
Main/Access plans use -lock=false and return for resource/cost approval.
No main/Access resource apply is included. The parent deployment review is
`/private/tmp/hyprn-staging-inventory-3k0g1h31/DEPLOYMENT-REVIEW.md`.

Parent independently reran committed state-bootstrap: 2 passed / 0 failed,
3.066 seconds, exit 0, and independently verified the saved plan SHA256.
