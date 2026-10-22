# Activation performance correction

Status: implemented and locally verified; not deployed or measured on staging.

Renewal previously repeated the product delivery verifier, hashing all inactive OCI
archives every 30 seconds after checking their running image identities. Remove
only that duplicate delivery verification. Keep installed native byte verification,
actual image digests, runtime isolation, network, host generation, owner state,
JWT refusal and bounded admission unchanged. No cache or stale attestation is added.

Sanitized observation logs expose phase and duration for the next staging measurement.
They never log policy values, credentials, fetched material or exception details.

Verification:

- `python3 -m unittest discover -s tests/platform -p 'test_activation*.py'`:
  20 passed, 0 failures.
- `python3 -m unittest discover -s tests/platform -p test_install_release.py`:
  12 passed, 0 failures, including installed byte/link/permission drift refusal.
- The first activation-only check passed 11 tests before integrated related checks.

Tests use temporary isolated inputs. No cloud state or live data was changed.
These tests verify control logic, not deployed latency or human acceptance.
Remaining: include this exact code in release plan, deploy, compare renewal phase
latency, and verify browser access and worker refusal behavior on staging.
