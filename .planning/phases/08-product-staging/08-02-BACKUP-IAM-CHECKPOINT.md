# Managed-backup authority preparation checkpoint

Source: `628a4ae70be063891e75d91e3f548c878c17100e`.
Status: source complete; exact cloud apply awaiting owner approval. This is one
08-02/08-05 prerequisite, not reconciler completion or hosted qualification.

## Change and evidence

The four-permission custom role is bound additively to the existing runtime
service account. Instance and BackupRun resource conditions use exact name or
slash-bounded children. Restore, deletion, instance modification and IAM changes
are absent. Existing backup-secret metadata and all previously applied resources
are preserved. See the scoped RECOVERY-AMENDMENT for the RLS-safe backup choice.

Offline source verification: `HYPRN_TF_PROVIDER_DIR=<reviewed Google cache>
tests/platform/run.sh infrastructure` passed 2 tests in 1.403 s, including nine
Terraform policy runs. The first invocation used a nonexistent cache path and
failed before executing the provider (1 pass, 1 failure, 0.001 s). Correcting the
path reused the existing pinned provider; no dependency was installed.
Committed-tree parent acceptance: same command, 2 passed in 1.457 s; log
`hyprn-backup-iam-committed.log` in the private scratch directory. All test stores
were isolated and removed by their fixtures; no cloud credentials were supplied.

The live read-only Terraform plan used a git-snapshot of the exact source above,
the previously reviewed staging inputs/state and dedicated HYPRN identity.
Refresh succeeded: exactly two creates, no updates or deletes. Saved-plan SHA256:
`18313a4473c083de423a98f6384f72f383332b2519c3e864052b54ed1243e183`.
Artifacts, complete source hashes and the owner review are retained in the
private staging inventory's `database-backup-authority/` directory. No plan/state,
credentials, personal identities or secret payloads enter Git.

A read-only source-instance inspection confirmed PostgreSQL17, STANDARD backup
mode, private networking, verified TLS configuration, enabled managed backups
and PITR. This checks actual provider field shapes; it does not test newly
proposed permissions, create a backup or establish coherent recovery.

## Remaining authority and acceptance

Exact two-resource apply/readback requires the platform owner's approval. This
has no additional fixed resource charge and authorizes no VM startup, backup,
restore, secret transfer, subscription change or deletion. Cloud SQL backup
storage remains usage-billed when backups are later enabled. Effective IAM
behavior, full continuous writer hold, set retention and isolated whole-store
restore need integration and a separately reviewed real cloud journey.
