# 08-02A checkpoint — 2026-10-20

Status: secret-delivery prerequisite implementation complete; full 08-02 lifecycle
and staging admission remain incomplete. No cloud mutation or real credential
read was performed. Parent owns integrated rerun and shared planning updates.

## Source and checks

- Branch: `codex/platform-contract`; no worktree.
- Base: `8647fad9a5245fa5ee22b0f2089727a96654ba68`.
- Initial implementation: `254da66745bbc9ef294363cb1cd038ea1c950156`.
- Final implementation: `5f317c97a8440f10887590d0cd7309494f7e40b5`.
- Files: `host/secrets.py`, `tests/platform/test_secrets.py`, the `secrets` group
  registration in `tests/platform/run.sh`, and `runbooks/runtime-secrets.md`.
- `python3 -B -m unittest discover -s tests/platform -p test_secrets.py -v`:
  initial 13 passed / 0 failed (6.632s); expanded boundary checks 16 passed /
  0 failed (6.709s); attached-identity correction 17 passed / 0 failed (8.454s).
- On committed implementation: `tests/platform/run.sh secrets` → 17 passed /
  0 failed, 8.180s, exit 0.
- Parent integrated rerun at `254da66`: same group → 17 passed / 0 failed,
  8.319s, exit 0.
- Parent review found a bootstrap dependency cycle: the first provider-secret
  version must be created before runtime agent IDs and version pins exist.
  `5f317c9` removes the transfer runtime argument and instead validates explicit
  staging project ID/number and the fixed approved target. Delivery/cleanup still
  require runtime. Updated `tests/platform/run.sh secrets` before commit →
  18 passed / 0 failed, 8.320s. This source delta invalidated the earlier 17-test
  acceptance; the parent performs the committed-tree 18-test rerun.
- `git diff --check` → exit 0. No deleted files in the source commit. Stub scan
  found no TODO/FIXME/placeholder in owned source/tests/runbook.
- A read-only `docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}}'` probe
  failed with Docker socket permission denied. No Docker/container qualification
  was attempted or claimed; the scoped task intentionally records that limitation.
- All test `TemporaryDirectory` scopes were released. No test output, tokens,
  secrets, cloud resources or runtime stores were written into the repository.
  Stub payloads are synthetic constants, not credentials.

## What this proves

The CLI validates the closed runtime schema and fixed aliases, project identity
and numeric versions. Real file operations exercise 0600 secret files, 0700
directories, per-consumer isolation, exclusive locking, atomic batch publication,
numeric rotation requiring cleanup, cleanup inventory validation, no-follow paths,
links/unexpected-content rejection and cleanup after fetch failure.

Transfer uses the unmodified CLI with a controlled gcloud executable. It checks
the expected Google project/secret, refuses unsafe source files, sends payload
only on stdin, keeps logs/value output empty, fsyncs a metadata-only receipt before
dispatch and refuses a second attempt after either success or ambiguous failure.
No actual cloud API or credential store is accessed in this suite.

Production attached-service-account mode uses fixed metadata and Secret Manager
endpoints through Python's standard library. It checks metadata project ID/number
and the Terraform-defined runtime service account before obtaining a token;
there is no ADC, CLI, proxy, redirect or credential fallback. It checks the returned
version resource and CRC32C. Transport-seam tests verify wrong-principal rejection
before token request, fixed version paths, no gcloud/ADC use and the standard
CRC32C vector `123456789` → `3808858755`.

## Limits and remaining ownership

On macOS, the delivery test launcher substitutes only `require_tmpfs` and consumer
UID assignment. It exercises the parser, implementation, filesystem, gcloud stub
and permissions, but does not prove Linux root-to-service UID/GID assignment or
tmpfs. The unmodified CLI rejects this unqualified host before fetching a secret.
Attached-identity tests substitute HTTP transport; live IAM, metadata routing,
TLS, effective container mounts and production SDK retry behavior remain unverified.

The runbook requires isolated GCP Linux qualification, swap disabled, effective
read-only single-file mounts, cross-consumer denial and failure/recovery rehearsal
before admission. The parent reconciler must fence writers, stop/unmount before
rotation, deliver migration/backup credentials only for their operation, guarantee
cleanup and handle interrupted directories. This slice does not implement those
lifecycle obligations. `cloudflare-tunnel` is outside `SECRET_CONSUMERS`; host
tunnel credential delivery/lifetime remains in 08-02.

The operator identity mode requires dedicated HYPRN configuration and ADC paths;
it is not the VM runtime path. The approved transfer command requires the platform
owner's explicit go for the exact target/source, not just the CLI approval flag.
Its receipt must remain in durable private storage outside Git/Terraform state.
Uncertain results require metadata/audit reconciliation; never bypass the receipt
by silently choosing a new directory or removing it to retry.

Parent owns `.planning/STATE.md`, `ROADMAP.md`, requirements and final integration;
these files were already being edited and were deliberately left unstaged. No
broader requirement or phase is completed by this prerequisite.
