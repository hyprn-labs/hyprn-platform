# 08-02 host prerequisite preflight checkpoint

Status: source implementation prepared; focused and parent acceptance pending.
Owned files: `host/preflight.py`, `tests/platform/test_preflight.py`, this checkpoint.
Parent owns test runner registration, host qualification and aggregate delivery;
bootstrap executor owns the call before installer, registry and secret effects.

## Scope and observations

The current Terraform host module supplies a stopped Debian VM with an attached
persistent disk and metadata identity. It does not acquire Docker/Compose,
create service accounts/directories, format/mount the disk, install host firewall
rules or activate a Cloudflare connector. None of those actions is performed by
this preflight. Missing prerequisites refuse with named codes.

`check(target, policy_path, host=...)` reads one protected closed
`hyprn-host-preflight/v1` policy bound to exact target identity and desired digest.
It checks Debian 12/linux-amd64, systemd/Docker services, reviewed Docker/Compose
hashes and versions, actual canonical UNIX socket, daemon resource/containment
features, native execution account/group and exact container numeric store ownership, tmpfs/no swap and
the supplied CA source bytes. Actual metadata, exclusive disk and mounted-device
checks reuse `GoogleHost.check`; a caller receipt cannot replace them.

The configured native containment-probe home may be absent before initialization:
precreating it would violate the product's empty-execution-store requirement.
If present its exact ownership/mode are checked. No preflight creates it.

The firewall observation requires the real iptables-nft forwarding hook,
DOCKER-USER's first-rule metadata DROP and terminal default DROP, no unconditional
ACCEPT/RETURN bypass, disabled IPv6 on every observed interface and no unintended
public or Docker TCP listener. This is labelled minimum structural evidence;
it does not prove complete egress policy, alternate-path metadata isolation,
post-reboot enforcement or live container containment.

Closed backend bootstrap can pass while admission remains false. Live network
probes, Cloudflare connector activation, loopback routing, external Access/OAuth
qualification and execution attestation remain explicit blockers. There is no
fake externally ready state, arbitrary rule-hash approval or policy-supplied
program. Docker's `/var/run` alias must be replaced by its canonical reviewed
`/run` endpoint because the product already rejects symlink ancestors.

## Acceptance and limits

Focused tests use explicit standard-library OS/daemon boundaries and real local
policy/CA bytes. They do not run Docker, install packages, read secrets, contact
cloud resources, change IAM/Terraform, start a VM or qualify a Linux host.
The parent will register/run `tests/platform/run.sh preflight` on the committed
revision. Actual staged Debian host inspection, package provenance/acquisition,
firewall installation and external edge activation remain owner-authorized work.

Command shapes follow the official [Docker info reference](https://docs.docker.com/reference/cli/docker/system/info/).

## Focused development evidence

Initial stdlib discovery: 16 tests, 15 passed / 1 error. The macOS test runner's
Python 3.9 lacks `platform.freedesktop_os_release`; the simulated Debian boundary
patch needed `create=True`. Production Debian 12 supplies Python 3.11, and the
preflight refuses non-Linux execution before that read. The test fix preserves
that production boundary. Subsequent focused result and committed acceptance
will be recorded below.

`python3 -B -m unittest discover -s tests/platform -p test_preflight.py -v`:
- After test-boundary repair and real executable-byte pin assertion: 17 passed,
  0 failed, 0 skipped, 0.024 s.
- After defensive malformed-daemon handling and the absent-initial-home case:
  18 passed, 0 failed, 0 skipped, 0.039 s.
- `git diff --check` on the owned source/tests/checkpoint: exit 0.

All policy/CA/tool temporary directories and the temporary descriptor were
released. No socket server, Docker command or external request ran. Container
UIDs require exact numeric directory ownership, not unnecessary host login
accounts; only the native execution owner requires a real host account/group.


## Parent acceptance and forwarding correction

Parent registered the group at `c586889` and ran `tests/platform/run.sh preflight`
against source `586b103`: **18 passed, 0 failed, 0 skipped**, 0.036 s; log
`/private/tmp/hyprn-preflight-parent.log`.

A subsequent source review identified that actual Docker-reported IPv4 forwarding
must also be enabled for the app's route to private Cloud SQL. The narrow
correction requires boolean `IPv4Forwarding: true` alongside the other daemon
capabilities and adds the false case to the existing failure matrix. This source
change invalidates only preflight evidence; the parent reruns that group on the
corrective commit. No host sysctl or Docker setting was changed.
