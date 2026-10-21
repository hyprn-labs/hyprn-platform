# 08-02 Task 1 — coherent backup prerequisite checkpoint

Status: implementation prepared; committed acceptance pending. This scoped batch
is not completion of platform 08-02 or product 06-05. Owner: backup-set executor;
parent retains aggregate host qualification and release/recovery acceptance.

## Implementation

- Combines the existing managed Cloud SQL backup adapter and product
  `native_hold`/`snapshot_files`/`verified_manifest`; no copied snapshot engine.
- Fixed pinned-native child invocation, validated product binding, checked
  protected stop/drain receipts, actual product `assert_stopped()` inspection,
  inherited deployment flock and parent fence handshake, product lock and
  continuous executor/AiiDA holds. Reconciliation inside that hold is GET-only.
- Exact runtime endpoint is checked against Cloud SQL's private address and
  instance PSA DNS before POST. Provider resource/metadata hash, owner-file
  manifest/hash, source/config/store/native/schema identity are bound together.
  The whole-set manifest is create-only and published last; incomplete scopes
  cannot be resumed into complete sets after their continuous hold ends.
- Root-owned source/native files must already have been installed and verified by
  trusted bootstrap. The bridge records source hashes and checks the fixed paths;
  it does not invent a replacement release package or qualify bootstrap.

## Verification so far

- Initial local focused invocation under pinned native Python: 12 tests, 2 pass,
  10 errors because sandbox refused loopback socket bind; no product-behavior
  failure. Subsequent checks use the registered product entry point only.
- Parent-run `./hyprn-mvp dev check platform-backup-set` before endpoint hardening:
  12 passed, 0 failures, 0 skips; 7.087 test seconds / 7.318 group seconds. Parent
  evidence: `/private/tmp/hyprn-backup-set-first.log`. This evidence does not cover
  the later endpoint/policy hardening or AiiDA-at-dispatch/deadline additions.
- Await committed acceptance for the exact delivery revision via the registered
  `platform-backup-set` group and existing platform managed-backup regression.
  Fixture stores and loopback server are isolated and released by fixture cleanup.

## Remaining obligations and limits

- Parent: run exact committed acceptance and wire trusted policy/bootstrap into
  reconciler. No resource approval is inferred; missing policy or stopped-owner
  implementation refuses the production operation.
- Parent/platform owner: qualified Linux root mounted-host run, exact IAM review,
  real Cloud SQL backup/isolated restore drill, second activation and complete
  recovery acceptance. No cloud mutation, VM start, secret transfer or IAM apply
  occurred in this batch. Local AiiDA/SQLite and HTTP-boundary evidence cannot
  establish the mounted-host or actual Cloud SQL guarantees.

Endpoint field interpretation follows the official [Cloud SQL instances API](https://docs.cloud.google.com/sql/docs/postgres/admin-api/rest/v1/instances):
PRIVATE address, instance PSA DNS mapping; cluster/write DNS is not accepted.
