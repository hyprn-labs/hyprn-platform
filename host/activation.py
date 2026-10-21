"""Renew bounded, reviewed staging qualification access from fresh host observations.

This is not human acceptance or proof of a scientific user journey. It never
starts containers, attests a worker, sends a provider message or expands budget.
"""
import argparse
import http.client
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bootstrap

contract, reconcile = bootstrap.contract, bootstrap.reconcile
Refused = reconcile.Refused
FIELDS = {'schema', 'binding', 'desired_sha256', 'journal_root', 'disk',
          'network_policy', 'mode', 'not_before', 'not_after'}
LEASE_SECONDS = 240


def validate_policy(value):
    if (not bootstrap.exact_fields(value, FIELDS)
            or value['schema'] != 'hyprn-qualification-access/v1'
            or not all(bootstrap.absolute(value[k]) for k in ('binding', 'journal_root'))
            or not bootstrap.sha(value['desired_sha256'])
            or type(value['not_before']) is not int or value['not_before'] < 0
            or value['mode'] not in ('qualification', 'staging')):
        raise Refused('activation_policy')
    if ((value['mode'] == 'qualification' and
            (type(value['not_after']) is not int
             or not 0 < value['not_after'] - value['not_before'] <= 86400))
            or (value['mode'] == 'staging' and value['not_after'] is not None)):
        raise Refused('activation_window_policy')
    network = value['network_policy']
    if (not bootstrap.exact_fields(network, {'path', 'sha256'})
            or not bootstrap.absolute(network['path']) or not bootstrap.sha(network['sha256'])
            or not bootstrap.exact_fields(value['disk'], {'disk_name', 'device_name', 'retired_hosts'})):
        raise Refused('activation_policy')
    return value


def load_policy(path):
    return validate_policy(contract.read_json(reconcile.protected(path)))


def window(policy, now):
    if now < policy['not_before'] or (policy['not_after'] is not None and now >= policy['not_after']):
        raise Refused('activation_window_closed')


def bound_state(target, policy, journal):
    target.protect()
    if str(target.path) != policy['binding'] or contract.digest(target.desired) != policy['desired_sha256']:
        raise Refused('activation_target_changed')
    previous = journal.read()
    if (previous is None or previous['stage'] != 'installed_closed'
            or previous['sequence'] != target.desired['sequence']
            or previous['desired_sha256'] != policy['desired_sha256']
            or previous['installed'] != {**target.identity, 'binding_sha256': target.binding_sha256}):
        raise Refused('activation_installation_unproven')
    identity = contract.read_json(reconcile.protected(Path(target.binding['control_root']) / 'runtime-identity.json'))
    if identity != target.identity:
        raise Refused('activation_identity_changed')


def command(arguments, *, timeout=30):
    return reconcile.bounded(arguments, timeout=timeout)


def check_container(actual, expected, project, service, image):
    """Compare engine observations with the renderer, including capabilities and mounts."""
    config, host, state = actual['Config'], actual['HostConfig'], actual['State']
    if (state.get('Status') != 'running' or state.get('Paused') or state.get('Restarting')
            or actual['Image'] != image['Id'] or config.get('Image') != expected['image']
            or config.get('Labels', {}).get('com.docker.compose.project') != project
            or config.get('Labels', {}).get('com.docker.compose.service') != service
            or config.get('User') != expected['user']
            or not host.get('ReadonlyRootfs') or host.get('Privileged')
            or sorted(host.get('CapDrop') or []) != ['ALL'] or host.get('CapAdd')
            or host.get('SecurityOpt') != ['no-new-privileges:true']
            or host.get('Memory') != 2 * 1024**3 or host.get('NanoCpus') != 1000000000
            or host.get('PidsLimit') != expected['pids_limit']
            or host.get('PidMode') or host.get('UTSMode') or host.get('IpcMode') != 'private'
            or host.get('Devices') or host.get('Init') is not True
            or host.get('Tmpfs') != {'/tmp': expected['tmpfs'][0].split(':', 1)[1]}
            or host.get('Ulimits') != [{'Name': 'core', 'Hard': 0, 'Soft': 0}]):
        raise Refused('activation_container_changed')
    for field, docker_field in (('entrypoint', 'Entrypoint'), ('command', 'Cmd')):
        wanted = expected.get(field, image['Config'].get(docker_field))
        if (config.get(docker_field) or []) != (wanted or []):
            raise Refused('activation_container_command_changed')
    environment = dict(item.split('=', 1) for item in config.get('Env', []))
    wanted = dict(item.split('=', 1) for item in image['Config'].get('Env', []))
    wanted.update(expected['environment'])
    if environment != wanted:
        raise Refused('activation_container_environment_changed')
    mounts = {item['Destination']: (item['Type'], item.get('Source'), item['RW'])
              for item in actual['Mounts'] if item['Type'] != 'tmpfs'}
    wanted = {item['target']: ('bind', item['source'], not item.get('read_only', False))
              for item in expected['volumes']}
    if mounts != wanted:
        raise Refused('activation_container_mount_changed')
    networks = actual['NetworkSettings']['Networks']
    wanted = {project + '_' + name: value['ipv4_address'] for name, value in expected['networks'].items()}
    if set(networks) != set(wanted) or any(networks[key]['IPAddress'] != ip for key, ip in wanted.items()):
        raise Refused('activation_container_network_changed')
    ports = host.get('PortBindings') or {}
    wanted = {'8000/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]} if service == 'app' else {}
    if ports != wanted:
        raise Refused('activation_container_ports_changed')


def containers(target):
    project = target.runtime['installation_id']
    raw = command(['docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + project])
    ids = raw.decode().split()
    if len(ids) != 3:
        raise Refused('activation_container_inventory_changed')
    rows = reconcile.decode(command(['docker', 'inspect', *ids]))
    found = {}
    for row in rows:
        service = row['Config'].get('Labels', {}).get('com.docker.compose.service')
        if service not in ('app', 'modeling', 'dispatcher') or service in found:
            raise Refused('activation_container_inventory_changed')
        expected = target.preview['compose']['services'][service]
        image = reconcile.decode(command(['docker', 'image', 'inspect', expected['image']]))
        if len(image) != 1 or expected['image'] not in image[0].get('RepoDigests', []):
            raise Refused('activation_image_pin_changed')
        check_container(row, expected, project, service, image[0])
        found[service] = row['Id']
    return found


NATIVE_PROBE = '''import json,sys
from pathlib import Path
source,binding=sys.argv[1:]
sys.path[:0]=[str(Path(source)/p) for p in ('deployment','application/src','integration/src')]
from cloud_lifecycle import Lifecycle,binding as load_binding
owner=Lifecycle(load_binding(binding,'inspect'),120)
owner.identity_check()
actual=owner.native('check')
process=owner.native_process()
if process is None or process['owner'] != actual:
    raise RuntimeError('native_owner_not_running')
print(json.dumps({'owner':actual,'container_id':process['container_id']}))
'''


def native(target, dispatcher_id):
    # The immutable archive verifier checks every installed byte before importing
    # the product's fixed lifecycle probe. The probe checks, never re-attests.
    product = bootstrap.prepared_product(target, install=False)
    product.preflight()
    source = target.preview['execution']['configuration']['source']
    result = reconcile.decode(command([product.python, '-I', '-B', '-c', NATIVE_PROBE,
                                       source, str(target.path)], timeout=130))
    owner = contract.read_json(reconcile.protected(Path(target.binding['control_root']) / 'native-owner.json'))
    if result != {'owner': owner, 'container_id': dispatcher_id}:
        raise Refused('activation_native_owner_changed')


def ingress(target):
    # Uvicorn only serves after Assistant continuity startup has completed.
    # Missing/malformed assertions must never reach a product session, including
    # while admission is open. This does not impersonate an allowed user.
    for headers in ({}, {'Cf-Access-Jwt-Assertion': 'not-a-signed-assertion'}):
        connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=5)
        try:
            connection.request('GET', '/api/1/session/mode', headers={
                'Host': target.runtime['external_origin'].removeprefix('https://'), **headers})
            response = connection.getresponse()
            body = response.read(65537)
            if response.status != 401 or len(body) > 65536 or response.getheader('Location'):
                raise Refused('activation_origin_authentication_failed')
        finally:
            connection.close()


def network(target, policy):
    value = reconcile.decode(bootstrap.read_pinned(policy['network_policy']))
    if (value.get('installation_id') != target.runtime['installation_id']
            or value.get('network') != target.preview['network_policy']):
        raise Refused('activation_network_policy_changed')
    # Installed host module, protected alongside this entry point. The operation
    # observes root files, engine networks and kernel enforcement; it cannot apply.
    module = bootstrap.sibling('service_network_install')
    module.verify_live(value)


def close(target):
    root = Path(target.binding['control_root'])
    if contract.read_json(reconcile.protected(root / 'runtime-identity.json')) == target.identity:
        reconcile.atomic(root / 'admission.json', dict(schema='hyprn-admission/v1',
            **target.identity, browser=False, scientific=False, expires_at=0), mode=0o644)


def renew(path):
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise Refused('activation_linux_root_required')
    policy = load_policy(path)
    target = reconcile.Target(policy['binding'])
    target.protect()
    for name in ('activation', 'bootstrap', 'reconcile', 'contract', 'service_network_install'):
        reconcile.protected(Path(__file__).parent / (name + '.py'))
    journal = reconcile.Journal(reconcile.protected(policy['journal_root'], directory=True))
    # A concurrent deploy holds the same lock and closes its own admission. An
    # activation attempt must not overwrite that newer release's control record.
    with journal.lock():
        try:
            started = time.monotonic()
            window(policy, int(time.time()))
            bound_state(target, policy, journal)
            host = reconcile.GoogleHost(target, **policy['disk'])
            fence = host.check()
            generation = host.desired()
            network(target, policy)
            running = containers(target)
            native(target, running['dispatcher'])
            ingress(target)
            connector = bootstrap.sibling('activation_install')
            installed = connector.validate(contract.read_json(reconcile.protected(connector.POLICY)))
            expected_policy = (installed['activation'] if policy['mode'] == 'qualification'
                               else connector.promoted_policy(installed))
            if expected_policy != policy:
                raise Refused('activation_connector_policy_changed')
            connector.verify(installed)
            if time.monotonic() - started > 180:
                raise Refused('activation_observation_expired')
            window(policy, int(time.time()))
            if (load_policy(path) != policy or host.check() != fence
                    or host.desired() != generation):
                raise Refused('activation_authority_changed')
            bound_state(target, policy, journal)
            expires = int(time.time()) + LEASE_SECONDS
            if policy['not_after'] is not None:
                expires = min(expires, policy['not_after'])
            reconcile.atomic(Path(target.binding['control_root']) / 'admission.json',
                dict(schema='hyprn-admission/v1', **target.identity,
                     browser=True, scientific=True, expires_at=expires), mode=0o644)
            return {'schema': 'hyprn-qualification-access-result/v1', 'identity': target.identity,
                    'expires_at': expires, 'mode': policy['mode'],
                    'human_acceptance': 'not-established', 'user_journeys': 'not-established'}
        except BaseException:
            close(target)
            raise


def units(policy_path, *, platform_root=None):
    if not bootstrap.absolute(policy_path) or any(c.isspace() or c in '%"\\' for c in policy_path):
        raise Refused('activation_unit_path')
    executable = (str(Path(__file__).resolve()) if platform_root is None
                  else str(Path(platform_root) / 'host/activation.py'))
    if any(c.isspace() or c in '%"\\' for c in executable):
        raise Refused('activation_unit_path')
    return {'hyprn-qualification-access.service': f'''[Unit]
Description=HYPRN bounded qualification access
After=docker.service hyprn-egress.service hyprn-service-network.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -I -B {executable} --policy {policy_path}
TimeoutStartSec=210
UMask=0077
''', 'hyprn-qualification-access.timer': '''[Unit]
Description=Renew HYPRN qualification access

[Timer]
OnActiveSec=1
OnUnitInactiveSec=30
AccuracySec=1
Unit=hyprn-qualification-access.service

[Install]
WantedBy=timers.target
'''}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(renew(args.policy), sort_keys=True))
        return 0
    except Exception as error:
        reason = error.reason if isinstance(error, Refused) else 'activation_refused'
        print(json.dumps({'status': 'refused', 'reason_code': reason}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
