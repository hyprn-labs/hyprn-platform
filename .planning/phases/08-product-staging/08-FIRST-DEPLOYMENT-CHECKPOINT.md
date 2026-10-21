# First staging deployment — current checkpoint

Updated 2026-10-21. First usable staging is pending; VM running, application closed.

## Current state and next action

The owner approved the original deployment, publisher correction, network repair
and database-user-type correction. The latter was applied: original CREATE_USER
operation reconciled successfully. Do not recreate the user or reset its password.
The original private-transfer intents/password remain unchanged. The replacement
30-minute OS Login key was used; its recorded expiry has passed.

The actual DB setup then refused TLS before creating roles. Read-only diagnosis
found Google's exact SAN has a trailing dot, and Terraform's real database is
hyprn while the old runtime required hyprn_app. Full verified TLS to hyprn passed;
application roles and credential folder are empty, and owner memberships are true.
No application, native dispatcher, modeling service, tunnel or hosted Assistant
has started. No nine runtime credential versions published. Original local Assistant
remains untouched. Network/proxy and original image pulls/publication are complete.

Next: approval of the consolidated correction:
`/private/tmp/hyprn-staging-database-correction/REVIEW.md`.
Amendment SHA256 `6e474f7755de53f07f2362eab83e4d5cde1d9f09f1938cb1db9ca265068e8461`.
It replaces the database/TLS/deployment pins, reuses the existing temporary user,
permits one two-hour connection key if needed, and resumes original deployment.
It adds no IAM, infrastructure or fixed charge. Exact operations and recovery
are in that packet. Prior frozen packets are retained unchanged, not overwritten.
Original conditional ongoing access, budget, allowlist and acceptance remain binding.

## Corrected source and artifact preparation

Platform code commits cbefafe (exact TLS name, target DB preflight) and8af657a
(explicit safe database-name schema) are prepared, not applied to cloud. Product
commit3744603 pins that contract. All three exact container manifests remain unchanged.
Real native rebuild/fresh-extraction checks passed at its new exact product prefix.

Release `839a67dc216d20d301e71093b4de9e604901644293f9c156147747023b70c46e`.
Config `ad4ce2cd9738f2cb16c0f176c32e2bf48ee49f215daaaea08a3220a989990bf7`.
The new platform is staged inside that release's deployment directory, satisfying
existing loader restrictions without weakening them. Thirty existing objects are
reused; thirty new nonsecret objects total230933716bytes. Old releases remain intact.
The network update changes only its pinned source path; rules and proxy routes match.

Prepared network plan17c619f9faf37402ea9921b2314ac0fb15e8d93e624783eeaa93453576d88458;
DB plan5075acc24ee879d63d1beed497d5002a1782260d58907d6cd385a983fdaa0977;
operator plandcfd4e7eb884f0d0cdf27aac626d29ac19bcb6ab684d1e27ef667b3cf07ab522;
activation plan528a62e842d12b240c542d2cd8c92b59abf85026f91caa46fa641bb9e7f7ccc8.
These supersede old execution identities only after approval. The operator wrapper
keeps the original operation lineage50d1bf8d and has no create-user action.

## Verification and failures

Platform runner checks at relevant corrected source: database-setup16,
database-operator15, service-network-install8, service-network-probe4,
activation-install6, bootstrap26 passed. Final schema source contracts25 passed.
Initial contracts fixture pins were stale and failed; regenerated exact fixture
pins restored24pass before adding the safe-name test. An earlier sandbox repeat
failed only a loopback socket bind; authorized run passed15/15. No source test is
claimed repeated after documentation-only checkpoint changes.

Product final hosted-lifecycle21pass,21.622s, checkda13d781-dad0-4f2b-95ed-9b248f6eb50b.
Execution-config16pass retained before the final schema-only pin delta. Build-helper8
retained because helper source unchanged. Actual image/native build evidence is in
`/private/tmp/hyprn-staging-build-3744603`; payload verification passed in
`/private/tmp/hyprn-staging-payload-3744603`. Packet verify-packet.py passes all bytes,
plans, source pins, network equivalence and manifest-location checks without cloud
calls. Initial packet preparation rejected an out-of-root platform path; relocation
used existing allowed release roots. No remote action used the rejected packet.

Live diagnosis receipts, original network/publication/user receipts and all failures
remain under `/private/tmp/hyprn-staging-final-plan/application-evidence`.
New packet EVIDENCE.md links focused logs and exact build/check identities. Scoped
build volumes are retained; no build container remains running. Runner-owned fixtures
were released. No unrelated files/index entries were staged or reverted.

## Remaining obligations

Continue database roles/credentials, delete only the temporary user, verify ordinary
roles, fence old Assistant, preserve501c prior spend and11215c total, publish corrected
desired, bootstrap/attest, network-probe, activate and exercise real login/execution/
Assistant/joint-slider journeys. No model reruns on slider movement and no weakened
accuracy, containment or TLS checks. Qualification window ends22October10:00UTC;
ongoing promotion requires original four real journeys. No silent expiry extension.

Owner: this deployment workstream. Two-human isolation/acceptance, full reboot and
recovery, aggregate release qualification and automatic staging-branch delivery
remain pending. Neither a passing local fixture nor healthy endpoint establishes
these. Existing €170–220/month estimate and €100 shared Assistant budget apply.
