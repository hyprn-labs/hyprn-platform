# Platform 08-01C checkpoint — 2026-10-20

Complete: offline managed Assistant contract amendment. No provider/cloud mutation,
host lifecycle implementation, boot qualification or human acceptance claimed.

- Branch: `codex/platform-contract`.
- RED: `2d8f042`.
- Initial implementation: `9c5deee09c40d72b0091f268102225934a2069db`.
- Final implementation/tested commit: `1f9a7fae0ef797509614e8bfbf84c9edec265fe0`.
- Schema SHA-256: `bf4b15f92dff78f56af18d2e641cf6c28568c1a63e7f04c6891a49dde970b9d5`.
- Renderer SHA-256: `b81cb7d2cfcb02ddbea67abcddc7bb032e706f5bf586da1a7c50ef25e6090a02`.
- Synthetic configuration SHA-256: `33e5695dffbc1095f49606cd37e80092899fab0752fe728bb60ebe802dcf9c6f`.
- Product interface inspected read-only at managed setup commit `1e0c10a`:
  `deployment/managed_assistant.py`, Assistant `Settings` and `allowance.prepare`.

## Verification

- `tests/platform/run.sh contracts`: RED, exit 1; 16 tests, 15 passed, 1 planned
  failure because `HYPRN_MVP_ASSISTANT_KEY_FILE` was absent from app settings.
- `node "$GSD_TOOLS" check tdd-red-evidence .planning/phases/08-product-staging/08-01C-RED.json --raw`:
  exit 0, RED_EVIDENCE_OK. Ignored raw evidence includes local paths. Semantic
  inspection confirms the target executed and failed at its intended assertion.
- GREEN, same registered command: 19 passed, 0 failed (4.268 s).
- After explicit EUR approval/conversion amendment: same command, 20 passed,
  0 failed (4.688 s).
- Required committed-tree check at `9c5deee`: same command, exit 0; 20 passed,
  0 failed (4.632 s).
- Parent accepted the initial source with 20 passing tests, then requested generic
  runtime approval fields. After that source/test/schema change: same command,
  20 passed (4.983 s), then required final committed-tree check at `1f9a7fa`,
  exit 0, 20 passed, 0 failed (4.722 s).
- `git diff --check`: exit 0. No task commit deleted files. No stub markers.
- Tests use released TemporaryDirectory scopes. No dependency installed, live
  store accessed, credential read, provider request or cloud operation performed.
- Tooling failures: first git ledger write was sandbox-denied, then succeeded
  under reviewed escalation; two README patch context mismatches changed no file
  and were corrected after inspecting exact text. An exploratory nonexistent
  `assistant/spending.py` read was corrected to `assistant/allowance.py`.
  No unexpected verification failure occurred.
- Metadata commit hook rejected a machine-local path in this checkpoint; it was
  replaced by the resolved GSD tool variable before retrying. No hook was bypassed.

## Binding and actual guarantees

`release.assistant` requires definition/configuration SHA-256 pins.
`runtime.assistant` requires matching hashes, provider constant, agent ID,
canonical positive decimal-string agent version, environment ID and closed budget.
The app receives `HYPRN_MVP_ASSISTANT_` settings: `AGENT_ID`, `AGENT_VERSION`,
`ENVIRONMENT_ID`, `DEFINITIONS_SHA256`, `CONFIGURATION_SHA256`, `TOTAL_CENTS`,
`PRIOR_CENTS`, `APPROVED_MINOR`, `APPROVED_CURRENCY`, `CONVERSION_DATE`, and
`KEY_FILE=/run/secrets/assistant-provider`. Numeric Secret Manager version and
existing app-only file mount remain the sole provider credential binding.
Dispatcher/modeling/native execution/workers receive none of these settings.

Budget approval is explicit positive minor units (up to 1,000,000) in EUR or USD,
with USD conversion rate, UTC timestamp and floor-to-provider-cent convention.
USD approval requires unit rate. Exact decimal multiplication
must agree with provider `total_cents`. Prior cents are explicit USD spending
outside retained sessions. Policy requires one installation allowance and retained,
reconciled session history across releases/restarts. No per-study/session cap,
endpoint override, raw key, implicit zero or reset policy is accepted. The fixture
approval of EUR 100, rate 1.10 and timestamp are synthetic; no live exchange rate
or spending authorization was selected. Actual approval remains in the private
deployment review; changes require reviewed runtime updates, not schema edits.

Real CLI tests cover missing fields, invalid resources/hashes, currency changes,
invalid date/rate, arithmetic disagreement, raw-key redaction, secret-version
pins, unknown authority and desired-hash invalidation. Effective-render tests also
reject changed credential paths, extra session settings and removed continuity gates.

## Remaining consumers

The stateless validator cannot verify historical prior spending or provider state.
The host/product startup consumer must satisfy both new `start_requires` entries:
resource readback/release definition match and shared spending continuity. It must
verify conversion provenance/approval, retain provider-session accounting through
replacement/rollback, reconcile uncertain sessions and refuse unknown continuity.
The product's existing allowance preparation reads all retained sessions and adds
prior cents, but that does not establish cloud startup acceptance.

Current product Settings consumes every emitted setting except
`CONFIGURATION_SHA256`; the release/startup consumer must enforce it. Host secret
loading must produce an app-owned regular mode-0600 file, read-only in the app.
Effective egress, file ownership, provider resource readback and cloud boot remain
separate acceptance obligations. No actual provider resources were provisioned.

Parent owns the integrated acceptance rerun and global STATE/ROADMAP/REQUIREMENTS.
All unrelated infrastructure, runbook and planning edits were preserved. Later
task metadata commits change only this checkpoint and summary.
