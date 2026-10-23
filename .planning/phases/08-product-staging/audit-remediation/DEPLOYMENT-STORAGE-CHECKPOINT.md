# Deployment storage checkpoint — 2026-10-23

Implementation: `63fa0c2` (platform repository).

Future release-stage/v2 transfers require the mounted data disk and use its
`deployment/` directory. Historical v1 destinations remain unchanged. The new
cleanup helper removes only exact duplicate deployment archives after checking
host identity, deployment lock/state, current and backup retention, both pinned
payload inventories, byte hashes, and file identity. Unknown or unique artifacts,
metadata, installed releases, backups and scientific records remain untouched.

## Verification on committed tree

- `tests/platform/run.sh release-stage`: 15 passed, 0 failed, exit 0.
- `tests/platform/run.sh deployment-storage`: 7 passed, 0 failed, exit 0.
- `git diff --cached --check` passed before implementation commit.
- Initial cleanup test discovery failed because isolated sibling loading could
  not import `contract`; explicit trusted sibling loading fixed it. Both groups
  then passed before commit and once on the committed tree. No later source delta.
- Tests use temporary scoped fixtures, released automatically; no live changes.

## Prepared deployment recovery

Read-only host inventory found 27 transfer folders containing 24.887 GiB of
archives. The exact private plan in
`/private/tmp/hyprn-deployment-storage-plan/REVIEW.md` selects 46 duplicate
modeling/worker archives totalling 15,389,270,016 bytes. Canonical manifest SHA-256:
`37168b6197c151ecd1411bc22d851f3522f0feb3e928a2458f094af55daa4c42`.

Current and previous release folders plus two historical image-family copies are
retained in full. All unique app/native artifacts and every payload inventory are
retained. The host helper must still perform its real dry-run byte verification;
no cleanup, source installation or live data mutation was performed by this task.
The parent deployment controller owns reviewed installation, dry-run, apply and
post-cleanup disk/health measurements. New release manifests must use v2.

## Remaining scope

This protects the OS disk and reclaims verified duplicate transfer archives.
It is not a blanket retention policy for all unique historical payloads on the
data disk; ordinary space admission remains enforced. Live deployment and human
acceptance are pending parent integration. Unrelated planning edits were preserved.
