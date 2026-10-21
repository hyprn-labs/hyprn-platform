"""Read-only prerequisites for closed Debian 12 backend bootstrap.

This observes the host, never provisions it. A structural firewall observation
cannot qualify container containment or Cloudflare/remote OAuth admission. Those
remain explicit activation blockers even when closed bootstrap is ready.
"""
import grp
import hashlib
import ipaddress
import os
from pathlib import Path
import platform
import pwd
import re
import shlex
import stat
import sys

import reconcile

DOCKER = '/usr/bin/docker'
COMPOSE_PATHS = {prefix + '/docker/cli-plugins/docker-compose'
                 for prefix in ('/usr/lib', '/usr/libexec', '/usr/local/lib', '/usr/local/libexec')}
UTILITIES = ('/usr/bin/bash', '/usr/bin/ps', '/usr/bin/tail', '/usr/bin/whoami',
             '/usr/bin/findmnt', '/usr/bin/systemctl', '/usr/bin/ss',
             '/usr/sbin/iptables', '/usr/sbin/iptables-save')
BLOCKERS = ('live_container_network_probe_required', 'cloudflare_connector_activation_required',
            'loopback_origin_route_required', 'external_access_and_oauth_qualification_required',
            'execution_host_attestation_required')


def refuse(reason):
    raise reconcile.Refused(reason)


def tool(path, expected_sha256=None):
    """Debian alternatives may be root-owned links to protected system binaries."""
    path = Path(path)
    try:
        reconcile.protected(path.parent, directory=True)
        if path.lstat().st_uid != 0:
            refuse('host_tool_authority')
        real = reconcile.protected(path.resolve(strict=True))
        info = real.stat()
        if info.st_nlink < 1 or not info.st_mode & 0o111:
            refuse('host_tool_not_executable')
        digest = reconcile.digest_file(real)
        if expected_sha256 is not None and digest != expected_sha256:
            refuse('host_tool_pin_mismatch')
        return digest
    except (OSError, RuntimeError):
        refuse('host_tool_missing')


def observe(command, reason):
    try:
        return reconcile.bounded(command, timeout=20)
    except (reconcile.Refused, OSError):
        refuse(reason)


def policy_at(target, path):
    reconcile.protected(path)
    value = reconcile.contract.read_json(path)
    if (not isinstance(value, dict) or set(value) != {'schema', 'identity', 'desired_sha256',
            'docker', 'compose', 'database_ca_source'} or value['schema'] != 'hyprn-host-preflight/v1'
            or value['identity'] != target.identity
            or value['desired_sha256'] != reconcile.contract.digest(target.desired)):
        refuse('host_preflight_policy_binding')
    for name in ('docker', 'compose'):
        pin = value[name]
        if (not isinstance(pin, dict) or set(pin) != {'sha256', 'version'}
                or not isinstance(pin['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', pin['sha256'])
                or not isinstance(pin['version'], str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+~.][A-Za-z0-9.+~_-]+)?', pin['version'])):
            refuse('host_tool_policy')
    if value['compose']['version'].split('.')[0] not in ('2', '5'):
        refuse('compose_plugin_required')
    if not isinstance(value['database_ca_source'], str) or not Path(value['database_ca_source']).is_absolute():
        refuse('database_ca_source_required')
    return value


def operating_system():
    if sys.platform != 'linux' or os.geteuid() != 0:
        refuse('linux_root_required')
    if platform.machine() != 'x86_64':
        refuse('linux_amd64_required')
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        refuse('debian12_required')
    if release.get('ID') != 'debian' or release.get('VERSION_ID') != '12':
        refuse('debian12_required')
    if not Path('/run/systemd/system').is_dir():
        refuse('systemd_required')
    for path in UTILITIES:
        tool(path)
    for unit in ('docker.service', 'docker.socket'):
        state = observe(['/usr/bin/systemctl', 'show', '--property=ActiveState', '--value', unit],
                        'docker_systemd_unavailable').decode().strip()
        if state != 'active':
            refuse('docker_systemd_inactive')


def docker_observation(target, policy):
    digest = tool(DOCKER, policy['docker']['sha256'])
    endpoint = target.runtime['execution_host']['docker_endpoint']
    if not endpoint.startswith('unix:///'):
        refuse('docker_unix_endpoint_required')
    path = Path(endpoint.removeprefix('unix://'))
    try:
        # A /var/run alias conflicts with the product's native no-link rule;
        # select the canonical /run endpoint in reviewed runtime configuration.
        if any(part.is_symlink() for part in (path, *path.parents)):
            refuse('docker_canonical_socket_required')
        reconcile.protected(path.parent, directory=True)
        info = path.lstat()
        if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0 or info.st_gid == 0
                or stat.S_IMODE(info.st_mode) != 0o660):
            refuse('docker_socket_authority')
    except OSError:
        refuse('docker_socket_missing')
    prefix = [DOCKER, '--host', endpoint]
    observed = reconcile.decode(observe(prefix + ['info', '--format', '{{json .}}'], 'docker_daemon_unavailable'))
    required = {'OSType': 'linux', 'Architecture': 'x86_64', 'CgroupVersion': '2',
                'ServerVersion': policy['docker']['version'], 'LiveRestoreEnabled': False, 'IPv4Forwarding': True,
                'MemoryLimit': True, 'CpuCfsPeriod': True, 'CpuCfsQuota': True, 'PidsLimit': True}
    if (not isinstance(observed, dict) or any(observed.get(key) != value or
            type(observed.get(key)) is not type(value) for key, value in required.items())
            or not isinstance(observed.get('Swarm'), dict)
            or observed['Swarm'].get('LocalNodeState') != 'inactive'):
        refuse('docker_runtime_prerequisites')
    security = observed.get('SecurityOptions')
    if (not isinstance(security, list) or 'name=seccomp,profile=builtin' not in security
            or any(not isinstance(item, str) or 'rootless' in item for item in security)):
        refuse('docker_seccomp_required')
    client = observed.get('ClientInfo')
    plugins = client.get('Plugins') if isinstance(client, dict) else None
    if not isinstance(plugins, list) or any(not isinstance(plugin, dict) for plugin in plugins):
        refuse('compose_v2_missing')
    compose = [plugin for plugin in plugins if plugin.get('Name') == 'compose']
    if (len(compose) != 1 or compose[0].get('Path') not in COMPOSE_PATHS
            or compose[0].get('Version') != 'v' + policy['compose']['version']):
        refuse('compose_v2_pin_mismatch')
    tool(compose[0]['Path'], policy['compose']['sha256'])
    version = observe(prefix + ['compose', 'version', '--short'], 'compose_v2_unavailable').decode().strip()
    if version.removeprefix('v') != policy['compose']['version']:
        refuse('compose_v2_pin_mismatch')
    return dict(path=DOCKER, sha256=digest, version=observed['ServerVersion'], endpoint=endpoint,
                socket_gid=info.st_gid)


def owners_and_paths(target, docker):
    runtime = target.runtime
    users = {}
    for owner, uid in runtime['service_users'].items():
        try:
            user = pwd.getpwuid(uid)
        except KeyError:
            # Container-only numeric UIDs need no host login account. The native
            # execution owner uses whoami/pwd and therefore must actually exist.
            if owner == 'execution':
                refuse('native_service_account_missing')
            continue
        if user.pw_uid != uid or uid == 0:
            refuse('service_account_identity')
        users[owner] = user
    native_uid = runtime['service_users']['execution']
    try:
        group = grp.getgrgid(native_uid)
    except KeyError:
        refuse('native_service_group_missing')
    if users['execution'].pw_gid != native_uid or group.gr_gid != native_uid:
        refuse('native_service_account_identity')
    try:
        docker_group = grp.getgrgid(docker['socket_gid'])
    except KeyError:
        refuse('docker_socket_group_missing')
    if any(name in users and users[name].pw_name in docker_group.gr_mem for name in ('app', 'modeling', 'worker')):
        refuse('untrusted_owner_has_docker_group')
    for area, owner in (('application', 'app'), ('modeling', 'modeling'), ('execution', 'execution')):
        path = Path(runtime['mounts'][area])
        if any(part.is_symlink() for part in (path, *path.parents)):
            refuse('store_path_linked')
        try:
            info = path.lstat()
        except OSError:
            refuse('store_path_missing')
        uid = runtime['service_users'][owner]
        if (not stat.S_ISDIR(info.st_mode) or (info.st_uid, info.st_gid) != (uid, uid)
                or stat.S_IMODE(info.st_mode) != 0o700):
            refuse('store_path_ownership')
    home = Path(runtime['execution_host']['host_home'])
    execution = Path(runtime['mounts']['execution'])
    if (home == execution or execution not in home.parents or
            not Path(users['execution'].pw_dir).is_absolute()
            or users['execution'].pw_dir in ('/', '/root')
            or any(p.is_symlink() for p in (home, *home.parents))):
        refuse('native_home_identity')
    try:
        info = home.lstat()
        uid = users['execution'].pw_uid
        if (not stat.S_ISDIR(info.st_mode) or (info.st_uid, info.st_gid) != (uid, uid)
                or stat.S_IMODE(info.st_mode) != 0o700):
            refuse('native_home_ownership')
    except FileNotFoundError:
        # Initial product initialization requires an empty execution root. Its
        # configured containment-probe home must not be precreated here.
        pass
    except OSError:
        refuse('native_home_unavailable')
    root = reconcile._secret_loader.private_directory(runtime['mounts']['secrets'])
    try:
        reconcile._secret_loader.require_tmpfs(root)
    finally:
        os.close(root)


def firewall_structure(raw):
    """Minimum forwarding structure only; never a containment proof or receipt."""
    rules = []
    try:
        for line in raw.decode().splitlines():
            if line.startswith('-A '):
                rules.append(shlex.split(line))
    except (UnicodeError, ValueError):
        refuse('firewall_observation_invalid')
    forward = [rule[2:] for rule in rules if rule[1] == 'FORWARD']
    user = [rule[2:] for rule in rules if rule[1] == 'DOCKER-USER']
    if not forward or forward[0] != ['-j', 'DOCKER-USER']:
        refuse('docker_forward_guard_missing')
    if not user or user[0] != ['-d', '169.254.169.254/32', '-j', 'DROP']:
        refuse('container_metadata_drop_missing')
    if len(user) < 2 or user[-1] != ['-j', 'DROP']:
        refuse('container_default_deny_missing')
    for rule in user[1:-1]:
        if rule in (['-j', 'ACCEPT'], ['-j', 'RETURN']):
            refuse('container_unconditional_bypass')
    return hashlib.sha256(raw).hexdigest()


def ipv6_values():
    knobs = list(Path('/proc/sys/net/ipv6/conf').glob('*/disable_ipv6'))
    if not knobs or not {'all', 'default'} <= {path.parent.name for path in knobs}:
        refuse('ipv6_disable_observation_missing')
    return {path.parent.name: path.read_text().strip() for path in knobs}


def ipv6_observation():
    values = ipv6_values()
    enabled = sorted(name for name, value in values.items() if value != '1')
    if enabled:
        error = reconcile.Refused('ipv6_must_be_disabled')
        error.diagnostic = {'stage': 'host_ipv6_check', 'interfaces': enabled}
        raise error


def tcp_listeners():
    raw = observe(['/usr/bin/ss', '--no-header', '--listening', '--tcp', '--numeric'],
                  'host_listener_observation_unavailable')
    try:
        result = []
        for line in raw.decode().splitlines():
            address, port = line.split()[3].rsplit(':', 1)
            address = address.strip('[]').split('%', 1)[0]
            if address != '*':
                ipaddress.ip_address(address)
            result.append((address, int(port)))
        return result
    except (UnicodeError, ValueError, IndexError):
        refuse('host_listener_observation_invalid')


def check_listener(address, port):
    if port in (2375, 2376):
        refuse('docker_tcp_listener_forbidden')
    if port != 22 and (address == '*' or not ipaddress.ip_address(address).is_loopback):
        error = reconcile.Refused('unexpected_public_listener')
        error.diagnostic = {'stage': 'host_network_listener_check',
                            'address': address, 'port': port}
        raise error


def network_observation():
    version = observe(['/usr/sbin/iptables', '--version'], 'iptables_nft_required').decode()
    if '(nf_tables)' not in version:
        refuse('iptables_nft_required')
    raw = observe(['/usr/sbin/iptables-save', '-t', 'filter'], 'firewall_observation_unavailable')
    digest = firewall_structure(raw)
    ipv6_observation()
    for address, port in tcp_listeners():
        check_listener(address, port)
    return dict(backend='iptables-nft', observed_rules_sha256=digest, ipv6='disabled',
                assurance='minimum-structure-only', live_container_probe=False)


def check(target, policy_path, *, host):
    """Called under bootstrap's deployment lock; no caller success receipt is used."""
    target.protect()
    policy = policy_at(target, policy_path)
    operating_system()
    # The real GoogleHost checks metadata/Compute identities and every actual
    # kernel store mount. Local stat or a caller boolean cannot replace it.
    fence = host.check()
    docker = docker_observation(target, policy)
    owners_and_paths(target, docker)
    try:
        ca = reconcile.protected(policy['database_ca_source'])
        if reconcile.digest_file(ca) != target.runtime['database']['ca_sha256']:
            refuse('database_ca_source_mismatch')
    except OSError:
        refuse('database_ca_source_unavailable')
    network = network_observation()
    target.unchanged()
    connector_present = any(Path(path).is_file() for path in ('/usr/bin/cloudflared', '/usr/local/bin/cloudflared'))
    return dict(schema='hyprn-host-preflight/v1', identity=target.identity,
                bootstrap_ready=True, admission_ready=False, network_containment_qualified=False,
                docker=docker, host_fence=fence, firewall=network,
                cloudflare_connector='present-unqualified' if connector_present else 'not-installed',
                admission_blockers=list(BLOCKERS))
