# 08-02 closed host bootstrap checkpoint

Status: scoped source prerequisite implemented and focused acceptance passed;
08-02 and hosted qualification remain incomplete. Owned files: `host/bootstrap.py`,
`tests/platform/test_bootstrap.py`, this checkpoint. Parent owns runner registration,
aggregate integration and authorized Linux rehearsal; other executors own preflight
and product owner-schema inspection.

## Delivery and exact evidence

- `bb16108e4774ef52e592eff973cf6c91335b93fa`: protected bootstrap policy, fixed
  module wiring, authenticated native preparation, closed secret/control lifecycle,
  real deployment-lock reuse and coherent backup integration; 25 focused tests.
- `0884263`: require mode-0600 target and active lifecycle bindings before effects.
- Parent `43f117aa2a0a4a10d2769033326680d8f922a8a5`: registers bootstrap acceptance.
- Product reference observed during integration:
  `6b63335bc0b4493854f469cc9a0a28e920d12408`.

Focused command: `python3 -B -m unittest discover -s tests/platform -p
 test_bootstrap.py -v` (single command without the displayed wrapping). Final
source run passed 25 tests, 0 failures/errors/skips, 0.365 seconds after the
private-binding correction. Earlier development runs passed 19, then 22, then
25 tests; no failed bootstrap run occurred. Parent independently ran
`tests/platform/run.sh bootstrap` on committed `43f117a`: 25 passed, 0 failures,
0.364 seconds. Evidence: `/private/tmp/hyprn-bootstrap-parent.log`, SHA-256
`3dae36d33f4c435801b99600b3243e0d4e1a1d870b803730f476e04db3fcd7de`.
Tests use scoped temporary directories released by fixtures and no persistent
service, container, provider resource or secret. The checkpoint-only delta needs
no duplicate behavior run. The first checkpoint commit was refused by the local
terminology hook; its flagged prose was rewritten without changing behavior. Any
subsequent behavioral integration requires its
appropriate focused acceptance.

| Delivered file | SHA-256 |
|---|---|
| host/bootstrap.py | 55f3dd778ed7a357d5180e1d247cf7851962c46c46f29094a82aa8f0a07b4638 |
| tests/platform/test_bootstrap.py | df6477200fe518ecadf895617f8d1f025b288a87cd00d836271f8b2f3e22e84e |

## Executable boundary

The fixed CLI is `python3 -I -B /reviewed/platform/host/bootstrap.py --policy
/protected/bootstrap.json`. The actual reviewed installed platform path and
interpreter still need host provisioning; no speculative systemd unit is shipped.
Production execution requires Linux root, protected platform source, private
policy/bindings and exact reviewed descriptors, archive inventory and desired
hash. The policy contains paths, hashes and bounded choices, never commands.
`initialize` is explicit. Updates pin the active installation and require the
separate protected coherent-backup policy and explicit exact resource approval.

The outer deployment lock spans live Google/kernel host fencing, the immutable
GCS desired read, journal anti-replay checks, separately pinned preflight,
authenticated native archive installation/verification, image acquisition and
secret preparation through the existing lifecycle sequence. Nested reconciliation
uses the actual held descriptor and checks its lock, not a receipt. Installed
source and Python hashes derive from authenticated archive bytes; reused trees
are checked exactly before code execution. Registry authentication uses the
parent-owned image helper and its separate private tmpfs scope.

Normal secret consumers use the attached service identity and the exact approved
versions. An update requires unchanged bindings and rechecks real existing bytes
against the provider; it cannot authorize rotation from an old delivery receipt.
Assistant controls and database CA are copied only inside the migration scope,
after old writers stopped and the coherent backup completed. Migration credentials
and their temporary private binding are removed on scope exit. Incomplete backup
sets and uncertain journals remain available for operator recovery.

The real reconcile sequence ends with closed admission and qualification_pending.
Repeating an exact completed sequence checks the installed identity and recloses
admission; it does not retry uncertain work or silently restart a stopped host.
CLI failures use bounded reason codes and never echo secret values or arbitrary
arguments. Before host binding is established, failure reports admission unverified
instead of claiming it was closed.

## What the tests prove and what remains

The tests exercise protected closed policy parsing, exact pins, link/mode refusal,
real local atomic files, authenticated tiny native archive extraction/reverification,
tamper detection, actual deployment flock retention, sequence recovery refusal,
stdlib secrets import isolation and the isolated CLI argument boundary. Fixture
native bytes are deliberately non-executable. They do not execute the installed
product lifecycle, pull images, read real secrets, contact Google, create a backup,
start services or prove a Linux mount/firewall/containment boundary.

The separately owned `preflight.check(target, policy_path, host=host)` connection
uses the agreed actual host checks and requires bootstrap_ready true,
admission_ready false and the exact reviewed Docker path/hash. At this checkpoint
its source exists but its commit and focused acceptance remain owned by the
preflight executor and parent. Bootstrap does not interpret structural firewall
checks as network or edge qualification.

Before an authorized Linux rehearsal: provision the reviewed platform tree,
Debian packages, service identities, private directories, resolved Docker socket, persistent
disk mount and no-swap tmpfs, reviewed network rules, exact artifact/descriptor
inputs and policies. Then exercise actual initialization, two-release replacement,
interruption/recovery and backup/restore at the public installed boundary. Live
containment, Cloudflare/Access/OAuth ingress, scientific workflow and human
acceptance remain required before admission can open. Missing cloud permissions
remain read-only refusals; this task made no IAM/cloud/settings mutations, no
actual secret transfer, no backup creation and no VM/service start. Parent owns
these remaining integration and explicitly authorized deployment obligations.
