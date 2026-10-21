"""Install exactly reviewed tunnel and bounded qualification units; never edit cloud settings."""
import argparse
import base64
import grp
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import pwd
import re
import socket
import stat
import sys
import time
from types import SimpleNamespace
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activation
import setup

bootstrap, reconcile, contract = activation.bootstrap, activation.reconcile, activation.contract
Refused = activation.Refused
ROOT = Path(__file__).resolve().parents[1]
POLICY = Path('/etc/hyprn/activation-install.json')
ADMISSION = Path('/etc/hyprn/qualification.json')
STATE = Path('/var/lib/hyprn-activation-install')
TOKEN_ROOT = Path('/run/hyprn-tunnel')
TOKEN = TOKEN_ROOT / 'tunnel-token'
UID = 10006
NAME = 'hyprn-tunnel'
FIELDS = {'schema', 'platform_root', 'activation', 'account_id', 'tunnel_id',
          'secret_version', 'access_readback'}


def validate(policy):
    if (not bootstrap.exact_fields(policy, FIELDS)
            or policy['schema'] != 'hyprn-activation-install/v1'
            or not bootstrap.absolute(policy['platform_root'])
            or any(c.isspace() or c in '%"\\' for c in policy['platform_root'])
            or not isinstance(policy['account_id'], str)
            or re.fullmatch('[a-f0-9]{32}', policy['account_id']) is None
            or type(policy['secret_version']) is not int
            or not 1 <= policy['secret_version'] <= 2147483647):
        raise Refused('activation_install_policy')
    try:
        if str(UUID(policy['tunnel_id'])) != policy['tunnel_id']:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise Refused('activation_install_tunnel_identity') from None
    activation.validate_policy(policy['activation'])
    if policy['activation']['mode'] != 'qualification':
        raise Refused('activation_install_starts_with_qualification')
    readback = policy['access_readback']
    if (not bootstrap.exact_fields(readback, {'path', 'sha256'})
            or not bootstrap.absolute(readback['path']) or not bootstrap.sha(readback['sha256'])):
        raise Refused('activation_install_access_readback')
    return policy


def source_pins():
    files = [*sorted((ROOT / 'host').glob('*.py')), *sorted((ROOT / 'host').glob('*.json')),
             ROOT / 'contracts/v1/deployment.schema.json']
    return {str(p.relative_to(ROOT)): reconcile.digest_file(p) for p in files}


def units(policy):
    validate(policy)
    script = str(Path(policy['platform_root']) / 'host/activation_install.py')
    policy_hash = contract.digest(policy)
    result = activation.units(str(ADMISSION), platform_root=policy['platform_root'])
    result['hyprn-tunnel.slice'] = '''[Unit]
Description=HYPRN tunnel network boundary

[Slice]
IPAddressDeny=10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16
IPAddressAllow=127.0.0.1/32 127.0.0.53/32
'''
    result['hyprn-tunnel-credential.service'] = f'''[Unit]
Description=Load the pinned HYPRN tunnel credential
After=network-online.target
Wants=network-online.target
Before=hyprn-tunnel.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/python3 -I -B {script} credential --policy {POLICY} --approve-sha256 {policy_hash}
UMask=0077
LimitCORE=0
StandardOutput=null
StandardError=journal
'''
    result['hyprn-tunnel.service'] = f'''[Unit]
Description=HYPRN staging Cloudflare Tunnel
Requires=hyprn-tunnel-credential.service
After=hyprn-tunnel-credential.service network-online.target

[Service]
Type=simple
User={UID}
Group={UID}
Slice=hyprn-tunnel.slice
LoadCredential=tunnel-token:{TOKEN}
ExecStart=/usr/bin/cloudflared --no-autoupdate tunnel --protocol http2 --edge-ip-version 4 --metrics 127.0.0.1:20241 --loglevel warn run --token-file %d/tunnel-token
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictAddressFamilies=AF_INET AF_UNIX
LockPersonality=true
RestrictRealtime=true
MemoryMax=256M
CPUQuota=100%
TasksMax=128
LimitCORE=0
UMask=0077
StandardOutput=journal
StandardError=journal
LogRateLimitIntervalSec=30s
LogRateLimitBurst=30

[Install]
WantedBy=multi-user.target
'''
    result['hyprn-tunnel-boundary-probe.service'] = f'''[Unit]
Description=Verify HYPRN tunnel metadata denial
After=hyprn-tunnel.service

[Service]
Type=oneshot
User={UID}
Group={UID}
Slice=hyprn-tunnel.slice
ExecStart=/usr/bin/python3 -I -B {script} boundary-probe
NoNewPrivileges=true
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
RestrictAddressFamilies=AF_INET AF_UNIX
TimeoutStartSec=15
'''
    return result


def files(policy):
    result = {str(POLICY): (contract.canonical(policy), 0o600),
              str(ADMISSION): (contract.canonical(policy['activation']), 0o600)}
    result.update({str(Path('/etc/systemd/system') / name): (text.encode(), 0o644)
                   for name, text in units(policy).items()})
    return result


def plan(policy):
    policy = validate(policy)
    lock = contract.read_json(ROOT / 'host/host-packages.json')
    dependency = next(row for row in lock['packages'] if row['name'] == 'cloudflared')
    value = {'schema': 'hyprn-activation-deployment/v1', 'policy': policy,
             'sources': source_pins(), 'cloudflared': dependency,
             'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'mode': mode}
                       for name, (raw, mode) in files(policy).items()},
             'actions': ['verify-installed-closed-product-and-access-readback',
                         'create-dedicated-tunnel-user', 'install-exact-units',
                         'fetch-pinned-host-only-tunnel-token', 'start-tcp-7844-connector',
                         'verify-real-connector-and-cgroup-boundary', 'start-bounded-admission-renewal'],
             'cloud_resources_changed': False, 'new_packages': [],
             'provider_messages_sent': False, 'budget_changed': False,
             'human_acceptance': 'not-established',
             'conditional_promotion': {'activation': promoted_policy(policy),
                 'operator_checks': ['real-login', 'recorded-native-execution',
                                     'live-assistant-tools', 'validated-joint-exploration-no-reruns'],
                 'new_approval_required_if_plan_changes': True}}
    return dict(value, plan_sha256=contract.digest(value))


def promoted_policy(policy):
    return dict(policy['activation'], mode='staging', not_after=None)


def token_bytes(raw, policy):
    """The released connector's a/t/s token format; no alternate endpoint is allowed."""
    try:
        if len(raw) > 65536 or raw != raw.strip():
            raise ValueError()
        data = reconcile.decode(base64.b64decode(raw, validate=True))
        if (set(data) not in ({'a', 't', 's'}, {'a', 't', 's', 'e'})
                or data['a'] != policy['account_id'] or data['t'] != policy['tunnel_id']
                or data.get('e', '') != ''
                or len(base64.b64decode(data['s'], validate=True)) < 32):
            raise ValueError()
    except (ValueError, TypeError, KeyError):
        raise Refused('tunnel_credential_identity') from None
    return raw


def access_readback(policy, target):
    """Read the reviewed live API projection; no caller success boolean is used."""
    value = reconcile.decode(bootstrap.read_pinned(policy['access_readback']))
    expected = {'schema': 'hyprn-tunnel-readback/v1', 'account_id': policy['account_id'],
                'tunnel_id': policy['tunnel_id'], 'origin': target.runtime['external_origin'],
                'issuer': target.runtime['access']['issuer'], 'audience': target.runtime['access']['audience']}
    ingress = [{'hostname': target.runtime['external_origin'].removeprefix('https://'),
                'service': 'http://127.0.0.1:8080', 'originRequest': {'access': {
                    'required': True, 'teamName': target.runtime['access']['issuer'][8:].split('.')[0],
                    'audTag': [target.runtime['access']['audience']]}}}, {'service': 'http_status:404'}]
    if value != dict(expected, ingress=ingress):
        raise Refused('tunnel_access_readback_changed')


def target_for(policy):
    if str(ROOT) != policy['platform_root']:
        raise Refused('activation_install_platform_root')
    target = reconcile.Target(policy['activation']['binding'])
    target.protect()
    if contract.digest(target.desired) != policy['activation']['desired_sha256']:
        raise Refused('activation_install_target_changed')
    return target


def credential(policy_path, approved):
    require_root()
    policy = validate(contract.read_json(reconcile.protected(policy_path)))
    if contract.digest(policy) != approved or Path(policy_path) != POLICY:
        raise Refused('tunnel_credential_approval')
    installed_sources(policy)
    target = target_for(policy)
    reconcile.GoogleHost(target, **policy['activation']['disk']).check()
    google = bootstrap.loader.AttachedServiceAccount()
    google.preflight(SimpleNamespace(project_id=target.runtime['project_id'],
                                    project_number=target.runtime['project_number']))
    raw = token_bytes(google.fetch({'name': 'hyprn-staging-cloudflare-tunnel',
                                   'version': policy['secret_version']}), policy)
    setup.mkdir(TOKEN_ROOT, 0o700)
    fd = bootstrap.loader.private_directory(str(TOKEN_ROOT))
    try:
        bootstrap.loader.require_tmpfs(fd)
        names = os.listdir(fd)
        if names:
            if names != ['tunnel-token']:
                raise Refused('tunnel_credential_inventory')
            path = bootstrap.secure(TOKEN, private=True)
            if not hmac.compare_digest(path.read_bytes(), raw):
                raise Refused('tunnel_credential_changed')
        else:
            bootstrap.loader.write_file(fd, 'tunnel-token', raw, 0)
            os.fsync(fd)
    finally:
        os.close(fd)
    return {'credential': 'pinned-version-loaded'}


def require_root():
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise Refused('activation_install_linux_root_required')


def boundary_probe():
    # This process runs in the same IP-filtered cgroup slice and UID as cloudflared.
    if os.getuid() != UID or '/hyprn-tunnel.slice/' not in Path('/proc/self/cgroup').read_text():
        raise Refused('tunnel_probe_scope')
    with socket.create_connection(('127.0.0.1', 8080), timeout=3):
        pass
    try:
        connection = socket.create_connection(('169.254.169.254', 80), timeout=3)
    except OSError as error:
        import errno
        if error.errno not in (errno.EPERM, errno.EACCES, errno.ETIMEDOUT) and not isinstance(error, TimeoutError):
            raise Refused('tunnel_metadata_denial_unproven') from None
    else:
        connection.close()
        raise Refused('tunnel_metadata_reachable')
    return {'metadata': 'blocked-from-connector-slice', 'loopback_origin': 'reachable'}


def installed_sources(policy):
    expected = contract.read_json(reconcile.protected(STATE / 'intent.json'))
    if expected.get('policy') != policy:
        raise Refused('activation_install_intent_changed')
    for name, digest in expected['sources'].items():
        if reconcile.digest_file(reconcile.protected(ROOT / name)) != digest:
            raise Refused('activation_installed_source_changed')
    return expected


def verify(policy):
    require_root()
    expected = installed_sources(policy)
    installed_files = files(policy)
    promotion = STATE / 'promoted.json'
    if promotion.exists():
        receipt = contract.read_json(reconcile.protected(promotion))
        target = target_for(policy)
        if (receipt.get('plan_sha256') != expected['plan_sha256']
                or receipt.get('identity') != target.identity):
            raise Refused('activation_promotion_changed')
        installed_files[str(ADMISSION)] = (contract.canonical(promoted_policy(policy)), 0o600)
    for name, (raw, mode) in installed_files.items():
        path = reconcile.protected(name)
        if path.read_bytes() != raw or stat.S_IMODE(path.stat().st_mode) != mode:
            raise Refused('activation_installed_file_changed')
    executable = reconcile.protected('/usr/bin/cloudflared')
    if reconcile.digest_file(executable) != expected['cloudflared']['installed_files'][str(executable)]:
        raise Refused('tunnel_binary_changed')
    pid = int(setup.run(['/usr/bin/systemctl', 'show', '--property=MainPID', '--value', 'hyprn-tunnel.service']))
    if (pid <= 1 or Path('/proc', str(pid), 'exe').resolve() != executable
            or Path('/proc', str(pid)).stat().st_uid != UID
            or '/hyprn-tunnel.slice/' not in Path('/proc', str(pid), 'cgroup').read_text()):
        raise Refused('tunnel_process_identity')
    sockets = setup.run(['/usr/bin/ss', '--no-header', '--listening', '--tcp', '--numeric', '--processes']).decode()
    listeners = [row for row in sockets.splitlines() if len(row.split()) > 3
                 and row.split()[3] == '127.0.0.1:20241']
    if len(listeners) != 1 or ('pid=' + str(pid) + ',') not in listeners[0]:
        raise Refused('tunnel_metrics_socket_owner')
    # Positive host control distinguishes a blocked service from an absent route.
    # Connect only: no metadata request or credential is sent.
    with socket.create_connection(('169.254.169.254', 80), timeout=3):
        pass
    setup.run(['/usr/bin/systemctl', 'start', 'hyprn-tunnel-boundary-probe.service'])
    connection = http.client.HTTPConnection('127.0.0.1', 20241, timeout=5)
    try:
        connection.request('GET', '/ready')
        result = connection.getresponse()
        if result.status != 200 or len(result.read(65537)) > 65536:
            raise Refused('tunnel_not_connected')
    finally:
        connection.close()
    return {'connector': 'connected', 'origin_authentication': 'verified-separately',
            'metadata': 'blocked-from-connector-slice', 'human_login': 'not-established'}


def apply(policy_path, approved):
    require_root()
    policy = validate(contract.read_json(reconcile.protected(policy_path)))
    expected = plan(policy)
    if expected['plan_sha256'] != approved:
        raise Refused('activation_install_approval_mismatch')
    for name in expected['sources']:
        reconcile.protected(ROOT / name)
    target = target_for(policy)
    journal = reconcile.Journal(reconcile.protected(policy['activation']['journal_root'], directory=True))
    with journal.lock():
        activation.bound_state(target, policy['activation'], journal)
        activation.window(policy['activation'], int(time.time()))
        host = reconcile.GoogleHost(target, **policy['activation']['disk'])
        host.check()
        host.desired()
        activation.network(target, policy['activation'])
        activation.close(target)
        access_readback(policy, target)
        for path in files(policy):
            if Path(path).exists() or Path(path).is_symlink():
                raise Refused('activation_install_existing_file')
        setup.mkdir(STATE, 0o700)
        if list(STATE.iterdir()):
            raise Refused('activation_install_reconcile_previous_attempt')
        executable = reconcile.protected('/usr/bin/cloudflared')
        if reconcile.digest_file(executable) != expected['cloudflared']['installed_files'][str(executable)]:
            raise Refused('tunnel_binary_changed')
        for lookup in (pwd.getpwnam, pwd.getpwuid, grp.getgrnam, grp.getgrgid):
            try:
                lookup(NAME if lookup in (pwd.getpwnam, grp.getgrnam) else UID)
            except KeyError:
                pass
            else:
                raise Refused('tunnel_user_already_exists')
        reconcile.atomic(STATE / 'intent.json', expected)
        setup.run(['/usr/sbin/groupadd', '--system', '--gid', str(UID), NAME])
        setup.run(['/usr/sbin/useradd', '--system', '--uid', str(UID), '--gid', str(UID),
                   '--home-dir', '/nonexistent', '--shell', '/usr/sbin/nologin', '--no-create-home', NAME])
        for name, (raw, mode) in files(policy).items():
            setup.write_new(name, raw, mode)
        unit_paths = [str(Path('/etc/systemd/system') / name) for name in units(policy)]
        setup.run(['/usr/bin/systemd-analyze', 'verify', *unit_paths])
        setup.run(['/usr/bin/systemctl', 'daemon-reload'])
        setup.run(['/usr/bin/systemctl', 'enable', 'hyprn-tunnel.service'])
        setup.run(['/usr/bin/systemctl', 'start', 'hyprn-tunnel.service'])
        deadline = time.monotonic() + 60
        while True:
            try:
                result = verify(policy)
                break
            except (Refused, OSError, http.client.HTTPException):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)
        reconcile.atomic(STATE / 'installed.json', {'plan_sha256': approved, **result})
    # The renewer takes this same lock; start it only after releasing the installer.
    setup.run(['/usr/bin/systemctl', 'enable', '--now', 'hyprn-qualification-access.timer'])
    return {'installed': True, 'admission': 'pending-fresh-renewal', **result}


def promote(policy_path, approved):
    """Reviewed operator action after real checks; never claim human acceptance."""
    require_root()
    policy = validate(contract.read_json(reconcile.protected(policy_path)))
    expected = installed_sources(policy)
    if approved != expected['plan_sha256'] or expected != plan(policy):
        raise Refused('activation_promotion_approval')
    if (STATE / 'promoted.json').exists():
        raise Refused('activation_promotion_reconcile_previous_attempt')
    if contract.read_json(reconcile.protected(ADMISSION)) != policy['activation']:
        raise Refused('activation_promotion_window_changed')
    target = target_for(policy)
    verify(policy)
    # This checks machine prerequisites only. The authorized operator runs this
    # command after the real public-boundary checklist in the approved plan.
    activation.renew(str(ADMISSION))
    journal = reconcile.Journal(reconcile.protected(policy['activation']['journal_root'], directory=True))
    with journal.lock():
        activation.bound_state(target, policy['activation'], journal)
        reconcile.atomic(STATE / 'promoted.json', {'plan_sha256': approved,
            'identity': target.identity, 'recorded_at': int(time.time()),
            'human_acceptance': 'not-established'})
        reconcile.atomic(ADMISSION, promoted_policy(policy))
    result = activation.renew(str(ADMISSION))
    return {'promotion': 'reviewed-staging-operation', **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'apply', 'credential', 'verify', 'boundary-probe', 'promote'))
    parser.add_argument('--policy')
    parser.add_argument('--approve-sha256')
    args = parser.parse_args()
    try:
        if args.operation == 'boundary-probe':
            result = boundary_probe()
        elif args.operation == 'plan':
            result = plan(contract.read_json(args.policy))
        elif args.operation == 'credential':
            result = credential(args.policy, args.approve_sha256)
        elif args.operation == 'apply':
            result = apply(args.policy, args.approve_sha256)
        elif args.operation == 'promote':
            result = promote(args.policy, args.approve_sha256)
        else:
            result = verify(validate(contract.read_json(reconcile.protected(args.policy))))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({'status': 'refused', 'reason_code': getattr(error, 'reason', 'activation_install_refused')}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
