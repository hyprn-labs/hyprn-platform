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

`finalize_setup.py` completes the verified package repair after disabling
systemd-resolved link-local discovery and aligning the reviewed network-manager
configuration with the IPv4-only host policy. It preserves DHCPv4, DNS, routes and
MTU settings, verifies a second network reconfiguration cannot re-enable IPv6,
and applies strict host verification before recording completion. Unexpected
network configuration, interface drift or additional listeners refuse the repair. The corresponding plan explicitly binds a running final VM state;
other setup plans retain their stopped final state. Fresh setup includes the same
resolver settings.

`service_network.py --policy <file>` previews the platform's fixed service routes,
restricted CONNECT proxy and firewall chains. The preview is read-only and leaves
admission closed. `egress-proxy.json` pins the standalone host executable and its
notices. The host installer must establish the policy's jumps before starting the
proxy or product, preserve the closed Docker guard across restarts, and verify the
positive and negative packet paths. Preview and isolated proxy tests do not prove
those deployment conditions.


The bootstrap resolves platform siblings explicitly under isolated Python. Public
CA material is installed in a protected, readable trust directory before copying
controls. Runtime credentials remain in their separate private tmpfs folders.
An interrupted initialization stays blocked until its operation journal and actual
store state have been reconciled under an explicit recovery plan.
