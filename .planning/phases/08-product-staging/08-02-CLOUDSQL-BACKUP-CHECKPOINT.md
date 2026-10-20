# Cloud SQL backup adapter checkpoint — 2026-10-21

Bounded prerequisite delivered; platform08-02 and the coherent-backup gate remain open.
Implementation commit: `9c05e779fc87618c247c17fff2356b2efb6cf96f`.
This checkpoint adds evidence only; it changes no behavior from that tested tree.

## Verification

| Command | Result |
|---|---|
| `python3 -B -m unittest discover -s tests/platform -p test_cloudsql_backup.py -v` (initial red) | 14 tests, 14 expected failures: module not implemented, 7.110s |
| same (first implementation) | 14 passed, 0 failed, 15.736s |
| same (expanded pagination coverage) | 16 passed, 1 failed, 19.274s |
| same (reviewed source policy added) | 17 passed, 1 failed, 20.479s |
| same (corrected pagination fixture) | 18 passed, 0 failed, 20.373s, exit 0 |
| `tests/platform/run.sh backup` on implementation commit | 18 passed, 0 failed, 20.802s, exit 0 |
| `git diff --check` | exit 0 |

Both intermediate pagination failures had the same fixture cause: the exhaustion
fixture repeated the exact matching backup on every page, correctly producing
`backup_ambiguous` before its expected pagination limit. The fixture now returns
empty continuing pages; the separate cross-page duplicate case still proves ambiguity.
No production workaround was introduced for the fixture error.

The CLI subprocesses call the real HTTP transport against loopback HTTP servers.
Only connection construction is redirected in the test harness, with assertions on
the production destination. Metadata principal/token checks, request method/path/body,
provider decoding, state files, polling and returned receipts use production code.
Coverage includes pending/lost/failed/zero/ambiguous/denied/malformed/oversized responses,
all-page lookup, pagination exhaustion/cycles, changed bindings and recreated source,
private network/version posture, post-completion deletion, repeat calls, symlinks,
hardlinks, corrupt state, unsafe modes and competing lock holders.

## Source identities

| File | SHA-256 |
|---|---|
| `host/cloudsql_backup.py` | `99b2d5563cdbc956c8283185d774e6e1f7e55bd9c8980fb50ba3b6a5759794c2` |
| `tests/platform/test_cloudsql_backup.py` | `567483a709ab41995098bf7075f9a697a4b95f12b84113b822cdaa3cd30438fc` |
| `tests/platform/run.sh` | `bbb135914690e4e31245dd41edfec8b1c031523cf8709d1bc3ca53eb212c1dba` |

Fixtures use only synthetic project/instance/installation/token data. Each test owns
a `TemporaryDirectory` with prefix `hyprn-cloudsql-`, closes its loopback server and
removes the directory. No user store, Docker resource, cloud resource or actual token
was used. Executor temporary source copies and initial red log were removed after
recording these results. No dependencies were added; Python standard library and
existing host identity/private-file helpers are reused.

## Guarantees and limits

- One private durable directory is required per operation and must be retained.
  Intent and pending state are fsynced before the single POST. Existing intent makes
  every later invocation read-only at the provider, including another `create`.
  Missing/corrupt/unsafe state closes; directory loss must be recovered by the owner,
  never treated as authorization to recreate the same operation in a fresh directory.
- A binding digest covers source project/instance/createTime, installation, exact
  release/configuration digests, operation UUID and reviewed source policy. Metadata
  identity is the attached staging runtime account; there is no ADC/CLI fallback.
- Provider completion requires exactly one description match across all list pages,
  the same exact BackupRun GET, SUCCESSFUL without error and ordered timestamps.
  Operation DONE alone is insufficient; no extra operation polling is necessary.
- Receipts explicitly say `cloudsql-database-only` and
  `coherent_installation_backup: false`. Read-only verification rechecks the provider;
  a historical receipt remains historical if the backup later disappears.
- Live HTTPS/TLS, Cloud SQL permissions/condition effectiveness, provider timings,
  durable host filesystem behavior across actual power loss and restoration remain
  unproven. No actual backup/restore/API mutation or IAM change was performed.
- Parent owns approved IAM application and live qualification, common deployment lock,
  writer freeze, snapshot consistency across all owners, complete manifest publication,
  product lifecycle integration and separately authorized isolated empty-target restore.
  This adapter exposes no restore or delete operation and confers no release gate pass.

Official API and permission references are linked in the scoped plan. The next action
is parent acceptance/review of the committed adapter, followed by the separately
reviewed IAM gate and remaining platform08-02 integration work.
