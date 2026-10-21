# Staging database role setup

`host/database_setup.py` prepares the six fixed application identities in the
existing private PostgreSQL database. Application schema creation remains the
product migration operation. Runtime identities never receive `cloudsqlsuperuser`,
`CREATEROLE`, `CREATEDB`, `BYPASSRLS`, replication or inherited role membership.
The migration identity alone receives `CREATE` on `public`. The backup identity
is reserved and receives no table access or RLS bypass; Cloud SQL physical backups
use the existing separately scoped Google API authority.

## Reviewed input and operations

The policy has exactly these fields:

```json
{
  "schema": "hyprn-database-setup/v1",
  "project_id": "hyprn-staging",
  "instance": "hyprn-staging-app",
  "installation_id": "<reviewed installation identity>",
  "database": "<reviewed database name>",
  "private_ip": "<reviewed RFC1918 endpoint>",
  "server_name": "<reviewed Cloud SQL DNS name without trailing dot>",
  "ca_sha256": "<SHA256 of reviewed public CA PEM>",
  "bootstrap_role": "hyprn_bootstrap_<8 to 24 lowercase alphanumeric characters>"
}
```

Run planning with the platform source tree. Apply uses the already pinned product
Python environment containing `pg8000==1.31.5`; it installs no package. Freeze the
plan digest after all three source files in its `sources` map stop changing.

```sh
python3 -B host/database_setup.py plan --policy /review/database-policy.json
python3 -B host/database_setup.py apply --policy /review/database-policy.json \
  --ca-file /run/hyprn/database-setup/ca.pem \
  --admin-password-file /run/hyprn/database-setup/admin-password \
  --private-root /run/hyprn/database-setup/credentials \
  --approve-sha256 APPROVED_PLAN_SHA256
```

The private root must already exist, owned by root with mode `0700`, on tmpfs,
with swap disabled. CA and bootstrap-password inputs must be regular `0600`
files without symlinks or hard links. Runtime password files contain raw bytes,
as expected by the product reader. The command disables core dumps, sends only
salted SCRAM verifiers in role DDL, writes no credentials to command arguments or
stdout, and uses a verified TLS connection with separate private routing and DNS
certificate identities. It checks the target database and session identity.

The database and its public schema must be empty and controllable by the bootstrap
identity. Setup refuses before changing roles when those conditions are unmet.
All role creation and grants occur in one transaction. Passwords and an intent
are written before mutations; a successful receipt is written only after all six
credentials authenticate and privileges are read back.

## Operator actions in the combined deployment approval

The host script deliberately has no cloud API mutation or Secret Manager write authority.
The [operator helper](database-operator.md) performs these separately reviewed actions.
The combined deployment plan explicitly binds their order and exact identities:

1. Verify the existing SQL instance, its private endpoint/DNS/CA, existing database,
   and absence of the exact temporary bootstrap name. Create **only** that temporary
   built-in Cloud SQL user through the operator identity. Generate its password in
   protected memory/file storage; never pass it as a CLI argument. The API request
   is `POST /v1/projects/{project}/instances/{instance}/users`, with the
   exact JSON fields `name`, `type: BUILT_IN`, and generated `password`. Record the
   intent before submission and poll its returned operation to completion. A lost
   response requires inspection of users/operations, not another create/reset.
2. Transfer that password and the public CA to protected host tmpfs over the
   existing authenticated IAP/SSH channel. Apply the approved database plan once.
   Do not reset the existing `postgres` user or grant runtime users the Cloud SQL
   administrator role.
3. Capture all six protected `db-*` password files into the reviewed operator
   secret-transfer scope. Publish exactly one new version to each matching
   `hyprn-staging-db-*` Secret Manager secret. Bind numeric returned versions into
   the runtime descriptor. Retain an intent per alias, refuse a nonempty existing
   version set unless expressly reviewed, and reconcile uncertain writes by
   version identity and payload equality before retrying. Preserve the existing
   Assistant provider secret. The runtime service account remains accessor-only.
4. Delete the **same** temporary bootstrap user via
   `DELETE /v1/projects/{project}/instances/{instance}/users?name={name}`
   with an empty body, and poll the operation. Verify user absence through the
   API and the command below. No schema/database object is owned by this temporary
   user; its removal is not a cascade deletion of application objects.
5. Only after successful secret read-back and bootstrap-user removal, securely
   release transient password copies and perform the product schema migration.
   Retain only nonsecret receipts. Application admission requires the final
   authority receipt and the ordinary product initialization/execution gates.

PostgreSQL 17 automatically grants a non-superuser role creator an administrative
membership issued by PostgreSQL's bootstrap superuser; the creator cannot revoke
it. Preparation admits only that exact temporary membership (`ADMIN TRUE`,
`INHERIT FALSE`, `SET FALSE`). It does not give any runtime role membership in
another role. Final verification requires the temporary user and **all** such
memberships to be absent:

```sh
python3 -B host/database_setup.py verify --policy /review/database-policy.json \
  --ca-file /run/hyprn/database-setup/ca.pem \
  --private-root /run/hyprn/database-setup/credentials \
  --approve-sha256 APPROVED_PLAN_SHA256
```

A preparation receipt explicitly says `bootstrap_admin_removed: false`; it is not
a deployment admission. `verified.json` is the separate final authority receipt.

## Interrupted operations

A second apply refuses rather than resets credentials. Use `reconcile` with the
same arguments as `apply` to inspect role comments, flags, membership and all six
credential logins. If the original transaction committed, this completes the
receipt without SQL writes. If no roles exist, it reports `not_committed` without
retrying. A partial set, mismatched marker, changed privileges or lost password
files requires a reviewed recovery. Never silently generate replacements.

An outage/reboot loses tmpfs copies. Until numeric Secret Manager versions are
confirmed, keep the VM running and treat those copies as the recovery material.
A reconciliation cannot reconstruct a lost credential from its SCRAM verifier.

## Sources and limits

- [Cloud SQL API reference](https://docs.cloud.google.com/sql/docs/postgres/admin-api/rest/v1)
  defines the operator user creation and deletion operations.
- [Cloud SQL built-in users](https://docs.cloud.google.com/sql/docs/postgres/users)
  documents the default administrator role that must not reach runtime identities.
- [PostgreSQL 17 role attributes](https://www.postgresql.org/docs/17/role-attributes.html)
  explains the temporary creator membership.

Local PostgreSQL TLS verification establishes the SQL and driver behavior, not
Cloud SQL IAM/API behavior. Live operator user creation, Secret Manager publication,
Cloud SQL owner grants and actual private TLS still require the approved deployment
and its recorded results. There is no cloud mutation in planning or local tests.

## Runtime image invocation

The native host environment does not contain the PostgreSQL driver. Use the exact
reviewed application image, which already contains `pg8000==1.31.5`, as a one-off
operator container. This does not start the application. The image digest, source
folder and input-file locations are fixed by the combined deployment plan.

```sh
docker run --rm --name REVIEWED_DATABASE_SETUP_CONTAINER \
  --network hyprn-staging_application --user 0:0 --read-only \
  --cap-drop ALL --security-opt no-new-privileges:true \
  --pids-limit 64 --memory 128m --cpus 0.5 --ulimit core=0 \
  --mount type=bind,src=REVIEWED_HOST_SOURCES,dst=/platform,readonly \
  --mount type=bind,src=REVIEWED_POLICY,dst=/policy.json,readonly \
  --mount type=bind,src=REVIEWED_CA,dst=/ca.pem,readonly \
  --mount type=bind,src=BOOTSTRAP_PASSWORD,dst=/admin-password,readonly \
  --mount type=bind,src=ROOT_OWNED_TMPFS_CREDENTIALS,dst=/credentials \
  --entrypoint python REVIEWED_APP_IMAGE_DIGEST \
  -B /platform/database_setup.py apply --policy /policy.json \
  --ca-file /ca.pem --admin-password-file /admin-password \
  --private-root /credentials --approve-sha256 APPROVED_PLAN_SHA256
```

The application network must already have its reviewed private-database-only
route for this operation. No Docker socket, provider credential or host operator
OAuth token is mounted. UID 0 exists only to preserve ownership of the protected
files; all container capabilities are dropped. After deleting the temporary
bootstrap user, the `verify` invocation omits the bootstrap-password mount and
argument, retaining the same image, source, policy, CA and credential-directory
pins. The tmpfs and swap checks remain active inside the container. This exact
container launch still requires live deployment verification; the local SQL/TLS
fixture validated the same driver and role operations, not host packet rules.
