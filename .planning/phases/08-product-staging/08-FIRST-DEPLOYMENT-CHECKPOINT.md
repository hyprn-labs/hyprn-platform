# First application deployment preparation — 2026-10-21

## Current stopping point

The owner approved the original deployment, publisher correction and network
repair. Network repair was applied successfully on2026-10-21: actual firewall,
bridges and proxy passed, with admission closed. Host directories are prepared;
all three pinned runtime images are pulled and verified. All61 published/staged
nonsecret files remain intact. Desired state is still absent; product/tunnel and
Assistant delivery have not started. The original local Assistant is unchanged.

Database creation first stopped on a transient Google identity timeout before
any intent/mutation. After read-only identity verification, the next attempt
created the single approved temporary bootstrap user. Its recorded CREATE_USER
operation is DONE with no error. Google omitted the default built-in user-type
field, so the operator's post-create identity check failed. Do not recreate the
user or reset its password. The original password and intent/operation receipts
remain protected under the private packet's private-transfer directory.
No database roles or runtime credential versions have been published yet.

Committed correction44bb931 accepts only an omitted type as the documented
BUILT_IN default; explicit malformed or IAM types and duplicates still fail.
Focused database-operator checks:15passed. A sandbox-only repeat failed one
loopback fixture bind (14passed/1error); the committed-tree run with socket
permission passed15/15. GET-only verification against actual Google records
confirmed the corrected parser and completed operation; no receipt was fabricated.

Next: obtain approval for the concrete operator amendment in
`/private/tmp/hyprn-staging-final-plan/application-evidence/database-user-type-repair/REVIEW.md`,
SHA256 `23f63375a3aae178d45e016cce0f8cde1bb7c1bcc38deb2725de12677532f228`.
Its pinned wrapper verifies the corrected source plan, preserves original receipt
lineage and has no create-user action. Reconcile the existing creation, then
continue role setup, secret publication and the remaining approved deployment.
No permissions, costs, payloads or user passwords change.

The network amendment's desired publisher and activation SHA remain binding:
`57262e02cf8c3c11b379cfa3eb2a8d98be338e96557632ba9d2664c7c2381c37`.
The original operator key expires12:52:09UTC. The one replacement30-minute key
already approved in the network amendment has not been used. Preserve knownhosts.
The initial qualification window ends2026-10-22 10:00UTC. VM remains running;
no live login, contained execution, Assistant or slider success is claimed.

## Frozen source and evidence

- Product source: `ac1fe308b7936e951c90caf0de6a60cd0d0ccb33`.
- Platform host source: `3fb8aa13b334865a385414361800b73acf9ee1ee`.
- Consumer contract pin: `2a3cc534ac1e044ecb15c327b37f97cc77293323`.
- Release digest: `62e216ca44884eb96868b2210c11c08e3dc28371d3a150179641f12a2f0b4b0f`.
- Final staging manifest: `7606980e07fc5f1b1d3242fe3ecb8264fe805089546f94fd4170e6b166c56d85`.
- Publication plan: `ef8100ec8dcd0b4865471843353d7bf2109ea6e4d11bfb613224aa214e4f876e`.
- Activation plan: `9ef83f013b38721844c9cf0224bd7e3be4dc1cb1b0df354f97fe90bd797ba8b7`.

The payload contains actual verified AMD64 OCI archives, native bundle and build
provenance. See product build checkpoint and the platform database checkpoint for
artifact/test detail. The final manifest stages 61 nonsecret files, 1,098,528,133
bytes; no credential or live store is included. Private operator scripts and
manifests are hashed by the root plan. Their final read-only verification checked
source hashes, all publication bytes/sizes, rendered plans, exact binding/runtime
agreement, budget continuity and script syntax; exit 0. It performs no cloud call.

## Focused evidence retained

Platform runner groups already passed on their relevant implementation commits:
contracts 24; service-network 5; service-network-install 7; preflight 21;
service-network-probe 4; activation 8; activation-install 6; database-setup 15;
database-operator 13; release-stage 11. Final bootstrap hardening on 3fb8aa1 passed
26 tests via `tests/platform/run.sh bootstrap`. Actual isolated PostgreSQL/TLS
migrations/role boundaries and proxy positive/negative paths are recorded in the
existing checkpoints; they were not repeated without a source change.

Product groups: hosted-lifecycle 21, cloud-execution-config 16, cloud build helper
8. Native extraction/import and all three OCI graphs verified. An initial native
fixture disk-budget refusal was resolved using an explicitly larger isolated
budget, without deleting shared cache. No passing mock is treated as live staging.
This checkpoint-only commit does not alter any tested or frozen host input.

## First-use acceptance and remaining obligations

The approved batch must prove real Cloudflare login, native containment/execution,
Assistant tool authoring and jointly movable answer sliders with calculated or
validated estimated values and no model reruns. Pending cloud SQL ownership,
secret publication, live network and product startup conditions fail closed.
Temporary credentials remain protected until durable publication and verification;
uncertain mutations reconcile read-only before any further effect.

The host preparation corrects shared control-folder traversal while leaving
secret folders private, and keeps the deployment journal outside all owner data
stores. It runs after the network installer verifies the previous setup. Exact
source and operation bytes are in the private packet, not a broad authorization.

Remaining owner: this deployment workstream. Two-human isolation and acceptance,
full reboot/recovery and aggregate installed-release qualification remain pending.
The first working staging milestone does not complete a qualified release. The
automatic staging-branch delivery workflow is not yet implemented in either repo;
prepare that narrow GitHub/authority delta after the first installed path works.
Existing shared Assistant approval and all prior spending remain intact. The
narrow Secret Manager master-copy exception for machine runtime credentials is
explicitly approved in the original deployment review.

No unrelated planning/design edits were staged or reverted. Build evidence and
scoped build volumes remain retained for review; no running build containers remain.
