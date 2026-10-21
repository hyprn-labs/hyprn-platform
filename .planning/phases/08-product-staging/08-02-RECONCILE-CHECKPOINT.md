# Task 1 host reconciliation checkpoint — 2026-10-21

Status: scoped implementation delivered; 08-02 remains incomplete. This is not
Linux/GCE lifecycle acceptance, deployment authorization or human acceptance.

## Revisions and ownership

- `d719b003998ad2c01040edbf4b53411e72dbab01`: reconciliation primitives, focused tests, scoped plan.
- `167ef7b0bddb24d89a0b8e5d4a2b8b7fbc76acac`: isolate fixed sibling secret-loader import from Python stdlib `secrets`.
- Product source inspected at `488c02d77acb6d094c3f24aa3cac5f6184f55fb1`; no product code changed by this executor.
- This later checkpoint is the only subsequent delta owned here. Parent owns integration and final qualification; backup executor owns its adapter.

## Implemented behavior

`Target` checks exact closed descriptors/configuration. `GoogleHost` reads attached
metadata identity, live instance/disk ownership, retired-host stopped state,
READ_WRITE_SINGLE attachment, Linux kernel mount UUID/device and generation-bound
GCS current desired bytes. Read errors, redirects, missing permission, unsupported
mounts and unproven replacement refuse; this code creates no cloud resource.
`Product` verifies bootstrap-pinned protected scripts/interpreter and payload
inventory, invokes only fixed bounded lifecycle argument lists and checks JSON
identity/results. No descriptor can supply a shell command. Importing after
stdlib `secrets` preserves the standard module.

`Journal` retains monotonic sequences, desired generation/digest, host fence,
operation intents/completions, migration checksum/state and installed identity
under an actual process-exclusive deployment lock. Writes fsync file and parent.
Reconciliation retains the prior installed identity until migration completes,
requires explicit empty initialization or coherent backup before replacement,
uses operation-scoped migration bindings, attests before native start, and always
ends closed/qualification-pending. Interrupted migration or uncertain operation
cannot be retried by submitting even a higher sequence. No automatic restore,
rollback, admission opening or fabricated applied state exists.

## Exact verification

- Red: `python3 -B -m unittest discover -s tests/platform -p test_reconcile.py -v`: 1 import error before implementation.
- Development focused tests progressed through 1, 22 and 24 passes, 0 failures after their changes.
- `tests/platform/run.sh reconcile` at `d719b003998ad2c01040edbf4b53411e72dbab01`: 24 passed, 0 failed, 0 skipped, 0.489 seconds.
- Review regression red: focused command above: 24 passed, 1 failed, because importing after stdlib secrets selected the wrong module.
- Import fix focused command: 25 passed, 0 failed, 0 skipped, 0.587 seconds.
- `tests/platform/run.sh reconcile` at `167ef7b0bddb24d89a0b8e5d4a2b8b7fbc76acac`: 25 passed, 0 failed, 0 skipped, 0.519 seconds.
- `git diff --check -- host/reconcile.py tests/platform/test_reconcile.py`: exit 0 before implementation commit; this does not prove behavioral acceptance.

The tests exercise the public reconciliation API with explicitly labeled product
and host protocol peers, real durable files, real concurrent-process flock, real
subprocess timeout/output bounds and a substituted Google HTTP boundary. They do
not substitute a fake receipt for production host authority. The two-activation
protocol test is not a real store-preservation test. No Docker, Google API, backup
creation, VM start, secret transfer, IAM or GitHub setting action was run.

An initial sandbox write attempt outside the product writable root was refused;
no intended files were created and its zero-test discovery is not evidence.
The assigned sibling-repository writes succeeded via scoped escalation. No
approval review rejection or unresolved filesystem block remains.

All TemporaryDirectory fixture scopes were released, child processes were waited
or killed on timeout, and no retained test store or artifact was created. No user
installation was a test fixture; unrelated modifications/index entries preserved.

## Artifact identities (SHA-256)

| File | Digest |
|---|---|
| host/reconcile.py | 2d4eacf65d90708f2a1b36a7d59ab4ad927ec4887837299a814ba15fc6d07949 |
| tests/platform/test_reconcile.py | e329c7e159abe3e5fb56b925c6e5ed2483ccc71bac75ecf864de74dce077dbaa |
| host/contract.py | 918a2b4343da2767ceaf82a30e821e02847457e835288640ee6d73de5b7db0ca |
| contracts/v1/deployment.schema.json | 718e7467661a15df096f166529ce6fc5aa51bc8f03c25811ee4d0fad9b6b8453 |

## Integration prerequisites and remaining risks

1. Trusted bootstrap must wire the Python API, protected prepared release/payload
   paths, exact interpreter/script pins, durable installation-disk journal,
   reviewed disk/retired-host policy and temporary migration-secret context.
   There is deliberately no installable systemd unit or caller JSON receipt that
   can authorize this incomplete bootstrap. Artifact installation/extraction,
   secret rotation, effective network policy and Linux tooling remain unqualified.
2. `Product.compatibility()` deliberately refuses real second activation with
   `owner_schema_observation_unavailable`: current product inspect returns only
   the application migration ledger (string SQL migration IDs); modeling and
   execution live schema observations and their mapping to release integer store
   contract versions are missing. Unchanged declarations do not prove this.
   Changing store declarations is also refused. Parent owns the real owner-probe
   contract/adapter and compatibility acceptance before enabling replacement.
3. Wire backup callback to `backup_set.create` using inherited journal lock,
   persisted drain/stop operation IDs, fixed active binding, reviewed private
   backup policy and explicit resource approval. The callback is trusted host
   implementation, never a caller-supplied successful-backup receipt. Parent and
   backup executor own integration; current tests explicitly use protocol peers.
4. GCE ownership checks require reviewed `compute.instances.get` and
   `compute.disks.get` permissions. None were granted. READ_WRITE_SINGLE,
   fixed by-id device naming, nonpartitioned mount and metadata behavior need a
   real scoped Linux/GCE exercise; unsupported cases refuse. GCS publisher
   authority remains the documented platform trust boundary.
5. Current product admission-opening refuses without trusted host qualification.
   No execution/browser access is opened. Whole-host effective isolation,
   identity, provider spending continuity, scientific qualification, reboot
   renewal, second activation preserving seeded private records and isolated
   Cloud SQL recovery remain mandatory parent-owned acceptance gates.
