"""Qualification access has bounded authority and uses real observation adapters."""
import copy
import io
from contextlib import ExitStack, contextmanager
import importlib.util
import json
from pathlib import Path
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('activation_subject', ROOT / 'host/activation.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'schema': 'hyprn-qualification-access/v1', 'binding': '/host/binding.json',
            'desired_sha256': 'a' * 64, 'journal_root': '/host/journal',
            'disk': {'disk_name': 'test-data', 'device_name': 'test-data', 'retired_hosts': []},
            'network_policy': {'path': '/host/network.json', 'sha256': 'b' * 64},
            'mode': 'qualification', 'not_before': 1000, 'not_after': 8200}

    def test_observations_log_only_fixed_phase_duration_and_outcome(self):
        stream = io.StringIO()
        with patch.object(subject.sys, 'stderr', stream):
            self.assertEqual(subject.observe('network', lambda: 7), 7)
            with self.assertRaisesRegex(ValueError, 'private detail'):
                subject.observe('native', lambda: (_ for _ in ()).throw(ValueError('private detail')))
        rows = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual([row['outcome'] for row in rows], ['ok', 'failed'])
        self.assertTrue(all(set(row) == {'event', 'phase', 'duration_ms', 'outcome'} for row in rows))
        self.assertNotIn('private detail', stream.getvalue())

    def test_native_renewal_verifies_installed_bytes_without_rehashing_delivery_images(self):
        target = SimpleNamespace(path=Path('/host/binding.json'),
            binding={'control_root': '/host/control'},
            preview={'execution': {'configuration': {'source': '/host/source'}}})
        product = SimpleNamespace(python='/host/python',
            preflight=lambda: self.fail('Delivery archives belong to installation verification'))
        owner = {'release': 'pinned'}
        with patch.object(subject.bootstrap, 'prepared_product', return_value=product) as prepared, \
                patch.object(subject, 'command', return_value=json.dumps({
                    'owner': owner, 'container_id': 'dispatcher'}).encode()), \
                patch.object(subject.reconcile, 'protected', side_effect=lambda path: path), \
                patch.object(subject.contract, 'read_json', return_value=owner):
            subject.native(target, 'dispatcher')
            prepared.assert_called_once_with(target, install=False)
        with patch.object(subject.bootstrap, 'prepared_product', side_effect=subject.Refused('changed')), \
                patch.object(subject, 'command') as probe, self.assertRaises(subject.Refused):
            subject.native(target, 'dispatcher')
        probe.assert_not_called()

    def test_no_arbitrary_success_receipts_or_executable_hooks(self):
        subject.validate_policy(self.policy)
        for field in ('qualified', 'accepted', 'command', 'checks', 'assistant_budget'):
            with self.subTest(field=field), self.assertRaises(subject.Refused):
                subject.validate_policy(dict(self.policy, **{field: True}))

    def test_window_cannot_be_indefinite_or_represented_by_boolean(self):
        for end in (1000, 999, 87401, True, '8200'):
            with self.subTest(end=end), self.assertRaises(subject.Refused):
                subject.validate_policy(dict(self.policy, not_after=end))
        subject.window(self.policy, 1000)
        subject.window(self.policy, 8199)
        for now in (999, 8200):
            with self.assertRaises(subject.Refused):
                subject.window(self.policy, now)

    def test_service_is_a_bounded_one_shot_with_expiring_lease(self):
        units = subject.units('/etc/hyprn/qualification.json')
        self.assertIn('TimeoutStartSec=210', units['hyprn-qualification-access.service'])
        self.assertIn('OnUnitInactiveSec=30', units['hyprn-qualification-access.timer'])
        self.assertLessEqual(subject.LEASE_SECONDS, 300)
        for path in ('relative.json', '/tmp/a b', '/tmp/%n', '/tmp/"bad'):
            with self.assertRaises(subject.Refused):
                subject.units(path)

    def container(self):
        expected = {'image': 'registry/app@sha256:' + 'a' * 64, 'user': '10002:10002',
            'pids_limit': 256, 'tmpfs': ['/tmp:rw,noexec,nosuid,nodev,size=134217728'], 'environment': {'SAFE': 'value'},
            'volumes': [{'source': '/data', 'target': '/store'}],
            'networks': {'application': {'ipv4_address': '172.29.81.2'}}}
        image = {'Id': 'sha256:' + 'b' * 64,
                 'Config': {'Entrypoint': ['python'], 'Cmd': ['app'], 'Env': ['PATH=/bin']}}
        actual = {'Id': 'c' * 64, 'Image': image['Id'],
            'Config': {'Image': expected['image'], 'User': expected['user'],
                'Labels': {'com.docker.compose.project': 'test', 'com.docker.compose.service': 'app'},
                'Entrypoint': ['python'], 'Cmd': ['app'], 'Env': ['PATH=/bin', 'SAFE=value']},
            'State': {'Status': 'running', 'Paused': False, 'Restarting': False},
            'HostConfig': {'ReadonlyRootfs': True, 'Privileged': False, 'CapDrop': ['ALL'],
                'CapAdd': [], 'SecurityOpt': ['no-new-privileges:true'], 'Memory': 2 * 1024**3,
                'NanoCpus': 1000000000, 'PidsLimit': 256, 'PidMode': '', 'IpcMode': 'private',
                'Devices': [], 'Init': True, 'Tmpfs': {'/tmp': 'rw,noexec,nosuid,nodev,size=134217728'},
                'Ulimits': [{'Name': 'core', 'Hard': 0, 'Soft': 0}], 'PortBindings': {'8000/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]}},
            'Mounts': [{'Type': 'bind', 'Source': '/data', 'Destination': '/store', 'RW': True}],
            'NetworkSettings': {'Networks': {'test_application': {'IPAddress': '172.29.81.2'}}}}
        return expected, image, actual

    def test_container_is_checked_against_real_engine_fields(self):
        expected, image, actual = self.container()
        subject.check_container(actual, expected, 'test', 'app', image)
        mutations = [('State', 'Status', 'exited'), ('Config', 'Image', 'latest'),
            ('Config', 'User', 'root'), ('HostConfig', 'Privileged', True),
            ('HostConfig', 'CapAdd', ['SYS_ADMIN']), ('HostConfig', 'ReadonlyRootfs', False),
            ('HostConfig', 'NanoCpus', 0), ('HostConfig', 'PidMode', 'host'),
            ('HostConfig', 'IpcMode', 'container:foreign'), ('HostConfig', 'UTSMode', 'host'),
            ('HostConfig', 'Init', False), ('HostConfig', 'Tmpfs', {'/tmp': 'rw,exec'}),
            ('Config', 'Env', ['PATH=/bin', 'SAFE=value', 'SECRET=unexpected']),
            ('Config', 'Cmd', ['other']), ('HostConfig', 'PortBindings', {
                '8000/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]})]
        for section, field, value in mutations:
            wrong = copy.deepcopy(actual)
            wrong[section][field] = value
            with self.subTest(field=field), self.assertRaises(subject.Refused):
                subject.check_container(wrong, expected, 'test', 'app', image)

    def test_every_rendered_scratch_mount_must_match_engine_observation(self):
        expected, image, actual = self.container()
        mount = '/native/tmp:rw,noexec,nosuid,nodev,size=33554432,uid=10001,gid=10001,mode=0700'
        expected['tmpfs'].append(mount)
        with self.assertRaises(subject.Refused):
            subject.check_container(actual, expected, 'test', 'app', image)
        path, options = mount.split(':', 1)
        actual['HostConfig']['Tmpfs'][path] = options
        subject.check_container(actual, expected, 'test', 'app', image)
        for changed in (options.replace('noexec,', ''), options.replace('10001', '0')):
            actual['HostConfig']['Tmpfs'][path] = changed
            with self.assertRaises(subject.Refused):
                subject.check_container(actual, expected, 'test', 'app', image)

    def test_mount_and_network_drift_is_refused(self):
        expected, image, actual = self.container()
        actual['Mounts'].append({'Type': 'bind', 'Source': '/var/run/docker.sock',
                                 'Destination': '/engine', 'RW': True})
        with self.assertRaises(subject.Refused):
            subject.check_container(actual, expected, 'test', 'app', image)
        actual['Mounts'].pop()
        actual['NetworkSettings']['Networks']['test_application']['IPAddress'] = '172.29.81.3'
        with self.assertRaises(subject.Refused):
            subject.check_container(actual, expected, 'test', 'app', image)

    def test_network_receipt_must_match_rendered_target_before_observer(self):
        target = SimpleNamespace(runtime={'installation_id': 'test'}, preview={'network_policy': {'a': 1}})
        value = {'installation_id': 'wrong', 'network': {'a': 1}}
        with patch.object(subject.bootstrap, 'read_pinned', return_value=json.dumps(value).encode()), \
                patch.object(subject.bootstrap, 'sibling') as observer, self.assertRaises(subject.Refused):
            subject.network(target, self.policy)
        observer.assert_not_called()

    def test_real_http_ingress_probe_never_supplies_a_user_assertion(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get('Cf-Access-Jwt-Assertion')))
                self.send_response(401)
                self.end_headers()
            def log_message(self, *args):
                pass
        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        real = subject.http.client.HTTPConnection
        try:
            with patch.object(subject.http.client, 'HTTPConnection',
                              side_effect=lambda _host, _port, **kw: real('127.0.0.1', server.server_port, **kw)):
                subject.ingress(SimpleNamespace(runtime={'external_origin': 'https://staging.example.test'}))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual(requests, [('/api/1/session/mode', None),
                                   ('/api/1/session/mode', 'not-a-signed-assertion')])

    def test_renewal_closes_when_any_observer_fails_and_never_claims_acceptance(self):
        target = SimpleNamespace(protect=lambda: None, path=Path(self.policy['binding']),
            binding={'control_root': '/host/control'}, identity={'installation_id': 'test'})
        @contextmanager
        def held():
            yield
        journal = SimpleNamespace(lock=held)
        host = SimpleNamespace(check=lambda: {'boot': 'same'}, desired=lambda: '123')
        for failure in (None, 'network', 'containers', 'native', 'ingress'):
            with self.subTest(failure=failure), ExitStack() as stack:
                stack.enter_context(patch.object(subject.sys, 'platform', 'linux'))
                stack.enter_context(patch.object(subject.os, 'geteuid', return_value=0))
                stack.enter_context(patch.object(subject.time, 'time', return_value=8100))
                stack.enter_context(patch.object(subject, 'load_policy', return_value=self.policy))
                stack.enter_context(patch.object(subject.reconcile, 'Target', return_value=target))
                stack.enter_context(patch.object(subject.reconcile, 'protected', side_effect=lambda p, **kw: p))
                stack.enter_context(patch.object(subject.reconcile, 'Journal', return_value=journal))
                stack.enter_context(patch.object(subject.reconcile, 'GoogleHost', return_value=host))
                stack.enter_context(patch.object(subject, 'bound_state'))
                connector = SimpleNamespace(POLICY='/host/install.json', validate=lambda p: p,
                    verify=lambda p: None, promoted_policy=lambda p: p['activation'])
                stack.enter_context(patch.object(subject.bootstrap, 'sibling', return_value=connector))
                stack.enter_context(patch.object(subject.contract, 'read_json',
                    return_value={'activation': self.policy}))
                closed = stack.enter_context(patch.object(subject, 'close'))
                published = stack.enter_context(patch.object(subject.reconcile, 'atomic'))
                for name in ('network', 'containers', 'native', 'ingress'):
                    stack.enter_context(patch.object(subject, name,
                        return_value={'dispatcher': 'a' * 64} if name == 'containers' else None,
                        side_effect=subject.Refused('probe_failed') if name == failure else None))
                if failure:
                    with self.assertRaises(subject.Refused):
                        subject.renew('/host/policy.json')
                    closed.assert_called_once_with(target)
                    published.assert_not_called()
                else:
                    result = subject.renew('/host/policy.json')
                    closed.assert_not_called()
                    lease = published.call_args.args[1]
                    self.assertEqual(lease['expires_at'], 8200)
                    self.assertEqual(result['human_acceptance'], 'not-established')
                    self.assertEqual(result['user_journeys'], 'not-established')


if __name__ == '__main__':
    unittest.main()
