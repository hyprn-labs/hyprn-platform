#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
group="${1:-}"
case "$group" in
  contracts) pattern=test_contract.py ;;
  service-network) pattern=test_service_network.py ;;
  service-network-live) pattern=test_service_network_live.py ;;
  service-network-install) pattern=test_service_network_install.py ;;
  service-network-probe) pattern=test_service_network_probe.py ;;
  database-setup) pattern=test_database_setup.py ;;
  database-operator) pattern=test_database_operator.py ;;
  release-stage) pattern=test_release_stage.py ;;
  activation) pattern=test_activation.py ;;
  activation-install) pattern=test_activation_install.py ;;
  secrets) pattern=test_secrets.py ;;
  backup) pattern=test_cloudsql_backup.py ;;
  reconcile) pattern=test_reconcile.py ;;
  install) pattern=test_install_release.py ;;
  images) pattern=test_images.py ;;
  bootstrap) pattern=test_bootstrap.py ;;
  preflight) pattern=test_preflight.py ;;
  host-setup) pattern=test_host_setup.py ;;
  delivery) pattern=test_delivery.py ;;
  infrastructure) pattern=test_infrastructure.py ;;
  state-bootstrap) pattern=test_state_bootstrap.py ;;
  access-infrastructure) pattern=test_access_infrastructure.py ;;
  *) printf 'Unknown check group: %s\n' "$group" >&2; exit 2 ;;
esac
if [ "$#" -ne 1 ] || [ ! -f "tests/platform/$pattern" ]; then
  printf 'Missing or invalid check group: %s\n' "$group" >&2
  exit 2
fi
if ! git ls-files --error-unmatch "tests/platform/$pattern" >/dev/null 2>&1; then
  printf 'Uncommitted check group: %s\n' "$group" >&2
  exit 2
fi
exec python3 -B -m unittest discover -s tests/platform -p "$pattern" -v
