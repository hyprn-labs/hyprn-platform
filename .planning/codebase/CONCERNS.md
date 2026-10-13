---
last_mapped_commit: a393bda2510b521148d626a02e4a5aef58dae1d6
last_mapped_at: 2026-10-13
---

# Codebase Concerns

**Analysis Date:** 2026-10-13

## Tech Debt

**Control plane does not exist yet — spec describes target, repo holds only Ada/Codd:**
- Issue: `docs/specs/agent-fleet.md` and `docs/adr/0006-agent-first-operating-model.md` describe gateway, controller, queue/dispatcher, loop registry, credential broker, run runner, budgets, kill switch, and eval/learning loops. None exists in the repo. Only the single-host engineering path (`agents/host/`, `agents/wake/`, `infra/agents/`) is implemented.
- Files: `docs/specs/agent-fleet.md`, `docs/adr/0006-agent-first-operating-model.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`
- Impact: Phases 3–7 cannot start without greenfield builds; every M2/M3 requirement (CP-01–CP-06, RT-01, LOOP-01–LOOP-03, LRN-01–LRN-04, FLT-01–FLT-08) is pending.
- Fix approach: Accept ADR-0006 first (Phase 3 gate in `.planning/STATE.md`), then build gateway → controller/run-state → broker/runner → one loop, in that order. Do not start Boole loops before CP-01–CP-06 land.

**Fleet registry duplication (`agents.txt` + `wake.json` → `fleet.yaml`):**
- Issue: Agents are declared twice in incompatible formats — `agents/host/agents.txt` (provisioning source of truth) and `agents/wake/wake.json` (wake service config). Target `agents/fleet.yaml` (FLT-01) does not exist.
- Files: `agents/host/agents.txt`, `agents/wake/wake.json`, `agents/host/provision.sh`, `agents/wake/provision.sh`, `infra/agents/variables.tf`
- Impact: Adding/removing an agent requires coordinated edits in three places plus Terraform `var.agents` / `var.slack_agents`; drift is easy and silent.
- Fix approach: Implement FLT-01 in Phase 6 — one `agents/fleet.yaml` that generates `agents.txt`, `wake.json`, and Terraform vars; add a check that fails when they diverge.

**Egress is observe-only; no proxy or allowlist enforcement:**
- Issue: `infra/agents/network.tf` provides open outbound via Cloud NAT (`ALL_SUBNETWORKS_ALL_IP_RANGES`, log `ERRORS_ONLY`). There is no Squid/forward proxy, no `agents/policy/egress-allowlist.txt`, and no per-user firewall redirect. EGR-01/EGR-02/EGR-03 are all pending.
- Files: `infra/agents/network.tf`, `agents/host/files/egress.nft`, `tests/agents/host-checks.sh`
- Impact: Any agent user or container can reach any internet destination today; exfiltration and prompt-injection egress are uncontained until Phase 7.
- Fix approach: Phase 1 ships observe-mode logging per agent (EGR-01); Phase 7 enforces the allowlist (EGR-02) without breaking Ada/Boole work; operations containers get per-loop allowlists from first run (EGR-03).

**OpenCode ships from a personal fork, not upstream:**
- Issue: `agents/host/provision.sh` downloads OpenCode from `https://github.com/anomalyco/opencode/releases` with a pinned version + SHA256. That is a single-maintainer mirror, not the upstream release channel.
- Files: `agents/host/provision.sh`, `agents/host/files/opencode.json`, `runbooks/agents/opencode.md`
- Impact: Supply-chain risk (fork takeover, stale patches, delayed security fixes); free Zen models change often so the pin rots.
- Fix approach: Switch to upstream releases when available with checksum verification retained; add a monthly check of `OPENCODE_VERSION` against the Zen model list; record the fork rationale or remove it.

**Interim Codd data-use exception is load-bearing:**
- Issue: Codd runs `opencode/muse-spark-1.3-contributor-free` on OpenCode Zen free tier, whose terms allow Meta to train on prompts/completions. This is accepted for `hyprn-platform` only and must be retired or rebound to the gateway in Phase 3.
- Files: `runbooks/agents/opencode.md`, `agents/host/files/opencode.json`, `agents/host/agents.txt`, `.planning/STATE.md`
- Impact: Any file a Codd session reads can reach Meta; accidental use on product repos or secrets expands exposure.
- Fix approach: Keep the `hyprn-platform`-only App installation and Linux-user boundary; retire per `runbooks/agents/opencode.md` Retire section once the gateway exists; never add Slack/Workspace identities to Codd.

**Staging/prod are spec-only; no Terraform roots, no pipeline:**
- Issue: `docs/specs/cloud-platform.md` sections 3–9 specify `hyprn-staging`/`hyprn-prod` projects, per-environment Terraform roots, contracts in `contracts/v1/`, and the delivery pipeline. `environments/staging/` and `environments/prod/` exist but the hosted build-out is deferred (PLAT-01/PLAT-02) with no implementation.
- Files: `docs/specs/cloud-platform.md`, `environments/staging/`, `environments/prod/`, `contracts/v1/`, `host/README.md`
- Impact: No place to apply platform changes for product hosting; ACC-04 must be re-run when staging/prod appear.
- Fix approach: Trigger PLAT-01 only on the product's local edition; until then do not invent staging/prod projects or state buckets.

## Known Bugs

**Org Policy API concurrent-write failure (`CONCURRENT_POLICY_CHANGES`):**
- Symptoms: First `bootstrap/` apply partially failed on two organization policies; remaining 16 resources needed a re-plan and second apply.
- Files: `bootstrap/org_policies.tf`, `bootstrap/README.md`, `runbooks/agents/gcp.md`
- Trigger: Default Terraform parallelism issuing concurrent writes against one organization.
- Workaround: Always run `bootstrap/` with `-parallelism=1` for plan and apply, as documented in `bootstrap/README.md`. Second occurrence would look identical — retry serially, never raise parallelism.

**Claude Code replaces the channel server seconds after start, losing first-instance work:**
- Symptoms: Wake test 1 — host booted and session started but the waking message was never answered and left no trace.
- Files: `agents/marketplace/`, `runbooks/agents/slack.md`
- Trigger: Any host (re)start where work happens in the first Slack server instance.
- Workaround: Plugin 0.1.1 repeats catch-up at 5, 30, and 90 s (delivered messages skipped) and logs to `~/.local/state/hyprn-slack/server.log` (timestamps only). Do not do real work in the first seconds after start.

**GitHub token broker race — token minted just before secret reload is lost:**
- Symptoms: First broker run lost the token; Ada's `gh` calls failed until the loader change.
- Files: `agents/host/files/hyprn-agent-github-token`, `agents/host/files/hyprn-agent-secrets`, `runbooks/agents/github.md`
- Trigger: Broker mints a one-hour installation token, then the secrets loader overwrites/reloads and drops it.
- Workaround: Loader now mints on every start (`runbooks/agents/github.md` record 2026-10-13). Do not revert to mint-once; the 35-minute freshness check in `tests/agents/host-checks.sh` catches regressions.

**Secret-value load mistakes (wrong value in the right secret):**
- Symptoms: App-token v1 held the bot token by mistake; allowlist v1–v2 held a Slack App ID (`A…`) instead of a member ID (`U…`/`W…`).
- Files: `runbooks/agents/slack.md`, `infra/agents/secrets.tf`
- Trigger: Manual `pbpaste | gcloud secrets versions add … --data-file=-` loads (required because the desktop terminal pane does not pass Ctrl-D).
- Workaround: Check values by shape only (`xapp-…`, `xoxb-…`, `[UW][A-Z0-9]{6,}$`), disable bad versions rather than deleting history (`runbooks/agents/slack.md` cleanup records). Never type secrets into stdin or print them.

**Quota-project requirement for user-credential API calls:**
- Symptoms: Without a quota project, Cloud Identity group lookups report "no such group"; several APIs (Cloud Identity, Org Policy, Budgets) fail the same way.
- Files: `bootstrap/README.md`, `.planning/STATE.md`, `runbooks/agents/gcp.md`
- Trigger: Running `gcloud`/Terraform with user credentials and no billing/quota project set.
- Workaround: Terraform sets `billing_project` to `hyprn-bootstrap`; `gcloud` takes `--billing-project=hyprn-bootstrap`. Bake this into every runbook command; do not "fix" by granting broader roles.

**Shell identity defaults point at the wrong account:**
- Symptoms: Workstation tools default to non-hyprn identities; plain `gcloud projects delete` without the hyprn config fails with "no active account" (which is the safeguard working).
- Files: `.planning/STATE.md`, `runbooks/agents/opencode.md`
- Trigger: Running `gcloud`, Terraform, or `gh` without `CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`, or `GH_CONFIG_DIR` set to the hyprn configurations; non-interactive shells lack aliases.
- Workaround: Always export the hyprn configs explicitly; this repo's `.git/config` resets credential helpers to the hyprn `gh` login only.

## Security Considerations

**GitHub Free — no ruleset on private repos; Ada's App has org-wide write:**
- Risk: Until the Team plan (GHE-01/GHE-03, Phase 1 owner purchase), deny rules (POL-04) are the only control. Ada's App `ada-agent-hyprn` is installed on **all** `hyprn-labs` repositories with Contents + Pull requests read/write, so a compromised session can push anywhere.
- Files: `runbooks/agents/github.md`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, `docs/specs/agent-fleet.md`
- Current mitigation: Agent policy + OpenCode `opencode.json` refusal of pushes to `main` / force push / `gh pr merge`; interim machine account removed (GH-03 complete).
- Recommendations: Buy the Team plan before any agent beyond Ada writes (spec §13 gate); land GHE-01 + GHE-03 + POL-04 together; verify with the Phase 1 negative test (GitHub refuses App merge/push to `main`).

**`strictKnownMarketplaces` not evidenced (POL-03):**
- Risk: Without enforcement, an agent session could install an unreviewed Claude Code marketplace/plugin and gain a privileged path around `managed-settings.json`.
- Files: `runbooks/agents/slack.md`, `agents/marketplace/`, `.planning/STATE.md`
- Current mitigation: Admin-console settings recorded in `runbooks/agents/slack.md` section 3 list `allowedChannelPlugins` but do not show `strictKnownMarketplaces`.
- Recommendations: Set and evidence `strictKnownMarketplaces` → `hyprn-agents` only in Phase 1; add a host check asserting the effective org policy.

**Break-glass, 2FA, and detection alerts all missing (SEC-01, SEC-02, DET-01, DET-02):**
- Risk: No offline break-glass admin, no enforced 2FA on `hyprn-labs`, no Secret Manager Data Access audit logs + alert, no IAM-change alert. Secret reads by unexpected principals and privilege grants are currently silent.
- Files: `runbooks/agents/gcp.md`, `.planning/REQUIREMENTS.md`, `infra/agents/secrets.tf`, `infra/agents/iam.tf`
- Current mitigation: None — all four are Phase 1 requirements with owner-action gates.
- Recommendations: Land in Phase 1 order: SEC-01 (hardware-key break-glass, no standing GCP role) → SEC-02 (enforce 2FA) → DET-01/DET-02 (alerts to `gcp-admins@hyprn.ai`; confirm the group accepts Google Cloud mail).

**Secret IAM is coarser than the "one agent, one secret" story:**
- Risk: `infra/agents/secrets.tf` grants **both** `host` and `wake` `secretAccessor` on **every** agent Slack secret (`agent_slack` IAM over `keys(local.agent_slack_secrets)` × `["host","wake"]`). A wake-VM compromise reads all agents' Slack app + bot tokens; the host root loader likewise holds all agents' tokens at once.
- Files: `infra/agents/secrets.tf`, `agents/wake/wake.py`, `agents/host/files/hyprn-agent-secrets`
- Current mitigation: Per-agent file ownership (`400`, agent-owned) under `/run/hyprn-agents/secrets/` verified by `tests/agents/host-checks.sh`; GitHub App keys are host-only.
- Recommendations: Scope wake access to only the secrets the wake service needs per agent, or document why shared wake access is accepted; add a DET-01 alert consumer for cross-agent reads; re-audit in Phase 4 (ACC-07 Ada/Boole isolation proof).

**Codd training-data exposure (accepted, bounded, must not widen):**
- Risk: Free-tier Zen terms let Meta train on prompts/completions; everything Codd reads (code, runbook notes, pasted output) can leave the org.
- Files: `runbooks/agents/opencode.md`, `agents/host/files/opencode.json`
- Current mitigation: Owner acceptance scoped to `hyprn-platform` only (2026-10-13); Codd App installed on `hyprn-platform` only; no Slack/Workspace identity; host check `Codd's GitHub App limited to hyprn-platform` in `tests/agents/host-checks.sh`.
- Recommendations: Never point Codd at `hyprn-mvp`, staging/prod, or secret values; check values by shape only; retire or rebind per the runbook Retire section in Phase 3.

**Network posture is allow-open with a single-VM blast radius:**
- Risk: Cloud NAT allows all outbound; VPC has no deny-all egress rule; host boot disk has `auto_delete = true`; wake VM has no `deletion_protection`; service-account scopes are `cloud-platform` (IAM, not scopes, carries auth — but a host-root compromise still holds the VM identity with log/metric/secret-access grants).
- Files: `infra/agents/network.tf`, `infra/agents/host.tf`, `infra/agents/wake.tf`, `infra/agents/iam.tf`, `docs/specs/cloud-platform.md`
- Current mitigation: No public IPs (folder `agents_no_external_ip` deny in `bootstrap/agents.tf`); IAP-only SSH in `infra/agents/network.tf`; OS Login + blocked project keys + Shielded VMs in `infra/agents/host.tf` / `infra/agents/wake.tf`.
- Recommendations: Phase 1 adds the VPC deny-all + proxy outer bound (spec §5.2 pattern); set `auto_delete = false` or document why boot-disk ephemerality is accepted; add `deletion_protection` to the wake VM; keep ACC-05 (host holds no user credentials/key files/staging/prod roles) as a blocking check.

**AGPL licensing gate before any commercial cloud launch (Q13):**
- Risk: `modeling` is a patched WhatsOpt copy (GNU AGPL v3); source notices must ship with every release and network separation is explicitly not a licensing conclusion.
- Files: `docs/specs/cloud-platform.md`, `docs/legal/` (referenced, product repo)
- Current mitigation: Internal staging may proceed; legal review gates commercial launch.
- Recommendations: Do not open prod admission without the Q13 legal review; track the permissive-replacement-backend scoping behind the Modeling Backend Contract.

## Performance Bottlenecks

**On-demand host cold start (~50 s Slack-to-answer):**
- Problem: Wake test 2 measured start-requested 20:55:07 → message delivered 20:55:57. Every first message after idle pays boot + session + catch-up latency.
- Files: `agents/wake/wake.py`, `infra/agents/host.tf`, `runbooks/agents/slack.md`
- Cause: `t2d-standard-8` boot, rootless Docker + session start, Slack Socket Mode reconnect; wake polls Compute status every `POLL_SECONDS = 15` in `agents/wake/wake.py`.
- Improvement path: Keep on-demand (cost) but shorten the tail — prestart on schedule before known work windows, lower poll interval cautiously (API quota), and keep the 5/30/90 s catch-up so no wake is wasted. Revisit host sizing from telemetry (spec §4) before upsizing.

**Wake-VM per-agent Socket Mode fan-out:**
- Problem: `agents/wake/wake.py` holds one `WebSocketApp` per agent plus a 15 s status-poll loop and per-start `hold_until` backoff; each additional Slack agent adds a persistent connection on an `e2-micro`.
- Files: `agents/wake/wake.py`, `agents/wake/wake.json`, `infra/agents/wake.tf`
- Cause: Controller-held Socket Mode design (spec §5) not built yet; wake is the interim multiplexer.
- Improvement path: Phase 3 controller takes over operations-agent Socket Mode; wake keeps engineering agents only; monitor `e2-micro` CPU/memory before agent 3–4.

**Polling-first triggers (Notion every 5 min):**
- Problem: Meeting-loop trigger polls the Notion meetings database every 5 minutes; worst-case intake latency is 5 min + queue + host boot (~1 min) + run time.
- Files: `docs/specs/agent-fleet.md`, `docs/adr/0006-agent-first-operating-model.md`
- Cause: Webhook receiver deliberately deferred (WEB-01) until polling proves insufficient.
- Improvement path: Accept polling for M2 (LOOP-01 success = run queued within 5 min); promote to WEB-01 under its own ADR only with measured evidence.

**Rootless Docker + single-host build/test load:**
- Problem: All engineering sessions and (future) operations containers share one `t2d-standard-8` with rootless Docker; package/Docker caches persist per agent (EFF-02, not yet implemented) so cold worktrees pay full toolchain + image-pull cost.
- Files: `infra/agents/variables.tf`, `agents/host/provision.sh`, `.planning/REQUIREMENTS.md`
- Cause: M1 has not landed EFF-01 (preinstalled pinned toolchains) or EFF-02 (persistent caches).
- Improvement path: Phase 2 lands EFF-01/EFF-02 and measures; resize/add hosts only from telemetry per spec §4.

## Fragile Areas

**Org-policy apply — must stay serial:**
- Files: `bootstrap/org_policies.tf`, `bootstrap/README.md`, `bootstrap/agents.tf`
- Why fragile: The Org Policy API rejects concurrent writes on one org with `CONCURRENT_POLICY_CHANGES`; `bootstrap/agents.tf` also orders project creation behind policy + folder resources via `depends_on`.
- Safe modification: Always `plan`/`apply` with `-parallelism=1`; keep `depends_on` chains; review destroy/replace on stateful resources (buckets with `prevent_destroy`, folder with `deletion_protection`).
- Test coverage: None automated — no policy-concurrency test in `tests/agents/`; Phase 1 `tests/agents/run.sh` (ACC-08) should pin the `-parallelism=1` invocation.

**Quota-project + group-lookup coupling:**
- Files: `bootstrap/README.md`, `runbooks/agents/gcp.md`, `.planning/STATE.md`
- Why fragile: Cloud Identity group reads need `--billing-project=hyprn-bootstrap`; a missing flag looks like "no such group" and invites wrong fixes (recreating groups, widening roles).
- Safe modification: Keep the quota-project flags in every documented command; verify group existence in the admin console before changing Terraform.
- Test coverage: None; consider a read-only check that resolves `gcp-admins@hyprn.ai` with the quota project set.

**Metadata-server/DNS conflation (`169.254.169.254:53`):**
- Files: `agents/host/files/egress.nft`, `tests/agents/host-checks.sh`, `.planning/STATE.md`
- Why fragile: On Google Cloud the metadata address is also the DNS resolver — a naive metadata block breaks all DNS. The nftables table `inet hyprn_agents` must deny metadata while keeping port 53 open.
- Safe modification: Change `agents/host/files/egress.nft` only with the paired `tests/agents/host-checks.sh` assertions (`metadata unreachable` + `DNS resolves` + `outbound HTTPS`) passing for every agent; verify after Docker restart and reboot (spec §5.2 pattern).
- Test coverage: Covered per-agent in `tests/agents/host-checks.sh` — keep all three checks together; never assert metadata-block alone.

**Slack/GitHub vendor manual steps (no API path):**
- Files: `runbooks/agents/slack.md`, `runbooks/agents/github.md`, `docs/specs/agent-fleet.md`, `.planning/STATE.md`
- Why fragile: Slack config token / install approval / Socket Mode token, GitHub App creation / installation / logo, Claude seat invite + first sign-in, Notion integration + page shares all need a human. Automation that assumes APIs exist will fail at these steps.
- Safe modification: Keep the vendor table in `docs/specs/agent-fleet.md` section 12 as the authority; `agents/fleet add` (FLT-06) must stop and print manual steps rather than work around them; Phase 6 spikes (FLT-02/FLT-03/FLT-05) timebox each unknown.
- Test coverage: None automated; FLT-06 acceptance (test agent of each kind in 15 min / ~8 human actions) is the executable proof.

**Claude session lifecycle (sign-in gate + server replacement):**
- Files: `agents/host/provision.sh`, `agents/host/files/hyprn-agent@.service`, `agents/marketplace/`
- Why fragile: `add_agent` only enables the systemd session when `~/.claude/.credentials.json` is non-empty; a replaced channel server drops first-instance work; herdr migration (COK-02) will change the runtime under running sessions.
- Safe modification: Re-provision via `agents/host/apply.sh` after credential changes; restart (not duplicate) `hyprn-agent@<name>.service`; keep tmux as fallback until herdr proves resume-after-boot (COK-02 success criterion).
- Test coverage: Partial — `tests/agents/host-checks.sh` asserts plugin install and Slack tokens but not session liveness or herdr resume.

**Secret-reload vs token-broker ordering:**
- Files: `agents/host/files/hyprn-agent-secrets`, `agents/host/files/hyprn-agent-github-token`, `agents/host/files/hyprn-agent-github-token@.service`, `agents/host/files/hyprn-agent-github-token@.timer`
- Why fragile: Hourly broker refresh (`-mmin -35` freshness check) races secret reloads; the previous loss bug was fixed by mint-on-every-start, which must survive future refactors.
- Safe modification: Keep mint-on-start; never cache a token across a reload without re-minting; keep the `GitHub App token fresh` + `gh works with the App token` checks adjacent in `tests/agents/host-checks.sh`.
- Test coverage: Covered for freshness and validity; not covered for the reload race itself — add a reload-then-use sequence to the Phase 1 check suite.

**Worktree isolation incomplete (product-side gap):**
- Files: `.planning/STATE.md`, `docs/specs/agent-fleet.md`, `runbooks/agents/opencode.md`
- Why fragile: One worktree per task needs its own port block, Compose project, and test database (GH-02); isolation is complete only once the product reads those overrides from the environment — product work outside this repo.
- Safe modification: Do not claim GH-02 complete from the platform side alone; verify two worktrees side by side with the product's tests (Phase 2 success criterion 2–3).
- Test coverage: None yet; GH-02 needs an executable two-worktree test in the Phase 2 check additions.

## Scaling Limits

**Slack Free 10-app ceiling → fleet tops out around eight agents:**
- Current capacity: 1 Slack agent (Ada); Codd has no Slack app.
- Limit: 10 apps workspace-wide (FLEET-05); spec budgets ~8 agents max.
- Scaling path: FLEET-05 triggers the paid Slack plan when the fleet nears 10 apps; until then every new operations agent consumes one of very few slots — prioritize Boole over experimental agents.

**Single agent host, single zone, zonal disk-less boot:**
- Current capacity: `hyprn-agents-host-01` `t2d-standard-8`, 100 GiB `pd-balanced` boot disk (`infra/agents/variables.tf`, `infra/agents/host.tf`); `e2-micro` wake.
- Limit: One VM is one failure domain; zone outage stops all engineering and runs; boot disk `auto_delete = true` loses the boot image on instance delete (data lives in homes/volumes, but rebuild time applies).
- Scaling path: Spec §4 — resize/add hosts from telemetry; keep host stateless-safe (caches in EFF-02 must be rebuildable); never treat the agent host as durable state — run state belongs in the gateway's Cloud SQL (CP-02).

**Budget is alert-only (100 EUR, no hard cap):**
- Current capacity: `google_billing_budget` on `hyprn-agents` at 50/80/100% in `bootstrap/agents.tf`; COST-01 revised budget pending Phase 3.
- Limit: Google budgets do not cap spend — overrun continues until a human acts; per-loop gateway budgets and the kill switch do not exist yet (CP-04).
- Scaling path: Phase 3 lands CP-04 (gateway-enforced per-loop budgets + per-loop/per-agent/fleet kill switch < 1 min) and COST-01 revised budget covering gateway, Cloud SQL, Workspace licences, and wake-ups.

**GitHub org is Free with a single human member:**
- Current capacity: Org `hyprn-labs` (Free), sole member the owner; two repos (`hyprn-platform`, `hyprn-mvp`).
- Limit: No rulesets/environments on private repos; no required reviewers/CODEOWNERS enforcement; every agent App permission is correspondingly more powerful.
- Scaling path: Team plan purchase (Phase 1 owner action) unlocks GHE-01/GHE-03; add CODEOWNERS for infra/IAM/host-adapter/workflows/prod desired state per spec §8.2.

## Dependencies at Risk

**`anomalyco/opencode` fork + Zen free-tier model volatility:**
- Risk: Pinned `OPENCODE_VERSION="1.19.0"` + SHA in `agents/host/provision.sh` tracks a personal fork; free Zen models (Muse Spark 1.3 Contributor Free) change often with their own data terms.
- Impact: Stale binary, checksum mismatch on rebuild, or model withdrawal breaks Codd and the `opencode` host checks.
- Migration plan: Recheck the Zen model list + data terms before every version bump (`runbooks/agents/opencode.md`); prefer upstream releases with retained SHA verification; retire OpenCode-for-Ada path already done — do not re-add.

**Claude Team plan — no member/seat API:**
- Risk: Engineering-agent onboarding always needs human invite + first sign-in; agent seats cannot be driven programmatically until Anthropic answers (FLEET-01 deferred, agent-to-agent prompting stays off).
- Impact: FLT-06 engineering test stops before seat invitation; herdr session-takeover scope is bounded.
- Migration plan: Keep the two manual seat actions in `agents/fleet add`; track FLEET-01 trigger (Anthropic's answer on agent seats); do not build seat-automation workarounds.

**Slack platform — Socket Mode + app-install human gates:**
- Risk: Config token creation, install approval, and Socket Mode token creation are manual forever (spec §12 table, checked 2026-10-13); FLT-03 icon via `apps.icon.set` and FLT-05 `setup-token` sign-in are unproven spikes.
- Impact: `fleet add` cannot be zero-touch; Phase 6 spikes may fail and leave interactive sign-in in place.
- Migration plan: Timebox FLT-03/FLT-05 spikes in Phase 6; on failure record the finding and keep the manual step documented in `runbooks/agents/onboarding.md` (FLT-08).

**GitHub Apps — manifest flow still needs human confirm + install:**
- Risk: App creation confirm, installation on selected repos, and logo upload need the owner; installation-token ceiling (App permissions ∩ installed repos) silently limits tokens minted too broadly.
- Impact: FLT-04 partially manual; Boole's App (OPS-03) gated on the Phase 1 ruleset.
- Migration plan: Keep `runbooks/agents/github.md` as the manual companion to `fleet add`; verify installation scope with the `installation/repositories` checks in `tests/agents/host-checks.sh` after every App change.

**Not-yet-procured providers (Fireworks, Anthropic API, OpenAI, Notion, Workspace):**
- Risk: No Fireworks account/key, no linked Anthropic Console org/key, no OpenAI key, no Boole Slack app, no Notion integration, no `boole@agents.hyprn.ai` user — all Phase 3–4 owner actions in `.planning/STATE.md` Pending Todos.
- Impact: CP-01/RT-01/LOOP-01 cannot be exercised; meeting-loop trigger (Granola → Notion path, LOOP-01) is undecided with the fallback (polling) as the only plan.
- Migration plan: Procure in Phase 3 planning order (gateway needs provider keys first); settle LOOP-01 before Phase 4; keep finance/e-signature (TOOL-01) and webhook receiver (WEB-01) deferred until a loop actually needs them.

**Pinned Debian image ages (`debian-12-bookworm-v20261006`):**
- Risk: `infra/agents/variables.tf` pins the full image (correct — never family lookup) but the pin dates to 2026-10-06 and will accumulate CVEs.
- Impact: Host and wake rebuilds carry a stale base; unattended-upgrades (`agents/host/provision.sh`) cover packages, not the base image.
- Migration plan: Quarterly reviewed image bump via Terraform change + `apply.sh` reprovision + full `host-checks.sh` pass; never auto-follow image families.

## Missing Critical Features

**Phase 1 security baseline — everything except DOC-01:**
- Problem: 18 of 19 Phase 1 requirements pending (GHE-01/03, POL-01–04, EGR-01, DET-01/02, SEC-01/02, ACC-01–06/08). The safety proof (`tests/agents/run.sh`, ACC-08) does not exist — only `tests/agents/host-checks.sh` runs, and only by hand on the host.
- Blocks: M1 completion; Boole's App (gated on ruleset); any claim that Ada is "safe".
- Files: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `tests/agents/README.md`, `tests/agents/host-checks.sh`

**Engineering workflow (Phase 2) — Slack-to-PR, worktrees, herdr, telemetry absent:**
- Problem: GH-01 (Slack task → draft PR), GH-02 (worktree helper), EFF-01/02 (toolchains/caches), COK-01/02 (herdr cockpit + runtime), OBS-01 (daily cost report) all pending.
- Blocks: M1 "efficient" half; owner visibility into seat cost/usage.
- Files: `agents/host/`, `agents/measurement/`, `.planning/REQUIREMENTS.md`

**Control plane + Boole + learning (Phases 3–5) — entirely absent:**
- Problem: Gateway (CP-01), controller/queue/run-state (CP-02), approvals-as-tool-call (CP-03), budgets/kill-switch (CP-04), loop registry (CP-05), broker (CP-06), runner (RT-01), enforced run containers (EGR-03), Boole identities (OPS-01–03), meeting loop (LOOP-01–03), evals/feedback/promotion (LRN-01–04) all pending.
- Blocks: M2 value (autonomous operations work with metered cost and learning).
- Files: `agents/loops/` (missing), `agents/fleet.yaml` (missing), `docs/specs/agent-fleet.md`

**Fleet-as-code onboarding (Phase 6) — no `fleet.yaml`, `fleet add/remove`, or onboarding runbook:**
- Problem: FLT-01–08 pending; `agents/host/agents.txt` + `agents/wake/wake.json` remain the dual source of truth; Workspace-user automation (FLT-02) and App-from-manifest flows (FLT-03/04) unproven.
- Blocks: M3 "one command to add an agent".
- Files: `agents/host/agents.txt`, `agents/wake/wake.json`, `infra/agents/variables.tf`, `runbooks/agents/onboarding.md` (missing)

**Enforced egress + final acceptance (Phase 7):**
- Problem: EGR-02 allowlist enforcement and ACC-10 full pass pending; no dated acceptance record exists.
- Blocks: Any "fleet is hardened" claim.
- Files: `agents/policy/` (egress allowlist missing), `tests/agents/`

## Test Coverage Gaps

**No runnable `tests/agents/run.sh` (ACC-08) — the one-command proof is missing:**
- What's not tested: The orchestrator that runs every check delivered so far and writes a dated record to `runbooks/agents/` after each phase.
- Files: `tests/agents/host-checks.sh`, `tests/agents/README.md`, `tests/README.md`, `.planning/REQUIREMENTS.md`
- Risk: Each phase's "proof" is a hand-run transcript in runbook Record tables, not a repeatable artifact; regressions between phases go unnoticed.
- Priority: High — build in Phase 1; every later phase extends it.

**Isolation/negative checks beyond host hygiene:**
- What's not tested: ACC-01 (permission relay `yes`/`no` + non-owner rejection), ACC-02 (non-allowlisted senders ignored end-to-end incl. wake path in `agents/wake/wake.py`), ACC-03 (merge/push-to-`main`/force-push/bypass refused in-session), ACC-04 (org-wide IAM search showing exact roles), ACC-05 (host holds no user credentials/key files/staging/prod roles), ACC-06 (wake identity refused everything but get/start/stop; no Slack connection while host runs; disk survives idle stop), ACC-07 (Ada↔Boole cross-read refusal), ACC-09 (controller/gateway roles + internal-only ingress + per-run credentials).
- Files: `tests/agents/host-checks.sh`, `infra/agents/iam.tf`, `infra/agents/wake.tf`, `infra/agents/secrets.tf`
- Risk: The current 40 checks prove hygiene (private homes, no sudo/docker groups, metadata unreachable, secret file modes, token freshness) but not authorization boundaries — the exact properties Phase 1 must prove.
- Priority: High — ACC-01–06 + ACC-08 are Phase 1 success criteria.

**Egress enforcement tests:**
- What's not tested: Per-agent destination logging (EGR-01 observe mode), domain-allowlist refuse + log (EGR-02/EGR-03), DNS-stays-open while metadata-blocked, effective-rules-after-Docker-restart-and-reboot (spec §5.2 pattern).
- Files: `agents/host/files/egress.nft`, `infra/agents/network.tf`, `tests/agents/host-checks.sh`
- Risk: The nft table assertion (`metadata block loaded`) proves the table exists, not that enforcement holds under container-network and reboot conditions.
- Priority: High for EGR-01 in Phase 1; Medium for EGR-02/03 until Phase 3/7.

**Terraform/CI coverage (plan-on-PR, policy-as-code, drift):**
- What's not tested: Credential-free `fmt`/`validate`/static-policy on PR, credentialed binary-plan restricted-retention flow, apply-exactly-that-plan, scheduled drift report (spec §8.3 pattern) — none wired for `bootstrap/` or `infra/agents/`.
- Files: `bootstrap/`, `infra/agents/`, `.github/` (workflows — verify presence before planning Phase 1)
- Risk: Destructive diffs (bucket/folder `prevent_destroy` bypass via block deletion per spec §5.4 warning) caught only by human plan review.
- Priority: Medium — land with Phase 1 Terraform changes; at minimum pin provider versions + commit lockfile per spec §8.3.

**Secret-rotation and reboot-reload paths:**
- What's not tested: Rotation (new version → binding change → reconciliation → old version disabled), reboot secret reload, disabled-secret-blocks-start, no-secret-values-in-logs/rendered-config (spec §12 verification list adapted to the agent fleet).
- Files: `agents/host/files/hyprn-agent-secrets`, `agents/host/files/hyprn-agent-github-token@.service`, `infra/agents/secrets.tf`
- Risk: Rotation is the most likely operator procedure to fail under pressure; untested reboot reload risks a host that never rejoins Slack after idle stop.
- Priority: Medium — cover in Phase 1 alongside DET-01; re-exercise in Phase 7 acceptance.

---

*Concerns audit: 2026-10-13*
