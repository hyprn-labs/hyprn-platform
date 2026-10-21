# First staging deployment — current checkpoint

Updated2026-10-21. First usable staging remains pending. VM running; browser and
scientific admission closed; no product service running. Local web Assistant stopped
as explicitly approved; authoring records/native processes preserved.

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
