# Platform 08-01B checkpoint — 2026-10-20

Complete: offline dispatcher contract amendment. No cloud operation, lifecycle
implementation, boot qualification or human acceptance is claimed.

- Branch: `codex/platform-contract`.
- RED: `dde3e04`.
- Implementation/tested commit: `48963080e9e4249dc4ade52ab5e9615ff4175234`.
- Schema SHA-256: `67eee28b2c1b8b64078d0cf157d562fc6a09547d12045d158d8238ff17b549f1`.
- Renderer SHA-256: `193abe2bd70a4c947d79b9208bf107845541906ece67e2d1d8312df60590044a`.
- Synthetic configuration SHA-256: `5a99448eda3f04c08e89d138d7b11799ffbc5966dd0a402563c056c06685c69e`.

## Verification

- `tests/platform/run.sh contracts`: RED twice, exit 1; 13 tests, 12 passed,
  1 planned failure because dispatcher template was absent. Second run captured
  unchanged evidence for the required classifier.
- `node "$GSD_TOOLS" check tdd-red-evidence .planning/phases/08-product-staging/08-01B-RED.json --raw`:
  exit 0, RED_EVIDENCE_OK. Raw report is ignored because it includes local paths.
- GREEN: same registered command, 13 passed after renderer implementation.
- Expanded closed-role/authority tests: same command, 15 passed.
- Final exact environment audit: same command, 15 passed, 0 failed (2.635 s).
- Required committed-tree check at `4896308`: same command, exit 0;
  15 passed, 0 failed (2.529 s).
- `git diff --check`: exit 0. No task commit deleted files.
- Stub scan: no TODO/FIXME or placeholder behavior introduced.
- Every test TemporaryDirectory was released; no installation or cloud resource
  was touched. No dependencies installed. No unexpected failures occurred.

## Product interface

| Consumer | Credentials |
|---|---|
| App | modeling-auth, assistant-provider, db-app-request, db-app-auth, db-assistant-background |
| Dispatcher | modeling-auth, db-app-request, db-dispatcher-background |
| Modeling | modeling-auth, modeling-rails |
| Native execution / worker | none |

Required database fields `assistant_background_role` and
`dispatcher_background_role` are exact constants `hyprn_assistant_background`
and `hyprn_dispatcher_background`. Secret alias versions are positive integers.
Generic secret file variables retain the documented HYPRN_SECRET convention;
role variables are HYPRN_MVP_DATABASE_ASSISTANT_BACKGROUND_ROLE and
HYPRN_MVP_DATABASE_DISPATCHER_BACKGROUND_ROLE. Dispatcher has no auth role.

The dispatcher shares the pinned app image/UID, mounts only the application
artifact subtree read-write at /data/artifacts, and uses fixed stdio with no TTY.
Its host-dispatcher profile excludes ordinary Compose startup. Host-owned
run/attach and child lifetime replace no current local behavior: product 06-05
must implement cloud startup and bridge adaptation. Internal network alone
cannot reach private SQL. Host-controlled database routing and exact
modeling/SQL egress policy are explicit startup prerequisites, still unproved.
Provider/metadata access, public ports and Docker socket remain forbidden.

Source/runtime/artifact pins were refreshed only in synthetic fixtures; exact
pin checks were preserved. No Managed Agent IDs or provisioning settings were
added; that is the next separately owned amendment.

## Remaining ownership

Parent reruns this acceptance command and owns global STATE/ROADMAP/REQUIREMENTS
integration. Those pre-existing dirty records, infrastructure, runner, runbook,
ADR index, cloud spec and product source were not staged or edited. Subsequent
metadata commits add only this checkpoint and summary; they do not change the
tested implementation.
