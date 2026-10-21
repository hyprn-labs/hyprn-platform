"""Prepare a fresh, closed staging host from an explicitly approved plan.

Plan is read-only. Apply uses only predownloaded, pinned Debian packages and
fixed platform operations; it never fetches secrets or starts product services.
An interrupted application requires reconciliation, never automatic reformatting.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
from types import SimpleNamespace
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile

ROOT = Path(__file__).resolve().parent
LOCK = ROOT / 'host-packages.json'
STATE = Path('/var/lib/hyprn-host-setup')
CONFIG = Path('/etc/hyprn/host-setup')
DATA = Path('/srv/hyprn/staging')
MOUNT = 'srv-hyprn-staging.mount'
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
       'DEBIAN_FRONTEND': 'noninteractive'}
FIELDS = {'schema', 'project_id', 'project_number', 'zone', 'host_id', 'instance_id',
          'disk_name', 'disk_id', 'device_name', 'disk_bytes', 'disk_uuid'}


def fail(reason):
    raise reconcile.Refused(reason)


def canonical(value):
    return reconcile.contract.canonical(value)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate(value):
    if (not isinstance(value, dict) or set(value) != FIELDS
            or value['schema'] != 'hyprn-host-setup/v1'
            or value['project_id'] != 'hyprn-staging'
            or value['host_id'] != 'hyprn-staging-host'
            or value['disk_name'] != 'hyprn-staging-data'
            or value['device_name'] != 'hyprn-data'
            or value['zone'] != 'europe-west1-b'
            or type(value['disk_bytes']) is not int or value['disk_bytes'] != 100 * 1024**3):
        fail('setup_policy')
    for name in ('project_number', 'instance_id', 'disk_id'):
        if not isinstance(value[name], str) or not re.fullmatch('[1-9][0-9]{0,30}', value[name]):
            fail('setup_numeric_identity')
    try:
        if str(UUID(value['disk_uuid'])) != value['disk_uuid']:
            fail('setup_disk_uuid')
    except (ValueError, TypeError, AttributeError):
        fail('setup_disk_uuid')
    return value


def packages(folder):
    """Verify every exact archive before any installation or service operation."""
    manifest = reconcile.contract.read_json(LOCK)
    if (manifest['schema'] != 'hyprn-host-packages/v1' or manifest['os'] != 'debian12'
            or manifest['architecture'] != 'amd64'):
        fail('package_manifest')
    rows = manifest['packages']
    expected = {'containerd.io', 'docker-ce-cli', 'docker-ce', 'docker-compose-plugin',
                'cloudflared', 'libjansson4', 'libnftables1', 'nftables'}
    if len(rows) != len(expected) or {row['name'] for row in rows} != expected:
        fail('package_set')
    for row in rows:
        if Path(row['filename']).name != row['filename'] or not row['filename'].endswith('.deb'):
            fail('package_name')
        path = Path(folder) / row['filename']
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_size != row['size'] or reconcile.digest_file(path) != row['sha256']):
            fail('package_bytes')
    return rows


def files(policy):
    """Fixed platform configuration; no template accepts arbitrary commands."""
    mount = f'''[Unit]
Description=HYPRN staging data
Before=docker.service

[Mount]
What=/dev/disk/by-uuid/{policy['disk_uuid']}
Where={DATA}
Type=ext4
Options=rw,nodev,nosuid
TimeoutSec=30

[Install]
WantedBy=multi-user.target
'''
    guard = '''#!/bin/sh
set -eu
# Docker cannot start with permissive forwarding; all product rules come later.
/usr/sbin/iptables -w 10 -N DOCKER-USER 2>/dev/null || /usr/sbin/iptables -w 10 -S DOCKER-USER >/dev/null
/usr/sbin/iptables-restore --wait 10 --noflush <<'RULES'
*filter
-F DOCKER-USER
-A DOCKER-USER -d 169.254.169.254/32 -j DROP
-A DOCKER-USER -j DROP
COMMIT
RULES
while /usr/sbin/iptables -w 10 -C FORWARD -j DOCKER-USER 2>/dev/null; do
    /usr/sbin/iptables -w 10 -D FORWARD -j DOCKER-USER
done
/usr/sbin/iptables -w 10 -I FORWARD 1 -j DOCKER-USER
# Traffic to the host itself traverses INPUT rather than DOCKER-USER.
for bridge in docker0 'br+'; do
    if ! /usr/sbin/iptables -w 10 -C INPUT -i "$bridge" -j DROP 2>/dev/null; then
        /usr/sbin/iptables -w 10 -I INPUT 1 -i "$bridge" -j DROP
    fi
done
'''
    dropin = f'''[Unit]
Requires={MOUNT}
After={MOUNT}

[Service]
TimeoutStartSec=120
ExecStartPre={CONFIG}/container-guard
ExecStartPost={CONFIG}/container-guard
'''
    daemon = {'data-root': str(DATA / 'docker'), 'live-restore': False,
              'log-driver': 'local', 'log-opts': {'max-size': '10m', 'max-file': '3'},
              'bridge': 'none', 'iptables': True, 'ip6tables': False, 'ipv6': False,
              'userland-proxy': False}
    return {
        '/etc/systemd/system/' + MOUNT: (mount, 0o644),
        '/etc/systemd/system/docker.service.d/hyprn.conf': (dropin, 0o644),
        str(CONFIG / 'container-guard'): (guard, 0o755),
        '/etc/systemd/system/containerd.service.d/hyprn.conf': (
            '[Unit]\nRequires=' + MOUNT + '\nAfter=' + MOUNT + '\n'
            '[Service]\nTimeoutStartSec=120\n', 0o644),
        '/etc/containerd/config.toml': (
            'version = 3\nroot = "/srv/hyprn/staging/containerd"\n'
            'state = "/run/containerd"\ndisabled_plugins = ["io.containerd.grpc.v1.cri"]\n', 0o644),
        '/etc/docker/daemon.json': (json.dumps(daemon, sort_keys=True, indent=2) + '\n', 0o644),
        '/etc/sysctl.d/70-hyprn-containers.conf': (
            'net.ipv4.ip_forward=1\nnet.ipv6.conf.all.disable_ipv6=1\n'
            'net.ipv6.conf.default.disable_ipv6=1\n', 0o644),
        '/etc/tmpfiles.d/hyprn.conf': (
            'd /run/hyprn 0700 root root -\n'
            'd /run/hyprn/secrets 0700 root root -\n'
            'd /run/hyprn/registry 0700 root root -\n', 0o644),
    }


def plan(policy, folder):
    policy = validate(policy)
    rows = packages(folder)
    sources = {name: digest((ROOT / name).read_bytes())
               for name in ('setup.py', 'reconcile.py', 'secrets.py', 'contract.py', 'host-packages.json', 'preflight.py')}
    rendered = files(policy)
    value = dict(schema='hyprn-host-setup-plan/v1', policy=policy, sources=sources,
        packages=[{k: row[k] for k in ('name', 'version', 'filename', 'sha256', 'size')} for row in rows],
        files={name: {'sha256': digest(text.encode()), 'mode': oct(mode)}
               for name, (text, mode) in rendered.items()},
        actions=['verify-live-instance-and-exclusive-blank-data-disk',
                 'verify-package-metadata-and-dependencies', 'format-exact-blank-disk-ext4',
                 'mount-by-pinned-filesystem-uuid', 'install-pinned-packages-with-services-blocked',
                 'create-native-service-account-and-owner-directories',
                 'install-closed-firewall-and-bounded-docker-storage',
                 'start-empty-docker-behind-closed-firewall', 'verify-host-prerequisites'],
        product_started=False, secrets_transferred=False, admission='closed')
    return dict(value, plan_sha256=digest(canonical(value)))


def run(args, *, input=None, allowed=(0,), timeout=60, package_diagnostics=None):
    result = subprocess.run(args, input=input, env=ENV, capture_output=True, timeout=timeout)
    if result.returncode not in allowed:
        error = reconcile.Refused('host_command_refused:' + Path(args[0]).name)
        if package_diagnostics:
            # Only the package dry-run opts in; never expose arbitrary command data.
            error.diagnostic = {
                'stage': package_diagnostics, 'exit_code': result.returncode,
                'stdout': result.stdout[-16384:].decode('utf-8', errors='replace'),
                'stderr': result.stderr[-16384:].decode('utf-8', errors='replace')}
        raise error
    return result.stdout


def cloud_device(policy):
    target = SimpleNamespace(runtime=policy)
    host = reconcile.GoogleHost(target, disk_name=policy['disk_name'], device_name=policy['device_name'])
    host.principal.preflight(SimpleNamespace(**policy))
    for field, expected in (('instance/id', policy['instance_id']), ('instance/name', policy['host_id']),
            ('instance/zone', 'projects/' + policy['project_number'] + '/zones/' + policy['zone'])):
        if reconcile.request_google(True, '/computeMetadata/v1/' + field).decode().strip() != expected:
            fail('setup_host_identity')
    base = '/compute/v1/projects/' + policy['project_id'] + '/zones/' + policy['zone']
    instance = host.request('compute.googleapis.com', base + '/instances/' + policy['host_id'])
    disk = host.request('compute.googleapis.com', base + '/disks/' + policy['disk_name'])
    if (instance.get('id') != policy['instance_id'] or disk.get('id') != policy['disk_id']
            or disk.get('sizeGb') != str(policy['disk_bytes'] // 1024**3)
            or any(n.get('accessConfigs') for n in instance.get('networkInterfaces', []))):
        fail('setup_resource_identity')
    device = reconcile.disk_attachment(policy, disk_name=policy['disk_name'],
        device_name=policy['device_name'], instance=instance, disk=disk).resolve(strict=True)
    if not stat.S_ISBLK(device.stat().st_mode):
        fail('setup_block_device')
    return device


def blank_device(device, expected_bytes):
    value = json.loads(run(['/usr/bin/lsblk', '--json', '--bytes', '--output',
                          'PATH,TYPE,SIZE,MOUNTPOINTS', str(device)]))['blockdevices']
    if (len(value) != 1 or value[0]['type'] != 'disk' or value[0]['size'] != expected_bytes
            or value[0].get('children') or any(value[0].get('mountpoints') or [])):
        fail('setup_disk_not_blank')
    signatures = json.loads(run(['/usr/sbin/wipefs', '--json', str(device)]))
    if signatures.get('signatures') != []:
        fail('setup_disk_has_signatures')
    # Explicitly exclude the root filesystem even if attachment evidence is wrong.
    root = json.loads(run(['/usr/bin/findmnt', '--json', '/', '--output', 'SOURCE']))
    root_device = Path(root['filesystems'][0]['source']).resolve(strict=True)
    parent = run(['/usr/bin/lsblk', '--noheadings', '--output', 'PKNAME', str(root_device)]).decode().strip()
    if root_device == device.resolve(strict=True) or (parent and Path('/dev', parent).resolve() == device.resolve(strict=True)):
        fail('setup_boot_disk_forbidden')


def mkdir(path, mode=0o755, uid=0):
    path = Path(path)
    if not path.exists():
        mkdir(path.parent)
        path.mkdir(mode=mode)
        os.chown(path, uid, uid)
        path.chmod(mode)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_gid != uid
            or stat.S_IMODE(info.st_mode) != mode):
        fail('setup_directory_authority')


def write_new(path, raw, mode):
    path = Path(path)
    if path.parent.exists():
        reconcile.protected(path.parent, directory=True)
    else:
        mkdir(path.parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(mode)


def installed_package_version(name):
    result = subprocess.run(['/usr/bin/dpkg-query', '--show',
        '--showformat=${Status}\t${Version}', name], env=ENV, capture_output=True, timeout=20)
    fields = result.stdout.decode().split('\t')
    if result.returncode == 0 and len(fields) == 2 and fields[0] == 'install ok installed':
        return fields[1]
    return None


def dependencies(rows):
    """dpkg's install dry-run does not prove configure-time dependencies exist."""
    planned = {row['name']: row['version'] for row in rows}
    for row in rows:
        for field in ('depends', 'pre_depends'):
            for term in (row.get(field) or '').split(','):
                if not term.strip():
                    continue
                match = re.fullmatch(r'\s*([a-z0-9][a-z0-9+.-]*)(?: \((>=|<=|=|>>|<<) ([^ ()]+)\))?\s*', term)
                if not match:
                    fail('setup_dependency_syntax_requires_review')
                name, operator, minimum = match.groups()
                version = (planned.get(name) if field == 'depends' else None) or installed_package_version(name)
                if version is None:
                    fail('setup_dependency_missing:' + name)
                if operator:
                    result = subprocess.run(['/usr/bin/dpkg', '--compare-versions', version,
                        operator, minimum], env=ENV, capture_output=True, timeout=20)
                    if result.returncode != 0:
                        fail('setup_dependency_version:' + name)


def package_probe(rows, folder):
    paths = []
    for row in rows:
        path = str(Path(folder) / row['filename'])
        observed = run(['/usr/bin/dpkg-deb', '--show', '--showformat=${Package}\t${Version}\t${Architecture}', path])
        if observed.decode() != '\t'.join(row[key] for key in ('name', 'version', 'architecture')):
            fail('setup_debian_package_identity')
        declarations = run(['/usr/bin/dpkg-deb', '--show',
            '--showformat=${Depends}\t${Pre-Depends}', path]).decode()
        if declarations != (row.get('depends') or '') + '\t' + (row.get('pre_depends') or ''):
            fail('setup_package_dependencies_differ')
        paths.append(path)
    dependencies(rows)
    run(['/usr/bin/dpkg', '--dry-run', '--install', *paths], timeout=120, package_diagnostics="package_dry_run")
    return paths


def verify(policy, expected):
    device = cloud_device(policy)
    value = json.loads(run(['/usr/bin/findmnt', '--json', '--mountpoint', str(DATA),
                           '--output', 'SOURCE,UUID,FSTYPE,OPTIONS']))['filesystems']
    if (len(value) != 1 or value[0]['uuid'] != policy['disk_uuid'] or value[0]['fstype'] != 'ext4'
            or not {'rw', 'nodev', 'nosuid'} <= set(value[0]['options'].split(','))
            or Path(value[0]['source']).resolve() != device):
        fail('setup_mount_identity')
    for name, specification in expected['files'].items():
        path = reconcile.protected(name)
        if (reconcile.digest_file(path) != specification['sha256']
                or oct(stat.S_IMODE(path.stat().st_mode)) != specification['mode']):
            fail('setup_file_drift')
    for row in expected['packages']:
        value = run(['/usr/bin/dpkg-query', '--show', '--showformat=${Status}\t${Version}', row['name']]).decode()
        if value != 'install ok installed\t' + row['version']:
            fail('setup_package_drift')
    if run(['/usr/bin/docker', '--host', 'unix:///run/docker.sock', 'ps', '-aq']).strip():
        fail('setup_unexpected_containers')
    rows = reconcile.contract.read_json(LOCK)['packages']
    by_name = {row['name']: row for row in rows}
    for row in rows:
        for path, sha256 in row['installed_files'].items():
            if reconcile.digest_file(reconcile.protected(path)) != sha256:
                fail('setup_installed_binary_drift')
    import preflight
    preflight.operating_system()
    target = SimpleNamespace(runtime={
        'execution_host': {'docker_endpoint': 'unix:///run/docker.sock',
                           'host_home': str(DATA / 'execution/home')},
        'service_users': {'app': 10002, 'modeling': 10001, 'execution': 10003, 'worker': 65534},
        'mounts': {'application': str(DATA / 'application'), 'modeling': str(DATA / 'modeling'),
                   'execution': str(DATA / 'execution'), 'secrets': '/run/hyprn/secrets'}})
    docker = preflight.docker_observation(target, {
        'docker': {'sha256': by_name['docker-ce-cli']['installed_files']['/usr/bin/docker'],
                   'version': by_name['docker-ce']['version'].split(':')[-1].split('-')[0]},
        'compose': {'sha256': next(iter(by_name['docker-compose-plugin']['installed_files'].values())),
                    'version': by_name['docker-compose-plugin']['version'].split('-')[0]}})
    preflight.owners_and_paths(target, docker)
    preflight.network_observation()
    return {'schema': 'hyprn-host-prepared/v1', 'plan_sha256': expected['plan_sha256'],
            'disk_uuid': policy['disk_uuid'], 'product_started': False, 'admission': 'closed',
            'execution_qualified': False}


def apply(policy_path, folder, approved):
    if sys.platform != 'linux' or os.geteuid() != 0 or platform.machine() != 'x86_64':
        fail('setup_linux_root_amd64_required')
    policy_path = reconcile.protected(policy_path)
    reconcile.protected(folder, directory=True)
    for name in ('setup.py', 'reconcile.py', 'secrets.py', 'contract.py', 'host-packages.json', 'preflight.py'):
        reconcile.protected(ROOT / name)
    policy = validate(reconcile.contract.read_json(policy_path))
    for row in reconcile.contract.read_json(LOCK)['packages']:
        reconcile.protected(Path(folder) / row['filename'])
    expected = plan(policy, folder)
    if expected['plan_sha256'] != approved:
        fail('setup_approval_mismatch')
    if platform.freedesktop_os_release().get('VERSION_ID') != '12' or platform.freedesktop_os_release().get('ID') != 'debian':
        fail('setup_debian12_required')
    if len(Path('/proc/swaps').read_text().splitlines()) != 1:
        fail('setup_swap_forbidden')
    mkdir(STATE, 0o700)
    fd = os.open(STATE / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done, intent = STATE / 'completed.json', STATE / 'intent.json'
        if done.exists():
            if reconcile.contract.read_json(done)['plan_sha256'] != approved:
                fail('setup_already_initialized_differently')
            return verify(policy, expected)
        if intent.exists():
            fail('setup_interrupted_requires_reconciliation')
        device = cloud_device(policy)
        blank_device(device, policy['disk_bytes'])
        if DATA.exists():
            reconcile.protected(DATA, directory=True)
            if any(DATA.iterdir()):
                fail('setup_data_path_not_empty')
        if run(['/usr/bin/findmnt', '--noheadings', '--mountpoint', str(DATA)], allowed=(0, 1)).strip():
            fail('setup_data_path_already_mounted')
        for path in (*files(policy), '/usr/sbin/policy-rc.d'):
            if Path(path).exists() or Path(path).is_symlink():
                fail('setup_existing_configuration')
        for name in ('docker-ce', 'docker-ce-cli', 'docker.io', 'containerd.io', 'containerd', 'cloudflared'):
            found = subprocess.run(['/usr/bin/dpkg-query', '--show', '--showformat=${Status}', name],
                                   env=ENV, capture_output=True, timeout=20)
            if found.returncode == 0 and b'installed' in found.stdout:
                fail('setup_existing_runtime')
        import pwd, grp
        for lookup, value in ((pwd.getpwuid, 10001), (pwd.getpwuid, 10002), (pwd.getpwuid, 10003), (pwd.getpwnam, 'hyprn-execution'),
                              (grp.getgrgid, 10003), (grp.getgrnam, 'hyprn-execution')):
            try:
                lookup(value)
            except KeyError:
                continue
            fail('setup_existing_execution_account')
        rows = packages(folder)
        for row in rows:
            for name in row['installed_files']:
                if Path(name).exists() or Path(name).is_symlink():
                    fail('setup_existing_runtime_binary')
        for name in ('/etc/docker', '/etc/containerd', '/var/lib/docker', '/var/lib/containerd',
                     '/usr/local/etc/cloudflared', '/etc/systemd/system/docker.service.d',
                     '/etc/systemd/system/containerd.service.d'):
            path = Path(name)
            if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
                fail('setup_existing_runtime_configuration')
        for name in ('/usr/local/bin/cloudflared', '/etc/systemd/system/docker.service',
                     '/etc/systemd/system/docker.socket', '/etc/systemd/system/containerd.service'):
            if Path(name).exists() or Path(name).is_symlink():
                fail('setup_existing_runtime_configuration')
        paths = package_probe(rows, folder)
        write_new(intent, canonical(expected), 0o600)
        # Reconcile live attachment again immediately before the one format attempt.
        if cloud_device(policy) != device:
            fail('setup_device_changed')
        blank_device(device, policy['disk_bytes'])
        # No forced overwrite: exclusive blank-device proof precedes this one attempt.
        run(['/usr/sbin/mkfs.ext4', '-U', policy['disk_uuid'], '-L', 'hyprn-staging', str(device)], timeout=120)
        mkdir(DATA)
        rendered = files(policy)
        for name, (text, mode) in rendered.items():
            write_new(name, text.encode(), mode)
        run(['/usr/bin/systemctl', 'daemon-reload'])
        run(['/usr/bin/systemctl', 'enable', '--now', MOUNT])
        for name, uid in (('application', 10002), ('modeling', 10001), ('execution', 10003)):
            mkdir(DATA / name, 0o700, uid)
        for name in ('docker', 'containerd', 'deployment', 'backup-staging'):
            mkdir(DATA / name, 0o700)
        run(['/usr/sbin/groupadd', '--system', '--gid', '10003', 'hyprn-execution'])
        run(['/usr/sbin/useradd', '--system', '--uid', '10003', '--gid', '10003', '--no-create-home',
             '--home-dir', str(DATA / 'execution/home'), '--shell', '/usr/sbin/nologin', 'hyprn-execution'])
        blocker = Path('/usr/sbin/policy-rc.d')
        write_new(blocker, b'#!/bin/sh\nexit 101\n', 0o755)
        try:
            run(['/usr/bin/dpkg', '--force-confold', '--install', *paths], timeout=300,
                package_diagnostics='package_installation')
        finally:
            if blocker.read_bytes() == b'#!/bin/sh\nexit 101\n':
                blocker.unlink()
        run(['/usr/bin/systemctl', 'disable', 'nftables.service'])
        run(['/usr/sbin/sysctl', '--load=/etc/sysctl.d/70-hyprn-containers.conf'])
        run(['/usr/bin/systemd-tmpfiles', '--create', '/etc/tmpfiles.d/hyprn.conf'])
        run(['/usr/bin/systemctl', 'daemon-reload'])
        run(['/usr/bin/systemctl', 'enable', '--now', 'docker.service', 'docker.socket'], timeout=120)
        receipt = verify(policy, expected)
        write_new(done, canonical(receipt), 0o600)
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
        if args.operation == 'plan':
            value = plan(reconcile.contract.read_json(args.policy), args.packages)
        else:
            value = apply(args.policy, args.packages, args.approve_sha256)
        print(json.dumps(value, sort_keys=True, indent=2))
    except (reconcile.Refused, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        value = {'status': 'refused', 'reason': getattr(error, 'reason', type(error).__name__)}
        if hasattr(error, 'diagnostic'):
            value['diagnostic'] = error.diagnostic
        print(json.dumps(value))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
