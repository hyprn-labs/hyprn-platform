"""Fixed operational journal limits; never collect product or release records."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location('hyprn_retention_setup', Path(__file__).with_name('setup.py'))
setup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(setup)
Refused = setup.reconcile.Refused
PATH = setup.JOURNAL_PATH
LIMITS = setup.JOURNAL_LIMITS


def configuration():
    return setup.JOURNAL_TEXT


def plan():
    source = Path(__file__)
    value = {
        'schema': 'hyprn-operational-retention/v1',
        'sources': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (source, source.with_name('setup.py'),
                                 source.with_name('reconcile.py'), source.with_name('contract.py'),
                                 source.with_name('secrets.py'))},
        'file': str(PATH), 'sha256': hashlib.sha256(configuration().encode()).hexdigest(),
        'limits': LIMITS,
        'actions': ['install-identical-or-new-journal-drop-in', 'restart-journald',
                    'verify-effective-limits'],
        'deletes_product_records': False, 'deletes_release_artifacts': False,
    }
    return dict(value, plan_sha256=setup.digest(setup.canonical(value)))


def verify_effective(raw):
    """Check the ordered effective drop-ins, including later overrides."""
    section, actual = '', {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(('#', ';')):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line
        elif section == '[Journal]' and '=' in line:
            key, value = line.split('=', 1)
            actual[key.strip()] = value.strip()
    if any(actual.get(key) != value for key, value in LIMITS.items()):
        raise Refused('operational_retention_overridden')
    return {'journal_limits': 'verified', 'product_records': 'preserved',
            'release_artifacts': 'preserved'}


def apply(approved):
    expected = plan()
    if approved != expected['plan_sha256']:
        raise Refused('operational_retention_approval_mismatch')
    if sys.platform != 'linux' or setup.os.geteuid() != 0:
        raise Refused('operational_retention_linux_root_required')
    for name in expected['sources']:
        setup.reconcile.protected(Path(__file__).with_name(name))
    # Reject links/ownership drift before restart; an existing other policy is
    # never overwritten. Repeating a completed installation is idempotent.
    setup.mkdir(PATH.parent, 0o755)
    raw = configuration().encode()
    if PATH.exists() or PATH.is_symlink():
        setup.reconcile.protected(PATH)
        if PATH.read_bytes() != raw:
            raise Refused('operational_retention_existing_policy')
    else:
        setup.write_new(PATH, raw, 0o644)
    verify_effective(setup.run([
        '/usr/bin/systemd-analyze', 'cat-config', 'systemd/journald.conf']).decode())
    setup.run(['/usr/bin/systemctl', 'restart', 'systemd-journald.service'], timeout=30)
    setup.run(['/usr/bin/systemctl', 'is-active', '--quiet', 'systemd-journald.service'])
    return dict(verify_effective(setup.run([
        '/usr/bin/systemd-analyze', 'cat-config', 'systemd/journald.conf']).decode()),
        plan_sha256=approved)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('plan', 'apply'))
    parser.add_argument('--approve-sha256')
    args = parser.parse_args()
    try:
        if args.operation == 'plan' and args.approve_sha256:
            raise Refused('operational_retention_plan_is_read_only')
        value = plan() if args.operation == 'plan' else apply(args.approve_sha256)
        print(json.dumps(value, sort_keys=True))
    except Refused as error:
        print(json.dumps({'error': str(error)}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
