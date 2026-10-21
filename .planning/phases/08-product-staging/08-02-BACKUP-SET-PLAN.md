# 08-02 Task 1 — coherent backup integration prerequisite

Owner: backup-set executor. Scope: new `host/backup_set.py` and
`tests/platform/test_backup_set.py`; parent owns runner registration, product
lifecycle predicates, release/runtime contracts and aggregate acceptance.

Use the existing managed Cloud SQL adapter and product owner-file adapter in one
pinned native process. Keep the inherited deployment lock, parent fence checks,
product lifecycle lock and executor/AiiDA locks continuously held. Check exact
completed drain/stop receipts and actual stopped writers, bind source/configuration,
store/native/schema identities, persist provider intent before dispatch, reconcile
uncertainty only through reads, verify all snapshot bytes, and publish complete
manifest last. A lost hold invalidates the whole set permanently; database-only
reconciliation remains available separately. No new dependencies or cloud calls
outside the isolated HTTP fixture are authorized.

Acceptance: real pinned AiiDA/SQLite source snapshots and restore through existing
product adapter, HTTP provider fixture through existing Cloud SQL adapter, lock
conflicts/loss, restarted writer, provider ambiguity/lost response, receipt
integrity, unsafe file names/modes and unqualified production-host refusal.
Use parent-registered product check group for formal native integration. Linux
root mounted-host invocation and actual IAM/Cloud SQL restore remain unverified;
this prerequisite is not the complete 08-02 task or hosted recovery drill.

Reviewed extension: `host/cloudsql_backup.py` accepts an optional exact application
endpoint binding. Combined backup requires the observed PRIVATE address and
instance-level private-services-access DNS name to match the validated runtime
before any provider POST. Instance/network authority comes from a root-owned
`hyprn-backup-policy/v1` document bound to the active installation/project/release
and configuration, not from a new product runtime contract field. Trusted bootstrap
must have installed the immutable source/native tree from verified payload bytes.
