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

## Durable artifacts and bounded transfer cache

Object storage is the durable source for published release artifacts; the VM's
transfer folders are a disposable local cache. Keeping another archive copy on the
VM does not make storage scalable. Successful v2 staging now saves a protected
`transfer-receipt.json` containing its exact destination/object/hash/size mappings.
The receipt is create-only, belongs to that release and is saved after every
transfer succeeds. No object location is inferred from a display name or path.
V2 staging also requires the mounted data disk and enough space for the complete
incoming transfer plus a 4 GiB reserve before writing.

A `hyprn-deployment-cache-policy/v1` document has these exact fields:

| Field | Meaning |
|---|---|
| `identity` | Existing exact attached-host identity, same shape as release staging |
| `max_cleanup_bytes` | Maximum local/remote archive bytes verified per pass, 2–4 GiB |
| `max_seconds` | Verification deadline, 30–600 seconds; in-flight network reads also have a 30-second timeout |
| `max_cache_bytes` | Alert target for known transfer archives, 2–64 GiB |
| `min_free_bytes` | Required free-space alert threshold on root and data disks, 1–32 GiB |

A practical initial policy is 2 GiB per pass, 600 seconds, a 12 GiB archive target
and 4 GiB free-space threshold. These are infrastructure cache budgets, never
scientific input or execution defaults. The cache target is an observable operating
target rather than permission to remove recovery artifacts. A pass unable to reach
it reports pressure and exits 3; staging still refuses insufficient headroom.

### Install and invoke

1. Prepare the nonsecret policy with the reviewed host identity. Run
   `python3 -I -B host/deployment_cache_setup.py plan --policy <policy.json>`.
   Its plan pins policy bytes, seven helper source hashes, immutable snapshot path,
   service and timer. It neither accesses staging nor starts cleanup.
2. Through the existing reviewed deployment controller, stage the exact protected
   source files and policy. Run the same helper with
   `apply --policy <policy.json> --approve-sha256 <installation plan hash>`.
   Installation uses the deployment lock, verifies the attached host and data
   mount, installs immutable code/policy, reloads systemd and enables the timer.
   For a later policy/code update, include `--previous-plan-sha256 <installed hash>`
   in both plan and apply. Unknown unit edits or an unmatched prior policy refuse
   replacement. The installed receipt is `/etc/hyprn/deployment-cache-install.json`.
3. After successful activation, optionally invoke
   `systemctl start hyprn-deployment-cache.service`. The same service runs hourly
   with up to five minutes of jitter; boot delay is fifteen minutes. It is limited
   to 25% CPU, 256 MiB memory, 16 tasks, idle I/O and a bounded service timeout.
   Its filesystem is read-only except the two transfer roots and deployment
   journal; it has no product-store write mount.
4. Retain the service's JSON output in the operational journal. Inspect with
   `journalctl -u hyprn-deployment-cache.service` and monitor nonzero service exits.
   A busy deployment is a successful `skipped / deployment_in_progress` result;
   the next scheduled pass retries. It must not fail application deployment.

`deployment_archive_cleanup.py discover --policy <policy.json>` is the read-only
inventory operation. `maintain --policy <policy.json> --approve-sha256 <policy hash>`
is the service operation. Both derive current, installed and rollback release
identities from protected runtime/journal records under the existing deployment
lock. An incomplete deployment or unknown rollback identity refuses cleanup.

Only the four known top-level archives are candidates. Receipt-less legacy files,
unknown files, all inventories and all current/rollback release folders remain
preserved. Changed, linked or unprotected candidate files are refused. Each chosen
local file must match its payload inventory and transfer receipt. The same exact
SHA-256 and length must match a streamed object-store read pinned to the observed
GCS generation; this allocates no second local archive. Every selected candidate
passes before the first unlink, and each local inode is checked again immediately
before removal. A remote mismatch, interruption or deadline leaves all selected
local archives intact. Object storage is never modified by this process.

Reports include retained releases, protected/unmanaged archive bytes, eligible and
selected bytes, removed paths, generation/hash/size recovery references, root/data
free space before/after, remaining work and pressure. Work exceeding the per-pass
budget remains eligible for subsequent passes. This makes backlog and storage
limits visible instead of moving silent exhaustion to the data disk. Receipt-less
legacy archives need the separately reviewed duplicate cleanup or an explicitly
verified source receipt; no unverified automatic backfill is performed.

The object bucket's private/versioned retention and recovery controls remain in
force. Restore an obsolete transfer only from the reported exact generation and
verify its SHA-256 before reuse. Installed native releases, Docker images, scientific
stores and execution scratch have their own owners and are not collected here.
Future horizontal workers should use per-worker bounded scratch and the same durable
object references; no shared writable scratch filesystem or new cloud resource is
introduced by this lifecycle.
