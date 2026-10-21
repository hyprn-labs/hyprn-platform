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
