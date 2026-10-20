# Hosted recovery implementation amendment

Date: 2026-10-21. Status: implementation choice; cloud authority pending review.
This amendment narrows the PostgreSQL backup mechanism in cloud-platform.md
section 9 and the corresponding 08-02 / product 06-05 implementation plans.
It does not weaken cross-store consistency, recovery checks or release gates.
The owner authorized a pragmatic shortest working path and adjustments to the
proposed milestone sequence; actual IAM/resource changes still need exact approval.

## Mechanism

Use a standard Cloud SQL on-demand instance backup as the PostgreSQL member of
one coherent set. FORCE RLS stays enabled. The host needs no database login with
BYPASSRLS, no superuser and no new dump dependency. Modeling SQLite, AiiDA SQLite
and its complete repository, and application artifacts use the product's pinned
owner-file snapshot operation. Automatic SQL backups and PITR remain independent
additional recovery options, not evidence of cross-store consistency.

The trusted host keeps the deployment fence, closed admission, drained accepted
work and stopped writers throughout creation, successful provider completion and
owner snapshots. Product native executor and AiiDA locks remain held. A manifest
is published last and binds the provider backup identity/metadata, file hashes,
store/schema/native identities, exact release, configuration and continuous hold.
The provider object is a managed reference, not an export with an invented byte
checksum. A partial file snapshot or successful SQL backup alone is incomplete.

Before POST, persist intent and a unique correlation marker. The API offers no
idempotency key. A lost response is reconciled through a saved operation or every
backup-list page; missing or ambiguous matches never trigger another automatic
create. A lost writer hold makes the set ineligible even if the backup succeeds.
The fixed API adapter refuses redirects, foreign identities and unbounded waits.

## Authority and recovery

Proposed runtime role has only cloudsql.backupRuns.create/get/list and
cloudsql.instances.get, conditioned to the exact staging instance and its
BackupRun resources. No runtime restore, update, create-instance, deletion or
IAM privilege. Terraform uses additive role/member resources. This change is
prepared only, never covered by approval of the earlier 76-resource plan.
The old empty db-app-backup secret metadata is unused and retained; its deletion
is a separate future reviewed cleanup, not part of this change.

Recovery restores to a separately authorized empty private instance, never the
source or a live replacement. Cloud SQL instance backups include databases and
users: future users/databases on the same instance join this hold and recovery
policy. Recovery must verify target connectivity, flags, schemas, user grants,
secrets and scientific references before fresh execution attestation/admission.
A separate recovery operator owns restore/provisioning/deletion. On-demand
backups are not governed by the seven automated-backup retention count; explicit
complete-set retention and deletion remain required operational work.

## Evidence and remaining integration

Installed product application and numerical owner journeys have committed
acceptance; owner-file snapshot tests are real pinned SQLite/AiiDA checks.
Platform managed-backup tests may substitute only the Google HTTP boundary and
must not claim live IAM or Cloud SQL restore proof. Whole-store recovery remains
unqualified until a reviewed isolated real Cloud SQL drill and Linux host test.

Product 06-05 aggregate host proof and platform 08-02 integration are one shared
acceptance boundary. Their code prerequisites may be implemented together after
the installed owner checks; neither plan is complete until the real combined
lifecycle, second activation and isolated restore pass. This removes a circular
ordering dependency, not a correctness prerequisite. Parent owns integration;
scoped executor checkpoints retain exact changes and evidence.

## Sources

- [Cloud SQL backup API](https://docs.cloud.google.com/sql/docs/postgres/admin-api/rest/v1/backupRuns/insert)
- [IAM permissions](https://docs.cloud.google.com/sql/docs/postgres/iam-permissions)
- [IAM conditions for instance and BackupRun resources](https://docs.cloud.google.com/sql/docs/postgres/iam-conditions)
- [Restore scope and target effects](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/restore)
- [Backup retention](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/backups)
