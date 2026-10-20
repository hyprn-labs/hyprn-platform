# Platform 08-01 checkpoint — 2026-10-20

Task complete: offline contract/preview only. No hosted environment exists as a
result of this task.

Branch: `codex/platform-contract`.
Code commit: `408ed98b61ffe57de565e0a79a5493a66ddff05c`.
Starting commit: `8ffbdf92c28eb607f753fed4e603a10cc44865e6`.
Test commit: `3b28d6e`.

| Artifact | SHA-256 |
|---|---|
| `contracts/v1/deployment.schema.json` | `bf0220439ae678edf09fef248d790fd9d479449599fadf047d4c80ea24af7c8c` |
| `host/contract.py` | `a49b0ed119ed721bcad6fcf5da1cf3822999613ac571008635e2064a91bfca6a` |
| Golden rendered configuration | `e9daeb2f5ded8f163cfd2d0ca4f56cb6acbea1cf1d454e484854a1dc2b949907` |

## Commands and results

- RED target: `python3 -B -m unittest discover -s tests/platform -p test_contract.py -k test_valid_preview_is_deterministic_and_separates_secret_authority -v`
  — exit 1; 1 executed, 1 expected failure on missing implementation.
- `node "$GSD_TOOLS" check tdd-red-evidence .planning/phases/08-product-staging/08-01-RED.json --raw`
  — exit 0; `RED_EVIDENCE_OK`.
- Initial GREEN: `tests/platform/run.sh contracts` — 9 passed.
- After TLS and negative coverage additions: same command — 11 passed.
- After schema/renderer pins and runner finalization: same command — 11 passed.
- Required committed-tree check: same command at `2c3c947` — 11 passed,
  0 failed, 1.766 seconds.
- After product integration required separate authentication credentials: same
  command — 11 passed; committed-tree check at `408ed98` — 11 passed,
  0 failed, 1.860 seconds.
- `git show --first-parent --diff-filter=D --name-only --pretty=format: HEAD`
  — no deletions.
- `git check-ignore local.tfvars local.tfvars.json plan.json identity.key application_default_credentials.json app.sqlite .env .env.example`
  — all private examples ignored; `.env.example` is not ignored.

No unexpected test failures occurred. Repeated focused runs correspond to changed
TLS/schema/security code, final runner changes, and the required committed-tree
handoff. No broad qualification suite was run for this isolated stdlib addition.
The metadata commit initially failed the repository term hook because the raw RED
report contained a developer home path. That unchanged local report is now ignored;
portable checkpoint commands use the resolved `GSD_TOOLS` variable. No hook was bypassed.

## Product handoff

Use `contracts/v1/fixtures.json` for complete synthetic input shapes.

```sh
python3 -B host/contract.py preview \
  --workload workload.json --release release.json --runtime runtime.json
python3 -B host/contract.py validate \
  --workload workload.json --release release.json --runtime runtime.json \
  --desired desired.json --bundle native.tar.gz
```

Success returns release/configuration digests and verification flags; invalid
input exits 2 with an error code and safe field location. Cloud adapter consumes
runtime secret file paths and explicit DB host, TLS identity and CA pin.
Authentication lookup uses `hyprn_auth` and `db-app-auth`; scoped study access
uses `hyprn_request` and `db-app-request`. Migration/backup roles are not
mounted into the application. Product
schema migrations retain per-owner compatibility metadata even with fresh data.

Review `contracts/v1/README.md` for ownership and all validation limits. The
host/lifecycle implementation is the next dependency; this command never executes
an image or product code and is not authorization to deploy.

## Preservation and cleanup

Tests use isolated `TemporaryDirectory` scopes and remove them.
Implementation staging files remain in `/private/tmp/hyprn-platform-contract`
for this handoff, outside the repository; they contain no credentials or data.
Existing dirty STATE, ROADMAP, REQUIREMENTS, ADR index and cloud specification
were not staged, reverted or reformatted. No runtime installation was touched.

Parent owns integrating scoped 08-01 state because the global pointer still
tracks the independent engineering fleet. GitHub/cloud changes remain blocked
on exact operational approval and effective branch protections, not on this CLI.
