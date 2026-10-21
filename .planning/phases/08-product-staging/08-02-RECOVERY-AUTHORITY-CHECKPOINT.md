# Recovery authority and parent integration checkpoint

Source proposal `7456689`; owner explicitly approved the exact four-create plan
SHA-256 `c3101b526c57211277acb6daccbe4f91f78e33e7472eed22a14b4b336bf07c37`.
Terraform apply exited 0. Readback verified exact permission sets, exact resource
conditions and the sole existing runtime service-account member. The VM was
independently read back as TERMINATED. No backup was created, no secret transferred
and no Assistant request started. No additional fixed monthly resources were added.
The older two-create backup plan is superseded and must not be applied.

Two roles and two conditional bindings now provide:

- Create/get/list backups and inspect only the installation database and its backups.
- Get only the installation VM and data disk. No compute mutation or fleet listing.

The private recovery-authority review, saved plan, apply log and `applied.json`
remain in the operator's existing private deployment inventory, outside source.
No token is copied into the repository or deployment journal.

## Parent verification

- `tests/platform/run.sh infrastructure` on `7456689`: 2 passed, 0 failed,
  1.367 seconds; ten Terraform test runs. Initial added-run count assertion
  expected nine and failed; corrected to ten before commit. No provider calls.
- `tests/platform/run.sh reconcile` on `167ef7b`: 25 passed, 0 failed, 0.614 s.
- Actual read-only cloud observations found a different guest attachment name
  and no accessMode field on the approved pd-balanced disk. Source `923c8d0`
  now separates disk and device identities and enforces the documented supported
  disk type; explicit contradictory sharing modes remain refused.
- `tests/platform/run.sh reconcile` on `923c8d0`: 35 passed, 0 failed, 0.584 s.
  Tests double provider/kernel observations; actual running-host qualification
  is not established by the stopped-VM readback.
- Combined managed/native backup and standalone adapter acceptance is recorded
  in `08-02-BACKUP-SET-CHECKPOINT.md`; 16 + 18 passed on `b5953ec` paired with
  product `488c02d`. No redundant rerun after later documentation/IAM changes.

Source-authority interpretation: [Google resource-scoped IAM conditions](https://docs.cloud.google.com/iam/docs/configuring-resource-based-access).

Parent owns bootstrap integration, actual owner-schema compatibility, installed
Linux activation/update/recovery rehearsal and final activation approval.
This does not close 08-02 or open application access.
