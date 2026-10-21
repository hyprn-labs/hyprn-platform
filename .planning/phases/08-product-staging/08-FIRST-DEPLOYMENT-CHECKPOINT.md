# First staging deployment — current checkpoint

Updated 21 October 2026. VM and app/modeling/dispatcher are running. Admission remains
closed because connector verification failed. Human email-code login reached the
Cloudflare 1033 error in Chrome; application login, scientific execution, live
Assistant and answer exploration remain unverified. Stores and credentials preserved.

## Current state and next action

The approved container preparation b122a4bb succeeded. Fresh containment operation
b37cb497-4684-452b-aa9b-03263ed05132 and start 2185e83e-b418-4c05-a398-5e390e3d7b77
completed. Native owner rebind completed without initialization or migration.
`/private/tmp/hyprn-staging-container-handoff/application-evidence/` holds recover
and network-probe success: all 19 actual network tests passed, including database
TLS, required proxy routes and forbidden metadata/public/private paths. Startup
HTTP returns the expected unauthenticated 401. No scientific/provider request yet.

Activation partially installed: connector identity/token/units exist, timer inactive,
original installer intent exists with no installed receipt. Connector restarts because
it attempts DNS at blocked metadata address 169.254.169.254. A temporary collected
read-only probe in the same restricted cgroup confirmed: loopback origin times out,
local DNS connects, metadata HTTP remains blocked; root origin connects. Docker NAT
returns from 172.29.81.2, which the cgroup currently denies.

Prepared correction: `/private/tmp/hyprn-staging-tunnel-network-repair/REVIEW.md`.
Approval requested, NOT yet received at this checkpoint:
afd1cb2bcdeece8be0b4c9425ef7d066691d9e97d43ae08323950dd7b8849f3d.
It changes only connector DNS, the exact application return-address exception, and
specific origin failure diagnostics. Repair archives original intent/source, verifies
all preimages and identity, replaces three host config files and one installer source,
then repeats real connector readiness/metadata denial before bounded admission.
No app restart, credential/image/IAM/budget change. Do not blindly repeat old activate.

Focused verification: `sh tests/platform/run.sh activation-install`: 9 passed
(original new regressions: 2 failures/1 error); repair test_repair.py: 5 passed.
Real corrected connector remains unverified until approved apply. Prior 61 readiness,
23 hosted lifecycle, 32 bootstrap and live containment/service-network results remain
valid for unchanged product/runtime. No scientific/provider execution was performed.

Next: after approval, packet apply-approved.py stage then repair; verify Chrome login,
real model execution, Assistant tools, joint exploration without reruns. Only then
conditional ongoing access using corrected activation plan
70629577dfe850840817ede0436a79c4a7fc2f6036c5a7e30a0ad5ca0acbadf8.
Two-user acceptance, full reboot/recovery qualification and automatic branch deploys
remain separate unfinished obligations. Do not describe staging as usable yet.

Desired generation 1792597479844287; digest
4caf592f9bbea8463ff14e8e8a5f7dbf02f3b1975e46868c883365fd0d5150ae.
Release 708ac6900c15e1e2b1389f12332215d06d453c1fd87d0e86fa9c1055dee21459.
App fe70d83261e96f635dfec29d6781d98e49872090f8b15e4c64e43ea5fa94e886.
Product source 78814803fc87806109f19ac4b558e120a4ee53dd remains unchanged.

The replacement two-hour connection key was used; expiry 17:47:38 UTC 21 October.
No further renewal authority. Existing database-correction transport remains valid.
Qualification window ends 22 October 10:00 UTC. Infrastructure €170–220/month and
shared Assistant €100 (11215 cents total, 501 prior usage) remain unchanged.

## Previous combined startup correction

Approvalc369a6ab applied earlier: release4afd5b9 containment09976d06-4c96-4b80-bfc4-7407db232d55
passed and start456eaac1-8d70-4feb-a24b-f720f1bbb299 returned, then network probes caught
exited app/dispatcher. Actual logs showed stale Assistant continuity release/config
and actorless readiness read. Corrected application release708ac69 is published and
staged, pending the above operator handoff fix. Modeling/worker/UI/provider definition
and €100 shared budget unchanged. No tunnel/activation occurred.

## Historical state after stopped-container recovery (superseded)

Supersedes the pending d33b5d8c approval below. That approved helper applied:
qualification bb5f4d8b-4a7c-4311-a931-3ed77921f68b completed successfully with all nine
real containment probes passed, candidate executions zero. Start39a8839c-2b28-4668-9603-3e32b5c708a6
then failed component_operation_failed (exit6). The exact app/modeling containers
exited1; no dispatcher or tunnel started. VM running, admission closed. Stores and
all nine credential versions preserved; initialization remains complete.

Redacted container logs show app artifact folder absent and Rails refusing
/native/tmp/sockets on the read-only image. Read-only mount/path inspection confirms
both. No credentials printed. Actual evidence lives under the earlier packet's
application-evidence/{progress,containment-progress,start-container-diagnosis,start-logs}.json,
and /private/tmp/hyprn-staging-service-start-recovery/application-evidence/paths.json.

Permanent platform fix c0cc454 prepares the private application artifact directory,
adds only a32MiB modeling tmpfs and verifies all actual tmpfs mounts. Product b0f5372
pins that contract and includes the already-tested canary directory fix2ef0c8d.
Platform76 focused checks pass; product hosted-lifecycle21 passes36.329s, check
2b323793-5022-4de1-b149-37a0c22990a0; canary regression17 retained. Six recovery guards
pass. Native bundle built and fresh-extraction imports verified. All app image build
inputs unchanged: existing three published images reused, new cached app image explicitly
unpublished. Initial worker inventory refusal reconciled by new host-source inventory;
new live attestation required, never copied. Local test/build limitations and failures
are recorded in the packet EVIDENCE.md. Unrelated repo edits/index preserved.

Prepared, not applied: /private/tmp/hyprn-staging-service-start-recovery/REVIEW.md.
Amendment c369a6abaff76b968cb2dbfd914e6200c6e8c35a3e62dca0c8b940e0753d9655.
New release4afd5b9341dadd97fec05e98fc4d0615f9c9b7eb20e874ce98a3426d6223b68f;
23 new nonsecret objects230891836bytes,32 reused. Packet validation passed. Exact
publication/staging, desired CAS, stopped-owner recovery, native rebind/attestation,
startup, actual network checks and original activation are prepared. No initializer,
SQL migration, credential rewrite, new permission or new fixed cost. Original failed
journal is retained. Current key expires15:47:31UTC; one authorized replacement unused.

Next: obtain this exact amendment approval, then apply-approved.py phases files,
stage, desired, recover, network-probe, activate in order. Inspect any failure;
never reset intent or rerun initialization. All frozen evidence files must remain
unchanged; put new diagnostics elsewhere. Original four real acceptance journeys,
conditional promotion, two-user qualification, recovery testing and automatic branch
deployment remain outstanding. This is not a working staging or qualified release.

## Current state after qualification recovery attempt (2026-10-21)

This section supersedes the pending approval in the next section. Approval8593236f
was received, verified against all packet/external hashes, and its two nonsecret
files staged at/opt/hyprn/staging-operator/qualification-recovery-3845d94efc154c7a.
The exact helper refused all_product_writers_must_be_stopped before any recovery
mutation. No archive created; journal, initialization, credentials and sources unchanged.

Diagnosis: prior progress inspection used dockerps without-a, omitting two created
containers. App0ea718fad76a and modelingcb7ecb71f200 were prepared during initialization
at14:25:19UTC, never started, PID0, restart policy no, exact approved image/project.
The recovery's requirement for an empty container inventory was overly strict.
No container was deleted/stopped/recreated. New helper instead validates exactIDs,
images, labels, unchanged observations and never-started state; rejects any extra,
foreign, running, paused, restarting, started or altered container. Rechecks before
recovery intent. All other qualification/start actions remain unchanged.

Remaining actual read-only prerequisites passed: source closure, existing pinned
secret versions, installed product artifact, all three actual owner schemas/identities.
An inspect receipt was recorded through the real product command; journal unchanged,
no initialization/qualification/start repeated. Evidence:
/private/tmp/hyprn-staging-qualification-stopped-containers/preflight-result.json.

Prepared replacement review (not applied):
/private/tmp/hyprn-staging-qualification-stopped-containers/REVIEW.md
ApprovalSHA d33b5d8c4405be4dcb4a24a7d3dd2b3ec15fb5c121796ebdfe6aa82b99657b02;
policy78e368209ea359ba02791fef8436b60ac8eabf46eaf9c771112ce0e6d712e509.
Six local guard tests passed0.019s. Original recovery result and container diagnosis
are pinned under/private/tmp/hyprn-staging-qualification-recovery/application-evidence.
Use new targetfolderqualification-recovery-78e368209ea359ba after approval; preserve
previous staged helper. Existing key still expires15:47:31UTC; replacement unused.
No new resources, costs or authority. All original live acceptance work remains.
Chrome native accessibility reaches the existing staging Access login form; no email
or OTP submitted yet. CDP remains unnecessary; no login claim.

## Current state after approved initialization recovery (2026-10-21)

This section supersedes the earlier pending-initialization state below. Approval
 e13f2018ddb22344b600aa3eb629d78e9c4deb4713b17d3850592f2ad5f0f4d9 applied successfully:
failed undispatched journal and displaced controls/source archived, bootstrap-only
fix installed, no database or durable secret changed by recovery. Then normal
bootstrap initialized the application (all five migrations), modeling and native
stores successfully. Initialize operation7e38eb79-593e-4cea-99c0-b5a39e24c23e is complete.

Bootstrap exited2 after73.25s at actual worker qualification. Qualification operation
4e2a8e78-3c4b-47ed-bfb4-d97ea5e65f5a is a completed failed receipt; journal retains its
intent and operation_refused. Installed identity and complete migration remain.
No application containers/tunnel running; admission closed; VM remains running.
Native owner inspection and host scheduler prerequisites passed. All nine actual
synthetic probes failed only because input directories were0700 under private umask077;
worker reported Permission denied reading/input/canary.py. Candidate executions0.

Product fix2ef0c8d explicitly sets only synthetic mount directories0755. Regression
red16pass1fail, green17pass; committed-tree17pass0.147s. Not deployed. To preserve
approved images and completed initialization, prepared exact one-off compatibility
qualification with umask022 only for synthetic tests, restored077 before start.
All containment checks remain mandatory; no source/image/secret/network replacement.

Pending approval packet/private/tmp/hyprn-staging-qualification-recovery/REVIEW.md,
SHA8593236fe709e46dfc1d152f4d60b3a6c4fc4f6d4300923011a5c190411d511d.
Policy3845d94efc154c7ab4a7ea1ba8851e07a869e56e44f564a916e25453b157f08d.
Helper guard tests5pass. It archives failed evidence, requires exact stopped state,
checks actual schemas, records a new qualification ID, then starts only if successful.
No reinitialization, migration, receipt overwrite or blind retry. Not applied.
Existing key valid until15:47:31UTC; previous approval's single2h replacement unused.
No further renewal authorized. Same activation plan25fddc669681b8e1be658351cbbe6f850a3855272fcbdea88ebbea3954213748.

Evidence/private/tmp/hyprn-staging-initialization-recovery/application-evidence includes
recovery-result, bootstrap-result, progress, native-diagnosis and containment-diagnosis.
Do not overwrite these observations: next packet hashes them. Permanent fix must be
included in next product artifact build. Full live journeys and earlier remaining
release/automatic-delivery obligations still pending; no working-staging claim yet.

## Current next action

Owner approved correction6e474f7755de53f07f2362eab83e4d5cde1d9f09f1938cb1db9ca265068e8461.
It was applied through artifact publication, staging, network verification, database
roles/credentials and desired-state publication. Bootstrap installed and verified
native3744603, but stopped before issuing any initialization command because the
public CA destination directory did not exist. Journal conservatively records migration
intent; automatic retry is blocked. Do not reset or bypass that journal.

Prepared explicit unstarted-only recovery:
`/private/tmp/hyprn-staging-initialization-recovery/REVIEW.md`.
Approval SHAe13f2018ddb22344b600aa3eb629d78e9c4deb4713b17d3850592f2ad5f0f4d9.
Policy SHA510810994d2915bd1f22b75ecb8007f94a33cab1819d2486698fcb91b8a8e312.
Pending owner approval; no recovery applied. Helper verifies exact source/host/journal,
no dispatched initialization, empty stores and actual database, retains the failed
journal/controls/source in a persistent archive, clears only disposable credential
copies, applies bootstrap fixdc52b03 and permits explicit fresh bootstrap. It never
resets roles, rotates credentials, erases receipts or repeats a prior product command.

Current IAP key expires15:47:31UTC21October. Recovery review allows one replacement
2-hour key only if needed, preserving knownhosts. No automatic renewal. Original
qualification window still ends22October10:00UTC. Conditional ongoing promotion
still requires real login, execution, Assistant and joint-slider journeys.

## Completed and preserved

- Original61 artifact files and three image manifests retained; correction published
  thirty new files230933716bytes and reused thirty. Sixty files staged at the exact
  release-specific deployment root. All create-only generations recorded.
- Network source closure updated/verified under approved plan17c619f9; rules, proxy
  and permissions unchanged, IPv6 disabled, no public IP.
- Six restricted DB roles created in actual databasehyprn; all credentials authenticate
  over full verified TLS with exact absolute CloudSQLhostname. Nine numeric Secret
  Manager versions1 published/read-back verified. Assistant-provider v1 untouched.
- Original temporary userhyprn_bootstrap_20261021 deleted; six ordinary credentials
  reverified, no residual bootstrap memberships. Original intents/password/receipts
  preserved under the original private-transfer root; do not recreate/reset.
- Only local web pid3608/approved launcher stopped. Key moved to protected retirement
  path. Provider re-read: five idle sessions,501c prior spend; total11215c unchanged.
  No model/provider request made. No per-study cap introduced.
- Desired generation1792590975157515 published, SHAe357e417bcbd5a503e109bbdc6be63a47625f2323a4c69cbc4c6cc1bf6fabf58.
- Actual native bundle installed at product3744603 prefix and product artifact preflight
  passed. Normal app/dispatcher/modeling credential copies delivered to private tmpfs.
  Database schema and all owner stores remain empty; no initialize operation ID exists.
- Only product receipt: operation92d4f5dc-aecb-4010-b695-b7ad241508df, admission closed,
  completed. Original migration intent and conservative uncertain-outcome marker retained.

Exact release839a67dc216d20d301e71093b4de9e604901644293f9c156147747023b70c46e,
configad4ce2cd9738f2cb16c0f176c32e2bf48ee49f215daaaea08a3220a989990bf7.
Product3744603, platform contract8af657a remain the approved payload identities.
Prepared bootstrap-only fixdc52b03 does not change product images/native/contract.
New activation plan25fddc669681b8e1be658351cbbe6f850a3855272fcbdea88ebbea3954213748
changes only the bootstrap source pin; use only after recovery approval/application.

## Failure diagnosis and verification

First bootstrap refused isolated sibling import before installation. Read-only
replication under-I identified service_network_install missing from module search.
Explicit protected/hash-checked path invocation used identical reviewed code and
all checks; it then installed native and reached controls preparation. Missing
/etc/hyprn/trust caused failure before migration credential delivery or initialization.
Both are fixed generically in bootstrapdc52b03; source not yet deployed.

Committed focused checks: tests/platform/run.sh bootstrap29passed0.701s;
activation-install6passed0.005s. Added real isolated-Python import boundary, private
umask readability, symlink/unsafe-mode refusals. Recovery guard5passed (rejects any
dispatched operation, completed migration, installed state or changed observation).

Actual read-only verification: no product containers, no migration secret directory,
empty application/modeling/execution stores, database has zero application relations
or extra schemas, bootstrap user absent. The first SQL diagnostic failed before
connection because root with capabilities dropped could not read the service-owned
0600secret. Repeated with the retained root-owned copy of the same verified credential;
no permission was relaxed. One journal diagnostic omitted its required lock and was
corrected to use the real existing lock; no writes/operation replay were made.
Google CLI identity checks timed out before one modeling credential publication;
intent/version absence confirmed before the first actual write. Both failures retained.

Evidence root: /private/tmp/hyprn-staging-database-correction/application-evidence.
Recovery EVIDENCE.md links actual receipts, exact tests and local/remote distinctions.
Prior source checks and build evidence remain in parent correction EVIDENCE.md and
/private/tmp/hyprn-staging-build-3744603. No unchanged scientific test was repeated.
Chrome inspection twice failed in CDP focus emulation; no browser login was performed.

## Remaining work and boundaries

After recovery approval: inspect/recover exact undispatched state; normal bootstrap
and migration; real containment attestation; network probe; bounded activation; actual
human login, Assistant authoring, numerical execution and joint-slider verification
without model reruns. Preserve all accuracy, TLS, access and execution restrictions.
Remove transient credential copies only after successful startup/durable verification;
keep recovery archives and original nonsecret receipts. Native build volumes retained;
no build containers running. No unrelated changes staged/reverted.

Owner remains this deployment workstream. Two-human isolation/acceptance, full reboot/
recovery qualification, aggregate release checks and automatic staging-branch delivery
remain pending. No complete staging or qualified release claim. Existing €170–220/month
estimate and €100shared Assistant budget unchanged; no new IAM/resources/subscription.
