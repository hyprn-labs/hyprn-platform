# 08-02 bounded prerequisite: Cloud SQL database backup adapter

Owner: cloud_sql_backup executor. One task, test first, no cloud mutation during execution.

First outcome: a trusted-host CLI can request one approved standard on-demand database
backup, persist its intent before dispatch, and resume by reading provider state without
another POST. The target is the fixed Cloud SQL Admin HTTPS v1 API using only the
attached staging runtime service account, exercised locally through isolated HTTP doubles.

Task 1 owns host/cloudsql_backup.py, tests/platform/test_cloudsql_backup.py, the backup
entry in tests/platform/run.sh, and this plan/checkpoint. It does not own Terraform,
contracts, existing secrets code, reconciliation or product files.

Acceptance: exact project/instance/installation/release/configuration/operation binding;
reviewed PostgreSQL 17, standard backups enabled, no public IPv4, exact private network and encrypted connections; private durable intent before POST; bounded pagination and polling; lost responses,
zero/ambiguous matches, wrong identity, provider failures and repeated calls never
redispatch; successful provider state alone yields a database-only receipt; no raw
provider errors or tokens leak. Symlink/hardlink/mode/ownership checks and serialization
protect the state. Read-only resume and verification never authorize creation.

No documented provider idempotency key exists. A canonical binding digest in the
on-demand description identifies the attempt. Scan every list page and require exactly
one exact match before reading the immutable backup ID. Bounded scan exhaustion closes
without assuming absence. No automatic mutating retry, restore or deletion is implemented.

The shared role needs cloudsql.backupRuns.create/get/list and cloudsql.instances.get.
Creation still requires exact-resource approval; IAM application is outside this task.

Verification: first demonstrate failing tests, then tests/platform/run.sh backup on the
committed implementation. Doubles replace only connection creation and exercise real HTTP
request parsing at a local server. No Docker, live credentials or live Cloud SQL calls.

Next stopping point: scoped atomic implementation commit and checkpoint with exact
results. This does not complete platform08-02: writer freeze, coherent all-store snapshot,
manifest publication, real product lifecycle and approved empty-target restore remain
parent-owned. A successful database backup is never a whole-installation backup gate.

Official API references consulted 2026-10-21:
- https://docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/backupRuns
- https://docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/backupRuns/insert
- https://docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/backupRuns/list
- https://docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/instances/get

Provider operation completion is not polled separately: the receipt requires the exact
uniquely matched BackupRun GET to report SUCCESSFUL without an error, with ordered
enqueue/start/end timestamps. This uses only the four scoped role permissions above.

Permissions reference: https://docs.cloud.google.com/sql/docs/postgres/iam-permissions
Operation response reference: https://docs.cloud.google.com/sql/docs/mysql/admin-api/rest/v1/operations
