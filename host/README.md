# host

The host adapter for product environments: renderer, reconciler, secret loader, systemd units and firewall templates. It reads one validated environment intent, verifies artifacts, runs the fixed product lifecycle operations and reports the outcome ([specification](../docs/specs/cloud-platform.md) section 9).


`setup.py plan --policy <file> --packages <directory>` produces a deterministic
fresh-host plan. `setup.py apply` additionally requires its exact
`--approve-sha256` and Linux root authority. It prepares the bound blank staging
disk, pinned runtime packages, owner directories and closed Docker firewall.
Repeated completed setup verifies the same state; interrupted setup requires
operator reconciliation. [Package provenance](provenance.md) records the pins.

The preparation receipt leaves admission closed. Product artifacts, credentials,
database roles, actual service routes, execution attestation and the connector
are applied and qualified through the deployment lifecycle, not this command.


`repair_setup.py` reconciles the reviewed interrupted package stage against the
original intent, exact mounted filesystem, generated files and package states.
It installs only the three explicitly pinned missing OS dependencies and configures
the existing engine; it has no format action. Its source bundle includes the
original `base-plan.json`, and a distinct repair plan hash is required. Uncertain
or interrupted repairs are refused until reconciled. The same IAP controller
validates either a fresh-setup or repair bundle and stops the VM afterwards.
