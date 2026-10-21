# Staging host setup — approval-ready checkpoint

2026-10-21. Source commit `ef774567f8cc5b9e503763bbef5f572acb948c66`.
Owner: parent integration session. Preparation complete; application is **not deployed**.

## Delivered

`host/setup.py` generates a deterministic plan and applies only its explicitly
approved hash to the exact fresh staging VM/data disk. It checks dependencies and
blank, exclusively attached non-boot storage before formatting; installs five
pinned packages; configures data-disk runtime storage and closed container rules;
checks the actual host and records completion. Interrupted setup refuses automatic
retry. `host/setup_remote.py` verifies the frozen source/package archive, applies
through IAP using an expiring OS Login key, and reconciles/stops the same VM.

No cloud mutation, secret transfer, provider request or app startup occurred in
this batch. Read-only cloud inspection confirms the staging VM remains TERMINATED.

## Evidence on the committed tree

- `tests/platform/run.sh host-setup`: 19 passed, 0 failed (0.123 s test body).
- `tests/platform/run.sh preflight`: 19 passed, 0 failed (0.022 s test body).
- Real pinned archive metadata: all five package names/versions/AMD64 match.
- Real pinned containerd accepts the generated configuration; real pinned Docker
  `--validate` reports `configuration OK`. Isolated reviewed Linux image
  `sha256:cfb49e197e7694f2e2b3498157174acc753c7fe63a058687b38680da38e84d78`,
  network disabled, read-only root, no capabilities/secrets, bounded resources.
- Deterministic archive admission validates all 13 regular files and package/source
  hashes. No cloud controller apply was invoked.
- Fixture containers with label
  `org.hyprn-mvp.test-scope=host-package-inspection-20261021` are gone.

Private evidence: `/private/tmp/hyprn-host-setup-parent.log`,
`/private/tmp/hyprn-host-preflight-parent.log`, and
`/private/tmp/hyprn-staging-host-packages/{debian-metadata,config-validation}.log`.
Downloaded archive pins and licence references are in `host/host-packages.json`.
Docker index signature was checked with fingerprint
`9DC858229FC7DD38854AE2D88D81803C0EBFCD88`; cloudflared matches its official release digest.

Earlier failed checks: one fixture compared `/var` and `/private/var` paths;
canonical device comparison fixed it (initial 13/14, then 14/14, expanded 19/19).
Initial Debian metadata probe needed a scoped writable temporary directory;
corrected probe passed. A first inspection image lacked Python; no package code
ran in that failed attempt. No failure was hidden or waived. Native formatting,
installation and network mutation are covered by doubles, not yet proven live.

## Exact approval packet

Private folder: `/private/tmp/hyprn-staging-inventory-3k0g1h31/host-setup`.
`REVIEW.md` explains changes, risks, cost scope, command and recovery.
`deployment.json`, `plan.json`, `policy.json`, and `host-setup.tar.gz` bind the step.

- Plan SHA256: `0a18d1d19b1951fdc172b4a5ac986c387273e5ea187b3c42f5f8a5c1853c83ee`
- Bundle SHA256: `e934191bde48ea00ce1b398c820875aedd0ac7c18fbbdb175d3e36d9a8fac5e4`
- Controller SHA256: `4bf2d9d661376b75f93e54aac7e3077faff82a0c61eb649740cdfe8e01141108`

The archive is 93,052,989 bytes, contains no credentials, and is not committed.
Only documentation follows the tested source commit; it does not change the plan.

## Next action and remaining obligations

Obtain approval for the concrete start/setup/verify/stop step, including blank
100 GiB data-disk formatting. Do not apply before approval. Missing base dependencies
refuse before formatting; no uncontrolled install is used to work around them.
An incomplete intent needs stage reconciliation; do not reformat or silently retry.

Then finish scoped service routing and private SQL roles/secrets, install the
pinned app/connector, and qualify actual AMD64 execution, cloud login and study
isolation, Assistant delivery and shared-budget reconciliation, sampling/surrogates,
and required install/update/recovery behavior. Initial container networking is
closed, not an application-ready network. Opening staging needs that evidence.
Automatic staging-branch delivery remains an open owner requirement, with GitHub
settings separately reviewable. Parent retains integration ownership. This is
not final release qualification or human acceptance.

## Application outcome (supersedes pending approval above)

Owner approved the exact plan and the subsequent diagnostic inspection. The
original generic dpkg error was incorrectly reported as a pre-format dry-run
failure. Actual inventory disproved that: the intended disk was formatted/mounted,
four packages installed and Docker Engine unpacked but unconfigured. Its service
is inactive. The required nftables/libnftables1/libjansson4 packages are absent.
The diagnostic itself made no package changes and confirmed the same VM stopped.

Source `210e154` corrects the weak dependency check and provides a separate,
no-format repair bound to the exact original intent and partial state. Committed
host-setup checks: 31 passed; actual eight-archive metadata and dependency versions
checked using real Debian tools. See `runbooks/product-staging.md` for complete
failures/corrections and the exact private evidence references.

Next: approval of repair plan
`914022b3b649e61a411e4804427c8bb925d1207d4169f2b1a0b005c87d635478`,
then apply/verify/stop. Original bundle remains unchanged. No application startup,
secret transfer or new provider usage. Broader hosted milestone remains open.

## Repair outcome

Owner approved plan `914022b3b649…`; one execution reached the final network check
and refused an unexpected public TCP listener. Prior filesystem, package/binary,
Docker, ownership and firewall/IPv6 structural checks passed in that execution.
The VM is confirmed TERMINATED; no completion receipt, application or provider run.
Do not replay the repair intent. See the runbook for exact evidence.

`612995e` adds the missing listener address/port diagnostic without changing the
network rule; committed preflight group passed 19/19. Next is approval of the
prepared comprehensive read-only network/runtime inspection, then an evidence-based
completion plan. No unknown listener has been allowed or disabled by assumption.

## Current next action

The network inspection succeeded: systemd-resolved LLMNR is the 5355 listener.
Owner explicitly permits leaving the VM running through staging completion; after
the inspection's stop, the exact VM was restarted once and confirmed RUNNING.

Approve/apply finalization plan `d9578c423d42…`: one resolver drop-in disables
link-local discovery, preserves DNS, reruns strict verification and records closed
host completion. Source `38da65b`, committed host-setup 36/36. Frozen packet and
full hashes are in the runbook. It leaves the VM running. No application readiness
or live DNS-correction success is claimed before that operation.
