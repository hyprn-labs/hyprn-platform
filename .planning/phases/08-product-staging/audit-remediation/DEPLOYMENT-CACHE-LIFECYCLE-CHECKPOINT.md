# Deployment cache lifecycle checkpoint — 2026-10-23

Implementation: `b2f4077`. Scope: delivery transfer cache only; no live changes.

V2 staging saves exact protected transfer receipts after success and admits a
transfer only with its complete byte budget plus 4 GiB reserve. The lifecycle
helper discovers known archives across legacy/data transfer roots, derives current
and rollback retention from protected runtime/journal state, and verifies obsolete
receipted archives against generation-pinned durable object bytes before unlink.
It reports cache/free-space/backlog metrics and refuses uncertainty. Unknown legacy
archives and all scientific, execution, installed-native and control records remain.

The deterministic installer snapshots pinned code/policy and installs an hourly
bounded systemd service/timer. It verifies exact previous policy on upgrade;
unknown unit edits refuse replacement. Deployment-lock contention is a harmless
scheduled skip. Pressure is an observable exit 3, not silent disk growth. Journald
retention source/plan was unchanged.

## Verification on committed tree

- `tests/platform/run.sh release-stage`: 18 passed, exit 0.
- `tests/platform/run.sh deployment-storage`: 7 passed, exit 0.
- `tests/platform/run.sh deployment-cache`: 10 passed, exit 0.
- `git diff --cached --check`: passed before commit.
- Real isolated CLI `python3 -I -B host/deployment_cache_setup.py plan --policy ...`
  produced the deterministic plan successfully. No cloud call in this operation.
- Temporary fixtures cleaned up by tests. Systemd and GCS transports are isolated
  doubles; live scheduling, unit validation and durable-object retrieval remain
  parent deployment verification, not established by these tests.

Development failures: one new headroom test initially used the real root-only owner
instead of the fixture user (17 passed/1 failed), fixed in fixture setup. New group
initially refused its untracked test file, then registered explicitly. Subsequent
focused runs passed; only the final committed-tree counts above are delivery evidence.

## Prepared integration

Private policy/plan: `/private/tmp/hyprn-deployment-cache-install/`.
Initial installer hash:
`95d5768ca6a92320c6fc59897415c62c077de323d4953f6f6ea8419a4f99a67a`.
Policy hash:
`34f8de8c0110f93c7690410276b7a34093ab46bab08364070f5228d411f2bdb5`.

Parent owns staging exact source/policy, applying the installer after activation,
optional immediate service start, and live verification. The initial 12 GiB cache
target includes preserved legacy unique transfers; it may produce pressure while
those remain unreceipted. A reviewed 16 GiB target can be chosen by regenerating
only the policy/plan. No unique legacy archive is silently discarded. No fixed
cloud resource or IAM change was introduced. Other agents' files remained untouched.
