# Host operational retention

The platform owns operational journal limits. Scientific stores, AiiDA repositories,
execution work, deployment journals, backup sets and release trees have different
owners and are excluded from this operation.

For a reviewed release, run `python3 -I -B host/retention.py plan`, review its source
and configuration hashes, then execute `apply --approve-sha256 <plan hash>` on the
identified staging host through the existing approved deployment controller. This
is an explicit deployment step; importing or publishing the repository applies nothing.
The apply step requires root, refuses an existing different policy and linked or
unprotected paths, verifies later drop-ins have not overridden the limits, restarts
journald and verifies its service is active. A repeat with identical bytes is safe.
No cloud resources, credentials, application processes or permissions change.

The single policy also belongs to fresh host setup. Existing installations receive
this explicit step before invoking the updated setup verification; otherwise that
verification correctly reports the missing drop-in.

| Area | Policy |
|---|---|
| Persistent journal | 1 GiB target; 1 GiB reserved free; 64 MiB files |
| Volatile journal | 128 MiB target; 128 MiB reserved free; 16 MiB files |
| Journal age | 30 days maximum; rotate files at least daily |
| Docker local logs | Existing three 10 MiB files per container |
| Product records and release artifacts | Never selected or removed by this operation |

Journald removes archived journal files as it rotates; active files can temporarily
exceed size targets. No separate vacuum is invoked and 30 days of history is not
guaranteed under high volume. This is local operational retention, not the retention
policy for managed cloud audit logs. See the upstream
[journald configuration reference](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html).

If restart or verification fails, retain the installed policy and failure evidence,
inspect the conflicting drop-in or service failure, and repeat only after reconciling
it. Do not overwrite an unknown policy or rerun fresh-host setup. To revert, use the
recorded prior absence/identical state through a reviewed host change; product records
are unaffected.

## Release and execution work ownership

The installer removes only its own failed extraction temporary directory. Native
release destinations are content-identified and retained; activation pins the active
release, but there is no durable complete set of releases reserved for rollback or
recovery. Age, directory name and current activity therefore do not establish safe
removal. Automatic release/image pruning is deliberately absent. Bootstrap enforces
its existing minimum-free-space admission before installation.

Execution work belongs to AiiDA and its product owner. Deleting it from a platform
age-based job could erase pending or recoverable process evidence. No platform
cleanup touches it. A future removal must use the execution owner's terminal-state
and artifact-retention proof, and a release cleanup must first have an explicit
rollback/recovery retention set. Until then these areas can grow, so operator disk
headroom remains a real deployment risk rather than a claimed solved bound.


## Reviewed duplicate delivery archives

The platform supports an explicit cleanup of duplicate transfer archives left in
`/opt/hyprn/staging-deployment`. This is separate from installed native release
retention and never selects execution work, images in Docker, logs or scientific
stores. There is no age-based or directory-recursive deletion.

A `hyprn-deployment-archive-cleanup/v1` manifest names the exact staging host,
retained release hashes and candidate files. Keep at least the current and previous
release in that set, plus any historical representative needed to retain a unique
image archive. The live runtime identity, deployment journal's installed release
and its backup source must all be in the set. Unknown or unsettled deployment
state refuses cleanup. Hold the existing deployment lock for verification and apply.

Each candidate is one top-level `app.oci.tar`, `modeling.oci.tar`, `worker.oci.tar`
or `native.tar.gz` in an unretained historical delivery folder. It must have a
byte-identical protected retained copy, and both files must match pinned payload
inventory hashes, file hashes, sizes and modes. Every candidate is verified before
any removal; checked inode and timestamps are compared immediately before unlink.
Each retained copy is hashed once per operation and rechecked before each removal.
No directory, inventory or installed release is deleted. Missing candidate files
are already removed; a missing retained copy is a refusal.

Run the helper's `plan` on the target host and review the resulting exact hash and
reclaimable byte count. Apply only the same manifest/hash under the existing owner
authorization. Keep stdout and source identities with the release evidence. If the
operation stops, preserve its report, reconcile changed/missing candidates and
repeat only the same reviewed manifest. Deleted duplicate bytes remain recoverable
from the explicitly retained archive; reconstructing a historical transfer path is
a separate reviewed operation, never an automatic rollback substitution.

Future deployment manifests use release-stage version 2 and the protected data-disk
root `/srv/hyprn/staging/deployment`. Existing control paths remain unchanged; no
symlink redirects are introduced. This prevents repeated archives filling the OS
disk, but does not claim bounded retention for unique installed/native archives.
Their complete rollback/backup policy remains a separate obligation. Monitor data
volume headroom and retain bootstrap's free-space admission checks.
