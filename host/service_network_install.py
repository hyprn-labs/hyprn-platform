"""Install an exactly reviewed private service network on the prepared staging host."""
import argparse
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import stat
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup
import service_network as network
import preflight

ROOT = Path(__file__).resolve().parent
STATE = Path('/var/lib/hyprn-service-network')
POLICY = Path('/etc/hyprn/service-network.json')
CONFIG = Path('/etc/hyprn/egress.json')
SOURCES = ('service_network_install.py', 'service_network.py', 'egress-proxy.json',
           'setup.py', 'host-packages.json', 'contract.py', 'reconcile.py', 'secrets.py', 'preflight.py')
ENV = setup.ENV
run = setup.run
fail = setup.fail


def validate(policy):
    if (not isinstance(policy, dict) or set(policy) != {
            'schema', 'host', 'setup_plan_sha256', 'installation_id', 'network'}
            or policy['schema'] != 'hyprn-service-network-install/v1'
            or not re.fullmatch(r'[a-z][a-z0-9-]{1,62}', policy['installation_id'])
            or not re.fullmatch('[a-f0-9]{64}', policy['setup_plan_sha256'])):
        fail('service_network_policy')
    setup.validate(policy['host'])
    network.checked(policy['network'])
    return policy


def source_pins():
    return {name: setup.digest((ROOT / name).read_bytes()) for name in SOURCES}


def source_root():
    return Path('/opt/hyprn/service-network') / setup.digest(setup.canonical(source_pins()))


def files(policy):
    policy = validate(policy)
    script = source_root() / 'service_network_install.py'
    digest = setup.digest(setup.canonical(policy))
    service = f'''[Unit]
Description=HYPRN private service network
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target hyprn-egress.service
PartOf=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 -I -B {script} enforce --policy {POLICY} --approve-sha256 {digest}
ExecStop=/etc/hyprn/host-setup/container-guard
TimeoutStartSec=120
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
'''
    return {str(POLICY): (setup.canonical(policy), 0o644),
            str(CONFIG): (setup.canonical(network.proxy_config(policy['network'])), 0o644),
            '/etc/hyprn/egress-resolv.conf': (b'nameserver 127.0.0.53\noptions timeout:2 attempts:2\n', 0o644),
            '/etc/systemd/system/hyprn-service-network.service': (service.encode(), 0o644),
            '/etc/systemd/system/hyprn-egress.service': (network.proxy_unit().encode(), 0o644),
            '/etc/systemd/system/docker.service.d/hyprn-network.conf': (
                b'[Unit]\nWants=hyprn-service-network.service\n', 0o644)}


def plan(policy):
    policy = validate(policy)
    pins = source_pins()
    value = {'schema': 'hyprn-service-network-deployment/v1', 'policy': policy,
        'sources': pins, 'source_root': str(source_root()),
        'dependency': setup.reconcile.contract.read_json(ROOT / 'egress-proxy.json'),
        'files': {name: {'sha256': setup.digest(raw), 'mode': mode}
                  for name, (raw, mode) in files(policy).items()},
        'network_plan': network.plan(policy['network']),
        'actions': ['verify-prepared-host-and-exclusive-empty-product', 'install-pinned-proxy-and-notices',
                    'create-unprivileged-proxy-owner', 'install-owned-networks-and-default-deny-rules',
                    'start-restricted-proxy', 'verify-exact-host-network-state'],
        'product_started': False, 'secrets_transferred': False, 'admission': 'closed',
        'host_final_state': 'RUNNING'}
    return dict(value, plan_sha256=setup.digest(setup.canonical(value)))


def docker(*args):
    return run(['/usr/bin/docker', '--host', 'unix:///run/docker.sock', *args])


def network_name(policy, name):
    return policy['installation_id'] + '_' + name


def inspect_bridge(policy, name):
    raw = docker('network', 'inspect', network_name(policy, name))
    rows = json.loads(raw)
    if len(rows) != 1:
        fail('service_network_identity')
    row = rows[0]
    expected = policy['network']['bridges'][name]
    addresses = expected['ipam']['config'][0]
    labels = {'org.hyprn.installation': policy['installation_id'], 'org.hyprn.network': name}
    if (row.get('Name') != network_name(policy, name) or row.get('Driver') != 'bridge'
            or row.get('Internal') != expected['internal'] or row.get('EnableIPv6') is not False
            or row.get('Options') != expected['driver_opts'] or row.get('Labels') != labels
            or row.get('IPAM', {}).get('Config') != [
                {'Subnet': addresses['subnet'], 'Gateway': addresses['gateway']}]
            or row.get('Scope') != 'local'):
        fail('service_network_identity')
    return row['Id']


def bridges(policy):
    existing = docker('network', 'ls', '--format', '{{.Name}}').decode().splitlines()
    result = {}
    for name, value in policy['network']['bridges'].items():
        full = network_name(policy, name)
        if full not in existing:
            address = value['ipam']['config'][0]
            command = ['network', 'create', '--driver', 'bridge', '--ipv6=false',
                '--subnet', address['subnet'], '--gateway', address['gateway'],
                '--opt', 'com.docker.network.bridge.name=' +
                    value['driver_opts']['com.docker.network.bridge.name'],
                '--label', 'org.hyprn.installation=' + policy['installation_id'],
                '--label', 'org.hyprn.network=' + name]
            if value['internal']:
                command.append('--internal')
            docker(*command, full)
        result[name] = inspect_bridge(policy, name)
    return result


def table_rules(raw):
    result = {}
    for line in raw.decode().splitlines():
        parts = shlex.split(line)
        if len(parts) > 2 and parts[0] == '-A':
            result.setdefault(parts[1], []).append(normalize(parts[2:]))
    return result


def normalize(parts):
    parts = list(parts)
    # iptables-save emits an implicit TCP match and canonical state ordering.
    while ['-m', 'tcp'] == parts[:2]:
        parts = parts[2:]
    parts = [v for i, v in enumerate(parts)
             if not (v == '-m' and i + 1 < len(parts) and parts[i + 1] == 'tcp')
             and not (v == 'tcp' and i and parts[i - 1] == '-m')]
    if parts[-2:] == ['--reject-with', 'icmp-port-unreachable']:
        parts = parts[:-2]
    for i, value in enumerate(parts):
        if value == '--ctstate':
            parts[i + 1] = ','.join(sorted(parts[i + 1].split(',')))
    return parts


def verify_rules(policy):
    actual = table_rules(run(['/usr/sbin/iptables-save', '-t', 'filter']))
    expected = network.plan(policy['network'])
    for name, rules in expected['filter_chains'].items():
        if actual.get(name) != [normalize(row) for row in rules]:
            fail('service_firewall_drift')
    for name, jump in expected['required_jumps'].items():
        rows = actual.get(name, [])
        if not rows or rows[0] != normalize(jump) or rows.count(normalize(jump)) != 1:
            fail('service_firewall_jump_drift')
    return setup.digest(setup.canonical(actual))


def apply_rules(policy):
    value = network.plan(policy['network'])
    for chain in value['filter_chains']:
        # Only this operation owns these chains. Other chains remain untouched.
        present = run(['/usr/sbin/iptables', '-w', '10', '-S', chain], allowed=(0, 1))
        if not present:
            run(['/usr/sbin/iptables', '-w', '10', '-N', chain])
    lines = ['*filter']
    for chain, rows in value['filter_chains'].items():
        lines.append('-F ' + chain)
        lines.extend('-A ' + chain + ' ' + shlex.join(row) for row in rows)
    raw = ('\n'.join([*lines, 'COMMIT', ''])).encode()
    run(['/usr/sbin/iptables-restore', '--wait', '10', '--noflush', '--test'], input=raw)
    run(['/usr/sbin/iptables-restore', '--wait', '10', '--noflush'], input=raw)
    for chain, jump in value['required_jumps'].items():
        current = table_rules(run(['/usr/sbin/iptables-save', '-t', 'filter'])).get(chain, [])
        if current and current[0] == normalize(jump) and current.count(normalize(jump)) == 1:
            continue
        for _ in range(current.count(normalize(jump))):
            run(['/usr/sbin/iptables', '-w', '10', '-D', chain, *jump])
        run(['/usr/sbin/iptables', '-w', '10', '-I', chain, '1', *jump])
    return verify_rules(policy)


def require_root():
    if sys.platform != 'linux' or os.geteuid() != 0 or setup.platform.machine() != 'x86_64':
        fail('service_network_linux_root_required')


def pinned_files(policy):
    for name, (raw, mode) in files(policy).items():
        path = setup.reconcile.protected(name)
        if path.read_bytes() != raw or stat.S_IMODE(path.stat().st_mode) != mode:
            fail('service_network_file_drift')
    for name, digest in source_pins().items():
        path = setup.reconcile.protected(source_root() / name)
        if setup.reconcile.digest_file(path) != digest:
            fail('service_network_source_drift')
    pin = setup.reconcile.contract.read_json(ROOT / 'egress-proxy.json')
    binary = Path('/opt/hyprn/egress') / pin['sha256'] / 'envoy'
    if setup.reconcile.digest_file(setup.reconcile.protected(binary)) != pin['sha256']:
        fail('service_proxy_binary_drift')
    return binary


def enforce(policy_path, approved):
    require_root()
    policy = validate(setup.reconcile.contract.read_json(setup.reconcile.protected(policy_path)))
    if setup.digest(setup.canonical(policy)) != approved:
        fail('service_network_approval_mismatch')
    pinned_files(policy)
    setup.cloud_device(policy['host'])
    fd = os.open(STATE / 'network.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ids = bridges(policy)
        preflight.ipv6_observation()
        rules = apply_rules(policy)
        return {'bridges': ids, 'rules_sha256': rules}
    finally:
        os.close(fd)


def verify_live(policy):
    require_root()
    policy = validate(policy)
    binary = pinned_files(policy)
    ids = {name: inspect_bridge(policy, name) for name in policy['network']['bridges']}
    rules = verify_rules(policy)
    preflight.ipv6_observation()
    for unit in ('hyprn-service-network.service', 'hyprn-egress.service'):
        if run(['/usr/bin/systemctl', 'is-active', unit]).decode().strip() != 'active':
            fail('service_network_unit_inactive')
    pid = int(run(['/usr/bin/systemctl', 'show', '--property=MainPID', '--value',
                   'hyprn-egress.service']).decode().strip())
    if (pid <= 1 or Path(f'/proc/{pid}/exe').resolve() != binary
            or Path(f'/proc/{pid}').stat().st_uid != network.PROXY_UID):
        fail('service_proxy_process_identity')
    sockets = run(['/usr/bin/ss', '--no-header', '--listening', '--tcp', '--numeric', '--processes']).decode()
    matches = [line for line in sockets.splitlines() if len(line.split()) > 3
               and line.split()[3] == '172.29.81.1:3128']
    if len(matches) != 1 or ('pid=' + str(pid) + ',') not in matches[0]:
        fail('service_proxy_socket_owner')
    listeners = preflight.tcp_listeners()
    if listeners.count(('172.29.81.1', 3128)) != 1:
        fail('service_proxy_listener_missing')
    for address, port in listeners:
        if (address, port) != ('172.29.81.1', 3128):
            preflight.check_listener(address, port)
    return {'schema': 'hyprn-service-network-observation/v1', 'bridges': ids,
            'rules_sha256': rules, 'proxy_sha256': setup.reconcile.digest_file(binary),
            'policy_sha256': setup.digest(setup.canonical(policy)), 'ipv6': 'disabled',
            'packet_probes_passed': False, 'admission': 'closed'}


def apply(policy_path, dependency, approved):
    require_root()
    policy = validate(setup.reconcile.contract.read_json(setup.reconcile.protected(policy_path)))
    expected = plan(policy)
    if approved != expected['plan_sha256']:
        fail('service_network_approval_mismatch')
    setup.mkdir(STATE, 0o700)
    fd = os.open(STATE / 'install.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (STATE / 'intent.json').exists():
            fail('service_network_existing_attempt_requires_reconciliation')
        old = setup.reconcile.contract.read_json(setup.reconcile.protected(
            setup.STATE / 'finalize-intent.json'))
        receipt = setup.reconcile.contract.read_json(setup.reconcile.protected(
            setup.STATE / 'completed.json'))
        if (old.get('plan_sha256') != policy['setup_plan_sha256']
                or receipt.get('plan_sha256') != policy['setup_plan_sha256']
                or setup.digest(setup.canonical({k:v for k,v in old.items() if k != 'plan_sha256'}))
                    != policy['setup_plan_sha256']):
            fail('service_network_prepared_host_mismatch')
        setup.verify(policy['host'], old)
        pin = expected['dependency']
        dependency = setup.reconcile.protected(dependency, directory=True)
        artifacts = {'envoy': (dependency / ('envoy-' + pin['version'] + '-linux-x86_64'), pin['sha256'])}
        for name, field in (('LICENSE', 'license'), ('NOTICE', 'notice')):
            artifacts[name] = (dependency / name, pin[field]['sha256'])
        for path, digest in artifacts.values():
            if setup.reconcile.digest_file(setup.reconcile.protected(path)) != digest:
                fail('service_proxy_dependency_mismatch')
        for name in files(policy):
            if Path(name).exists() or Path(name).is_symlink():
                fail('service_network_existing_file')
        try:
            pwd.getpwuid(network.PROXY_UID)
        except KeyError:
            pass
        else:
            fail('service_proxy_uid_in_use')
        try:
            grp.getgrgid(network.PROXY_UID)
        except KeyError:
            pass
        else:
            fail('service_proxy_gid_in_use')
        for lookup in (pwd.getpwnam, grp.getgrnam):
            try:
                lookup('hyprn-egress')
            except KeyError:
                pass
            else:
                fail('service_proxy_name_in_use')
        setup.write_new(STATE / 'intent.json', setup.canonical(expected), 0o600)
        for name in SOURCES:
            setup.write_new(source_root() / name, (ROOT / name).read_bytes(), 0o644)
        destination = Path('/opt/hyprn/egress') / pin['sha256']
        for name, (path, _) in artifacts.items():
            setup.write_new(destination / name, path.read_bytes(), 0o755 if name == 'envoy' else 0o644)
        run(['/usr/sbin/groupadd', '--system', '--gid', str(network.PROXY_UID), 'hyprn-egress'])
        run(['/usr/sbin/useradd', '--system', '--uid', str(network.PROXY_UID), '--gid', str(network.PROXY_UID),
             '--no-create-home', '--home-dir', '/nonexistent', '--shell', '/usr/sbin/nologin', 'hyprn-egress'])
        for name, (raw, mode) in files(policy).items():
            setup.write_new(Path(name), raw, mode)
        run([str(destination / 'envoy'), '--mode', 'validate', '--config-path', str(CONFIG),
             '--concurrency', '1', '--log-level', 'error'])
        run(['/usr/bin/systemctl', 'daemon-reload'])
        run(['/usr/bin/systemctl', 'enable', 'hyprn-service-network.service', 'hyprn-egress.service'])
        run(['/usr/bin/systemctl', 'start', 'hyprn-service-network.service'], timeout=150)
        run(['/usr/bin/systemctl', 'start', 'hyprn-egress.service'])
        deadline = time.monotonic() + 15
        while ('172.29.81.1', 3128) not in preflight.tcp_listeners():
            if time.monotonic() >= deadline:
                fail('service_proxy_readiness_timeout')
            time.sleep(0.1)
        result = verify_live(policy)
        setup.write_new(STATE / 'completed.json', setup.canonical(dict(result, plan_sha256=approved)), 0o600)
        return result
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('plan', 'apply', 'enforce', 'verify'))
    parser.add_argument('--policy', required=True)
    parser.add_argument('--dependency')
    parser.add_argument('--approve-sha256')
    args = parser.parse_args()
    try:
        if args.operation == 'plan':
            value = plan(setup.reconcile.contract.read_json(Path(args.policy)))
        elif args.operation == 'apply':
            if not args.dependency or not args.approve_sha256:
                fail('service_network_required_arguments')
            value = apply(Path(args.policy), Path(args.dependency), args.approve_sha256)
        elif args.operation == 'enforce':
            value = enforce(Path(args.policy), args.approve_sha256)
        else:
            value = verify_live(setup.reconcile.contract.read_json(Path(args.policy)))
        print(json.dumps(value, sort_keys=True))
        return 0
    except (setup.reconcile.Refused, ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'error': getattr(error, 'reason', 'service_network_operation_failed')}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
