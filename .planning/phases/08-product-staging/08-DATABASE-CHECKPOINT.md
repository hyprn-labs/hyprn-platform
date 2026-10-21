# Database and credential deployment preparation — 2026-10-21

## Implemented, not applied

- `a1b0aa3`: private TLS host role plan/apply/reconcile/verify, six ordinary roles,
  fixed grants and no automatic reset.
- `9849f40`: operator Cloud SQL bootstrap create/delete and nine existing secret
  version publications; per-role byte binding, numeric receipts, no provider-key
  rewrite. Current source has no uncommitted implementation delta.
- The later checkpoint/documentation commit only records verification and the
  pinned application-image invocation. Native host lock lacks pg8000; use the
  existing application image, not a new host dependency.

No cloud mutation, application start, provider request or secret generation has
been performed by this task. Owner approval is still required for the frozen
combined deployment plan. Protected temporary fixture credentials were local and
synthetic; fixture directories and all fixture containers were removed.

## Verification

On committed implementation `9849f40`:

- `tests/platform/run.sh database-setup`: **15 passed**, 0 failed (0.111 s).
- `tests/platform/run.sh database-operator`: **13 passed**, 0 failed (0.572 s),
  with local loopback socket permission for its HTTP fixture.
- `git diff --check`: exit 0.

An isolated Docker PostgreSQL 17.6 fixture with a self-signed, hostname-verified
TLS certificate used the existing pg8000 1.31.5 environment. The actual setup
created six distinct SCRAM logins, checked NOINHERIT/nonprivileged authority,
removed the temporary administrator and verified zero residual memberships.
The real product initialized its full schema, inspected the immutable identity
as request authority, and accepted both Assistant/dispatcher purpose-role guards.
Four attempted request-role escalations (DDL, role creation, migration SET ROLE,
and temporary table creation) were refused. The fixture cleaned up afterwards.
The later source delta adds core-dump prevention and per-alias credential hashes;
it does not change SQL or TLS behavior and is covered by the committed tests.

Reproduction harness is an external scratch artifact named
`hyprn-database-live-check.py`, SHA256
`e06442fe71d4211f2c043dc7fc1c7b97ee044375f321e099821679ce62c37b05`.
The orchestration review holds its exact local path and interpreter path. This
is cross-repository acceptance evidence, not a portable production dependency.

Read-only live operator preflight passed against the prepared Cloud SQL identity,
private DNS/IP/CA and PostgreSQL17 metadata. The exact bootstrap user is absent;
the six database secret version sets are empty. Evidence is
`database-operator-readonly.json` beside the deployment review. No API writes
occurred. Earlier read-only checks from the orchestrator establish the other
three unpublished aliases and preserved Assistant-provider version.

## Failures resolved or scoped

- First isolated suite: seven errors from the local `secrets.py` shadowing the
  Python standard library. Generation uses OS randomness; the driver imports with
  the operator source directory excluded so scramp uses standard-library secrets.
- PostgreSQL fixture first refused `inet_server_addr()` because its text includes
  `/32`. Routing is instead pinned by the socket endpoint and verified server DNS/CA;
  database/session identity is queried without assuming Cloud SQL backend address.
- The real driver returns a tuple of row lists for TLS observation; the check now
  validates cardinality and the actual boolean, independent of row container shape.
- PostgreSQL17 creates an administrative creator membership that a non-superuser
  cannot revoke. Preparation admits only ADMIN TRUE / SET FALSE / INHERIT FALSE
  for the exact temporary user. Final verification requires its deletion and no
  remaining membership. Official PostgreSQL role documentation is linked in the runbook.
- A first cross-repository fixture import lacked product source paths; corrected
  harness then passed actual product migrations and both background guards.
- First read-only Google adapter request used an incorrect stable API path; live
  metadata caught it. The verified stable route is `/v1/projects/...`.
- One committed operator run could not bind its loopback test socket in the
  sandbox; the same group passed with the required socket permission. No source
  relaxation was made.
- Commit hook rejected official reference URLs containing the machine-path pattern;
  documentation now links the official API reference index without bypassing hooks.

## Remaining deployment obligations

Freeze and approve database and operator plans after all pinned source modules
stop changing. Prepared review digests at handoff:

- Database: `4893c3bda4e3e83e001e03563159976a61f21617bd6c03ee144872c7e60f67ef`.
- Operator: `50d1bf8daef8a85f5e933eacd4610d971fad45f293f8bd9f686daab6fcfa9a19`.

Operator account identity and machine paths remain only in private review files.
The combined deployment controller must capture trusted host receipts and transfer
protected files over its reviewed channel, publish numeric versions, delete the
bootstrap user, run final authority verification, then release transient secret
copies. Any pending/uncertain operator action exits 4 and requires read-only
reconciliation; it is not a successful mutation receipt.

Cloud SQL's actual owner grants, SQL/API writes, Secret Manager writes, container
network route, private TLS from the target VM, production migration and login,
scientific execution and Assistant interactions remain unverified. Local fixtures
and read-only preflight do not establish those user journeys.
