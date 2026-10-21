# Working private staging — 22 October 2026

Live: https://staging.hyprn.ai/ui/ . Restricted to the existing named email users.
Owner continuing authorization is recorded in
`/private/tmp/hyprn-staging-install-continuation/OWNER-AUTHORIZATION.md`.
Delayed approvals and prior repairs are completed; do not replay them.

Product `a1ee452cb30426637c19c46537da4ff3caeed344`; platform runtime artifact
`3488a518cbae96b283d3ab88e5096215744f756d`. Release
`eb6f7f8b3a5263d7370f3f2ec6a0c20f36b1dbc195839ce26a908e01dd024d8f`;
config `c0a35307a16364eb4deff92007c617a5e6602fbebda71a0673bf1addb2c2a73f`;
desired sequence 11, generation `1792622649640043`.
Exact packet and evidence: `/private/tmp/hyprn-staging-exploration-ready/`.
Amendment `bc8ddb2f879f440afab5982cb57510e39226fc2318b6145da6af901742fca747`.

Publication, staging, idle-stop, desired publication, native installation, fresh
containment, startup, all 19 real network probes and private activation passed.
Ongoing private access was promoted successfully (`mode: staging`), after live
verification. First promotion collided with the scheduled renewal's journal lock;
read-back proved no promotion had occurred. The same installed promotion was then
serialized with that timer, completed, and the timer restarted. Both receipts remain.
No initialization, migration, new secret version or scientific model run was repeated
in this update. Database schema remains 6. Budgets remain EUR100 shared Assistant
and EUR170–220/month infrastructure estimate.

## Observed user journey

Chrome retained the real email-authenticated session and opened the saved study.
The first exploration after a fresh app start completed without timeout or retry;
its basis was visible by 35.346 seconds and estimated outputs followed. This is an
observation upper bound, not a precise request timing. The installed predecessor's
isolated measurement was 28.716 s cold / 0.581 s warm, down from 11.888 s warm before
the database-maintained fingerprint change. Cold verification still has noticeable
latency; it is saved-record integrity checking, not model execution.

Moving both load and flow sliders produced estimated 11.8844605254 K and
-2.15751929548 kW at 13.5964175892 kW / 0.272354721279 kg/s, observed within 11.318 s.
Selecting calculated point 2 showed 9.52380952381 K / +0.6 kW within 0.403 s.
Both curves displayed real calculated and estimated points. No manual retry.
Assistant turn `0244dc5f-ef53-4813-b03f-49b0cccc0c5c` successfully called get_analysis
and get_surrogate (accepted receipts, no tool errors), confirmed validation, and
finished idle. Authoring counts stayed 27 runs, 26 configurations, 3 analysis versions,
1 answer. No surrogate refit, sampling or model rerun occurred during these checks.

Study `ae232ccb-d48b-4e9d-928d-879d97d86d22`; answer
`1fa6d0a2-78cb-4e61-82c5-6f3f00f20a80`; surrogate
`b90ad5f0-f7cd-5874-a239-6a4c86f1658a`. The Assistant authored the brief, model,
comparison, 24 real sample runs, checked surrogate and saved answer in earlier turns.
16 training points / 1 method-selection point / 7 independent validation points;
predeclared 0.05 K or kW absolute plus 1% relative tolerances remain unchanged and pass.
Original killed nominal run is preserved; the answer cites the successful replacement.

## Verification and cleanup

On committed product a1ee452c: calculations-api 73 passed (44.43 s); UI build,
design guard, token freshness and UI contract checks passed. Nine operator guards
passed. Verified 37 actual packages, unchanged Assistant definition, 54 unchanged
worker/modeling input hashes, 8 actual UI assets and fresh native extraction.
Earlier unchanged hosted-postgres 29 and contracts 127 evidence retained.
Development failures are preserved: sandbox cache refusal before tests; new test's
initial exact recheck-count assertion corrected because internal integrity checking
adds another check; build output-file collision before Docker started; UI extraction
attempt before the completed image receipt was copied. All affected checks completed
successfully before publication. No test targeted live stores.

Six explicitly labelled, unattached build volumes were removed after delivery;
one expired temporary private key was deleted. Release archives, nonsecret receipts,
live stores/containers and the current time-limited operator key were preserved.
Evidence: `application-evidence/live-verification.json`, `final-assistant-tools.json`,
`study-before-browser.json`, `study-after-sliders.json`, `promotion-resume-result.jsonl`,
`local-build-cleanup.json`, `expired-key-cleanup.json`, and `staging-study.png`.

The prior fingerprint deployment completed one additive application migration with
successful database-only backup `1792621192860`; its packet is
`/private/tmp/hyprn-staging-stored-fingerprint`. That backup is not a qualified
whole-installation recovery proof. No new database backup or migration in this release.

## Remaining obligations

This establishes a first working private staging product, not a qualified release.
- Product/platform orchestration: automatic deployment from protected staging-branch
  merges is not implemented; product 06-06 and platform 08-03 remain open.
- Platform: full reboot and coherent whole-installation restore qualification.
- Owner: second-user sign-in/isolation human acceptance; do not impersonate Guerric.
- Product: native cancellation hardening and further cold-load/prediction performance.
- Product UI: Assistant table/Markdown rendering remains rough; no cosmetic fix was
  folded into the deployment repair.
No subscription changes or wider access are authorized by this completion record.

# Earlier staging evidence

Updated21October2026. VM and all three services remain running. Tunnel and Assistant
amendments applied successfully. Chrome email login, private study creation and real
Assistant authoring pass. Real execution exposed defects; staging is not complete.

Live product3aa4415118e7fb5e7436746f18d978a33eb83f84/platform3488a518cbae96b283d3ab88e5096215744f756d.
Release131f3e8bfef7feb85d0c476baf9f45452efb9b93886060695ad92ecda8f04a64,
config5f6a806bb00237454549f99d5e59193bc5004f4657d0f26df38d52b0f1af61ae;
desiredgeneration1792605237148907/digestace16b1a1c2e3b4fde3506b926a219d0b57e66383eaef79a8536c5ad6da3d0eb.
Assistant enablement amendment2eadb6d16c31efbfcf4c4edd12bdac0f9baa33101a6fe41734ec0aa9db0bf353
completed all phases. Containmentb13ebab0-4244-4b09-aaa8-dfdef966d9f9,
start98722d21-5dcb-4ba9-bff8-6536ec80eb34 and19 network probes passed. Stores/secrets retained.

Actual study ae232ccb-d48b-4e9d-928d-879d97d86d22 and Assistant provider session
sesn_018B8bDt8pdWS8eUwuDmQjhR retained. Assistant authored brief/model/configs/analysis;
nominal run5666c078-8c7a-4bf8-a155-7c1c036ee43f paused before upload because home absent;
adverse0495c773-498e-4658-8f32-5ab40be7cb11 queued. Existing native process
 e8ca1e78-da90-4467-bf8d-ad26d9004b41 has no scheduler job/remote workdir/output.
Do not resubmit original requests. Run list/status also exposed SQLite BLOB cast on PG;
Assistant history DB work blocks HTTP. Product corrections committedfb6ee97+3529f76.

Prepared, not applied: /private/tmp/hyprn-staging-runtime-correction/REVIEW.md.
Amendment0b528369d92a6c7ab4b6e13a1e3e7a682447d49e33ef4fbf61cfece93449a046.
Product3529f76c13e8794d7a24a8b4a7d89a6f2168d7c3; platform unchanged.
New releasefd809f9f61e0af811298b45d0f9ad867fc547e7e3552f29df8a624aceec2af5c,
config59b8a0fd76bcf0cdf6c4fb4525daa2416ae8e930295bff877f9af8bbc1e5897f.
App4776c06ec80bed1b08e3397556d95ccbae9a8635936e4878e5cc965b022c829e;
modeling/worker/UI/network/secrets/Assistant definition unchanged. Exact native bundle
built and freshly verified, new target-host containment required. Product checks
139Assistant+25PostgreSQL+125history/API+18native-owner pass;16recovery guards pass.
Full proof and initial failures linked by product06-OWNER-STARTUP-CHECKPOINT.md.

Approval requested for publication/recovery/activation. Recovery verifies exact paused
process/PID/request, creates only missing private home, interrupts existing handler once,
waits for original requests to reconcile, then replaces release without reinitialization.
Next after approval: images/files/stage/desired/recover/network-probe/activate, actual
nominal/adverse results and validated joint exploration, then conditional ongoing access.
No new resource/IAM/credential version or fixed cost. Original journals and authoring remain.

Current operator key expires19:52:04UTC21October; proposal includes exactly one replacement
2h key only after expiry. Qualification ends22October10:00UTC. InfrastructureEUR170–220/month;
shared AssistantEUR100(11215US cents total including501carried+live usage), no per-study cap.
Two-user human acceptance, reboot/recovery qualification and automatic staging-branch
CI deployment remain unfinished. Bare domain redirect deferred; entryhttps://staging.hyprn.ai/ui/.

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
