# Host reconciliation implementation scope

This scoped Task 1 batch implements durable sequencing, exclusive deployment
locking, exact descriptor binding, fixed product CLI operations, Linux/GCE disk
identity checks and failure closure. Its seams are the public reconciliation
Python entry point, product subprocess JSON contract and read-only Google/kernel
observations. These seams were assigned by the orchestrator; focused fault tests
substitute external boundaries only and do not qualify a real host lifecycle.

The production entry point must reject absent bootstrap policy, unverified staged
payloads, uncertain migration, incomplete backups and unsupported admission
qualification. No cloud resource change, IAM apply, backup creation or VM start
is authorized in this implementation session. New dependencies: none.

Ownership: this executor owns host/reconcile.py, tests/platform/test_reconcile.py
and this scoped plan/checkpoint. Backup set and secrets are separate executors.
Parent owns combined real Linux acceptance, final integration and phase closure.
The first acceptance outcome is a callable, reviewable closed-admission sequence
with restart-safe mutation evidence; a fully applied deployment remains pending
trusted host qualification and the combined real two-release/recovery exercise.
