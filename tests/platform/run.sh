#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
group="${1:-}"
case "$group" in
  contracts) pattern=test_contract.py ;;
  reconcile) pattern=test_reconcile.py ;;
  delivery) pattern=test_delivery.py ;;
  infrastructure) pattern=test_infrastructure.py ;;
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
