"""Complete the reviewed host with durable IPv4 policy and no link-local discovery."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup
import preflight

REPAIR_PLAN = '914022b3b649e61a411e4804427c8bb925d1207d4169f2b1a0b005c87d635478'
RESOLVED = setup.RESOLVED
RESOLVED_TEXT = setup.RESOLVED_TEXT


def basis():
    value = setup.reconcile.contract.read_json(setup.ROOT / 'repair-plan.json')
    raw = {k: v for k, v in value.items() if k != 'plan_sha256'}
    if (value.get('plan_sha256') != REPAIR_PLAN
            or setup.digest(setup.canonical(raw)) != REPAIR_PLAN):
        setup.fail('finalize_repair_plan_binding')
    return value


def plan(policy, folder):
    previous = basis()
    value = setup.plan(policy, folder)
    if (previous['policy'] != policy
            or {k: v for k, v in value['files'].items() if k not in (str(RESOLVED), str(setup.NETWORK_OVERRIDE))} != previous['files']
            or value['packages'] != previous['packages']):
        setup.fail('finalize_repair_basis_changed')
    value.pop('plan_sha256')
    value['schema'] = 'hyprn-host-setup-finalize/v1'
    value['repair_plan_sha256'] = REPAIR_PLAN
    value['host_final_state'] = 'RUNNING'
    value['sources'].update({name: setup.digest((setup.ROOT / name).read_bytes())
                            for name in ('finalize_setup.py', 'repair-plan.json')})
    value['files'][str(RESOLVED)] = {'sha256': setup.digest(RESOLVED_TEXT.encode()), 'mode': '0o644'}
    value['actions'] = ['verify-repair-intent-and-installed-host',
        'persist-ipv4-network-policy-and-test-reconfiguration',
        'disable-systemd-resolved-link-local-discovery', 'restart-systemd-resolved',
        'verify-normal-dns-and-all-host-prerequisites', 'record-closed-host-completion']
    return dict(value, plan_sha256=setup.digest(setup.canonical(value)))


def before_change(policy, previous):
    if setup.reconcile.contract.read_json(setup.STATE / 'repair-intent.json') != previous:
        setup.fail('finalize_repair_intent_differs')
    setup.network_basis()
    try:
        setup.verify(policy, previous)
    except setup.reconcile.Refused as error:
        if error.reason == 'ipv6_must_be_disabled':
            if preflight.ipv6_values() != {'all': '1', 'default': '1', 'lo': '1', 'ens4': '0'}:
                setup.fail('finalize_ipv6_state_differs')
        elif (error.reason != 'unexpected_public_listener'
                or getattr(error, 'diagnostic', {}) != {
                    'stage': 'host_network_listener_check', 'address': '0.0.0.0', 'port': 5355}):
            raise
    # Enumerate all listeners: the known resolver cannot mask another refusal.
    for address, port in preflight.tcp_listeners():
        if (address, port) == ('0.0.0.0', 5355):
            raw = setup.run(['/usr/bin/ss', '--no-header', '--listening', '--tcp', '--numeric', '--processes']).decode()
            matches = [line for line in raw.splitlines() if len(line.split()) > 3
                       and line.split()[3] == '0.0.0.0:5355']
            if len(matches) != 1 or '"systemd-resolve"' not in matches[0]:
                setup.fail('finalize_listener_owner_differs')
        else:
            preflight.check_listener(address, port)
    for path, text in ((RESOLVED, RESOLVED_TEXT), (setup.NETWORK_OVERRIDE, setup.NETWORK_TEXT)):
        if path.exists() or path.is_symlink():
            if setup.reconcile.protected(path).read_text() != text:
                setup.fail('finalize_existing_resolver_override' if path == RESOLVED
                           else 'finalize_existing_network_override')


def apply(policy_path, folder, approved):
    if sys.platform != 'linux' or os.geteuid() != 0 or setup.platform.machine() != 'x86_64':
        setup.fail('finalize_linux_root_required')
    policy_path = setup.reconcile.protected(policy_path)
    setup.reconcile.protected(folder, directory=True)
    policy = setup.validate(setup.reconcile.contract.read_json(policy_path))
    expected = plan(policy, folder)
    if expected['plan_sha256'] != approved:
        setup.fail('finalize_approval_mismatch')
    for name in expected['sources']:
        setup.reconcile.protected(setup.ROOT / name)
    for row in expected['packages']:
        setup.reconcile.protected(Path(folder) / row['filename'])
    setup.reconcile.protected(setup.STATE, directory=True)
    fd = os.open(setup.STATE / 'lock', os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done, intent = setup.STATE / 'completed.json', setup.STATE / 'finalize-intent.json'
        if done.exists():
            if setup.reconcile.contract.read_json(done).get('plan_sha256') != approved:
                setup.fail('finalize_completed_plan_differs')
            return setup.verify(policy, expected)
        if intent.exists():
            setup.fail('finalize_interrupted_requires_reconciliation')
        previous = basis()
        before_change(policy, previous)
        setup.write_new(intent, setup.canonical(expected), 0o600)
        for path, text in ((RESOLVED, RESOLVED_TEXT), (setup.NETWORK_OVERRIDE, setup.NETWORK_TEXT)):
            if not path.exists():
                setup.write_new(path, text.encode(), 0o644)
        setup.configure_ipv4()
        setup.run(['/usr/bin/systemctl', 'restart', 'systemd-resolved.service'], timeout=60)
        setup.run(['/usr/bin/getent', 'ahostsv4', 'compute.googleapis.com'])
        setup.run(['/usr/bin/getent', 'ahostsv4', 'metadata.google.internal'])
        receipt = setup.verify(policy, expected)
        receipt['recovered_from_plan_sha256'] = REPAIR_PLAN
        setup.write_new(done, setup.canonical(receipt), 0o600)
        return receipt
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('plan', 'apply'))
    parser.add_argument('--policy', required=True)
    parser.add_argument('--packages', required=True)
    parser.add_argument('--approve-sha256')
    args = parser.parse_args()
    try:
        value = (plan(setup.reconcile.contract.read_json(args.policy), args.packages)
                 if args.operation == 'plan' else apply(args.policy, args.packages, args.approve_sha256))
        print(json.dumps(value, sort_keys=True, indent=2))
    except (setup.reconcile.Refused, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        value = {'status': 'refused', 'reason': getattr(error, 'reason', type(error).__name__)}
        if hasattr(error, 'diagnostic'):
            value['diagnostic'] = error.diagnostic
        print(json.dumps(value))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
