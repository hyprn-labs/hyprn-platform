"""Resume one reviewed package-stage setup failure without formatting storage."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup

BASE_PLAN = '0a18d1d19b1951fdc172b4a5ac986c387273e5ea187b3c42f5f8a5c1853c83ee'
ADDED = {'libjansson4', 'libnftables1', 'nftables'}
BLOCKER = Path('/usr/sbin/policy-rc.d')


def plan(policy, folder):
    base = setup.reconcile.contract.read_json(setup.ROOT / 'base-plan.json')
    canonical = {key: value for key, value in base.items() if key != 'plan_sha256'}
    if (base['plan_sha256'] != BASE_PLAN or setup.digest(setup.canonical(canonical)) != BASE_PLAN
            or base['policy'] != policy):
        setup.fail('repair_original_plan_binding')
    fresh = setup.plan(policy, folder)
    old = {row['name']: row for row in base['packages']}
    current = {row['name']: row for row in fresh['packages']}
    if set(current) - set(old) != ADDED or any(current.get(name) != row for name, row in old.items()):
        setup.fail('repair_original_packages_changed')
    if fresh['files'] != base['files']:
        setup.fail('repair_original_host_files_changed')
    fresh.pop('plan_sha256')
    fresh['schema'] = 'hyprn-host-setup-repair/v1'
    fresh['base_plan_sha256'] = BASE_PLAN
    fresh['sources'].update({name: setup.digest((setup.ROOT / name).read_bytes())
                            for name in ('repair_setup.py', 'base-plan.json')})
    fresh['actions'] = ['verify-original-intent-mount-files-and-package-stage',
        'verify-all-dependencies-explicitly', 'install-three-pinned-os-dependencies-with-services-blocked',
        'configure-existing-pinned-docker-package', 'keep-nftables-service-disabled',
        'apply-original-runtime-settings', 'start-empty-docker-behind-original-closed-firewall',
        'verify-host-prerequisites']
    return dict(fresh, plan_sha256=setup.digest(setup.canonical(fresh)))


def partial_state(policy, expected):
    intent = setup.reconcile.contract.read_json(setup.STATE / 'intent.json')
    base = setup.reconcile.contract.read_json(setup.ROOT / 'base-plan.json')
    if intent != base:
        setup.fail('repair_original_intent_differs')
    device = setup.cloud_device(policy)
    mounted = json.loads(setup.run(['/usr/bin/findmnt', '--json', '--mountpoint', str(setup.DATA),
                                   '--output', 'SOURCE,UUID,FSTYPE,OPTIONS']))['filesystems']
    if (len(mounted) != 1 or mounted[0]['uuid'] != policy['disk_uuid']
            or mounted[0]['fstype'] != 'ext4' or Path(mounted[0]['source']).resolve() != device
            or not {'rw', 'nodev', 'nosuid'} <= set(mounted[0]['options'].split(','))):
        setup.fail('repair_existing_mount_differs')
    for name, entry in expected['files'].items():
        path = setup.reconcile.protected(name)
        if (setup.reconcile.digest_file(path) != entry['sha256']
                or oct(stat.S_IMODE(path.stat().st_mode)) != entry['mode']):
            setup.fail('repair_existing_file_differs')
    for row in setup.reconcile.contract.read_json(setup.LOCK)['packages']:
        observed = subprocess.run(['/usr/bin/dpkg-query', '--show', '--showformat=${Status}\t${Version}', row['name']],
                                  env=setup.ENV, capture_output=True, timeout=20)
        if row['name'] in ADDED:
            if observed.returncode == 0 and b'not-installed' not in observed.stdout:
                setup.fail('repair_added_package_already_present')
            continue
        status = 'install ok unpacked' if row['name'] == 'docker-ce' else 'install ok installed'
        if observed.returncode or observed.stdout.decode() != status + '\t' + row['version']:
            setup.fail('repair_original_package_stage_differs:' + row['name'])
        for name, sha in row['installed_files'].items():
            if setup.reconcile.digest_file(setup.reconcile.protected(name)) != sha:
                setup.fail('repair_original_binary_differs')
    for name, uid in (('application', 10002), ('modeling', 10001), ('execution', 10003)):
        path = setup.DATA / name
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_gid != uid
                or stat.S_IMODE(info.st_mode) != 0o700 or any(path.iterdir())):
            setup.fail('repair_unexpected_product_data')
    for unit in ('docker.service', 'docker.socket', 'nftables.service'):
        state = setup.run(['/usr/bin/systemctl', 'show', '--property=ActiveState', '--value', unit]).decode().strip()
        if state != 'inactive':
            setup.fail('repair_unexpected_active_service')
    if BLOCKER.exists() or BLOCKER.is_symlink():
        setup.fail('repair_existing_service_policy')


def apply(policy_path, folder, approved):
    if sys.platform != 'linux' or os.geteuid() != 0 or setup.platform.machine() != 'x86_64':
        setup.fail('repair_linux_root_required')
    policy_path = setup.reconcile.protected(policy_path)
    setup.reconcile.protected(folder, directory=True)
    policy = setup.validate(setup.reconcile.contract.read_json(policy_path))
    expected = plan(policy, folder)
    if expected['plan_sha256'] != approved:
        setup.fail('repair_approval_mismatch')
    for name in expected['sources']:
        setup.reconcile.protected(setup.ROOT / name)
    for row in expected['packages']:
        setup.reconcile.protected(Path(folder) / row['filename'])
    setup.reconcile.protected(setup.STATE, directory=True)
    fd = os.open(setup.STATE / 'lock', os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done = setup.STATE / 'completed.json'
        if done.exists():
            if setup.reconcile.contract.read_json(done).get('plan_sha256') != approved:
                setup.fail('repair_completed_plan_differs')
            return setup.verify(policy, expected)
        repair_intent = setup.STATE / 'repair-intent.json'
        if repair_intent.exists():
            setup.fail('repair_interrupted_requires_reconciliation')
        partial_state(policy, expected)
        rows = setup.packages(folder)
        setup.package_probe(rows, folder)
        setup.write_new(repair_intent, setup.canonical(expected), 0o600)
        blocker = BLOCKER
        setup.write_new(blocker, b'#!/bin/sh\nexit 101\n', 0o755)
        try:
            paths = [str(Path(folder) / row['filename']) for row in rows if row['name'] in ADDED]
            setup.run(['/usr/bin/dpkg', '--force-confold', '--install', *paths], timeout=300,
                      package_diagnostics='os_dependency_installation')
            setup.run(['/usr/bin/dpkg', '--configure', 'docker-ce'], timeout=180,
                      package_diagnostics='docker_configuration')
        finally:
            if blocker.read_bytes() == b'#!/bin/sh\nexit 101\n':
                blocker.unlink()
        setup.run(['/usr/bin/systemctl', 'disable', 'nftables.service'])
        setup.run(['/usr/sbin/sysctl', '--load=/etc/sysctl.d/70-hyprn-containers.conf'])
        setup.run(['/usr/bin/systemd-tmpfiles', '--create', '/etc/tmpfiles.d/hyprn.conf'])
        setup.run(['/usr/bin/systemctl', 'daemon-reload'])
        setup.run(['/usr/bin/systemctl', 'enable', '--now', 'docker.service', 'docker.socket'], timeout=120)
        receipt = setup.verify(policy, expected)
        receipt['recovered_from_plan_sha256'] = BASE_PLAN
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
