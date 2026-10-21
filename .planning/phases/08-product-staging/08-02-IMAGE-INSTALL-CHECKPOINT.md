# Authenticated restart and image retrieval

Date: 2026-10-21. Source: `7fb6cc8`. Parent-owned prerequisite of 08-02;
not whole-host qualification or a live activation.

`verify_native` checks the original pinned archive and installed file inventory,
bytes, modes and ownership before bootstrap executes any release program. Missing,
extra, linked or changed files refuse; an existing tree is never overwritten.
`images.ensure_images` pulls only exact approved registry digests through the
attached runtime identity, temporary private tmpfs Docker auth and an explicit
local daemon. It checks the returned repository digest and Linux amd64 target.
Credentials are removed on success and failure. No container is started here.

Committed-tree acceptance:

- `tests/platform/run.sh install`: 12 passed, 0 failed, 0 skipped, 0.029 s.
- `tests/platform/run.sh images`: 8 passed, 0 failed, 0 skipped, 0.013 s.
- `git diff --check` on owned files: exit 0 before commit.

Logs: `/private/tmp/hyprn-install-verification-parent.log` and
`/private/tmp/hyprn-images-parent.log`. Initial focused tests also passed. No failed
checks in this slice. Temporary filesystem fixtures were released. Image tests
replace the metadata and Docker boundaries and Linux tmpfs guard; they do not
prove registry permission, actual image pull or real host startup. Those remain
in the combined Linux/cloud rehearsal, owned by the orchestrator. No cloud
mutation, secret read or live container action occurred.

Sources: [Google short-lived registry authentication](https://docs.cloud.google.com/artifact-registry/docs/docker/authentication)
and [Docker digest pulls](https://docs.docker.com/reference/cli/docker/image/pull/).

Bootstrap must hold its deployment lock, validate descriptors/payloads first,
protect policy/source paths, and run release code without bytecode writes.
