"""Offline installer planning, secret identity, and reviewed mode transition checks."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('activation_install_subject', ROOT / 'host/activation_install.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class ActivationInstallTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'schema': 'hyprn-activation-install/v1', 'platform_root': '/opt/hyprn/platform/release',
            'activation': {'schema': 'hyprn-qualification-access/v1', 'binding': '/host/binding.json',
                'desired_sha256': 'a' * 64, 'journal_root': '/host/journal',
                'disk': {'disk_name': 'test-data', 'device_name': 'test-data', 'retired_hosts': []},
                'network_policy': {'path': '/host/network.json', 'sha256': 'b' * 64},
                'mode': 'qualification', 'not_before': 1000, 'not_after': 8200},
            'account_id': 'c' * 32, 'tunnel_id': '11111111-2222-4333-8444-555555555555',
            'secret_version': 2, 'access_readback': {'path': '/host/access.json', 'sha256': 'd' * 64}}

    def token(self, **updates):
        value = {'a': self.policy['account_id'], 't': self.policy['tunnel_id'],
                 's': base64.b64encode(b'illustrative-secret' * 3).decode()}
        value.update(updates)
        return base64.b64encode(json.dumps(value).encode())

    def test_token_account_tunnel_and_destination_are_bound_without_echo(self):
        token = self.token()
        self.assertEqual(subject.token_bytes(token, self.policy), token)
        for value in (self.token(a='other'), self.token(t='other'), self.token(e='evil.test'),
                      self.token(s=base64.b64encode(b'x').decode()), token + b'\n', b'not-base64'):
            with self.subTest(shape=len(value)), self.assertRaises(subject.Refused) as caught:
                subject.token_bytes(value, self.policy)
            self.assertNotIn(value.decode(errors='ignore'), str(caught.exception))

    def test_plan_is_deterministic_and_does_not_access_cloud_or_mutate(self):
        with patch.object(subject.setup, 'run', side_effect=AssertionError('unexpected mutation')), \
                patch.object(subject.bootstrap.loader, 'AttachedServiceAccount', side_effect=AssertionError('cloud')):
            first = subject.plan(self.policy)
            second = subject.plan(self.policy)
        self.assertEqual(first, second)
        self.assertFalse(first['cloud_resources_changed'])
        self.assertFalse(first['provider_messages_sent'])
        self.assertIn('host/activation.py', first['sources'])
        promoted = first['conditional_promotion']['activation']
        self.assertEqual(promoted['mode'], 'staging')
        self.assertIsNone(promoted['not_after'])
        self.assertEqual(promoted['desired_sha256'], self.policy['activation']['desired_sha256'])

    def test_installer_always_starts_bounded_and_has_no_arbitrary_command(self):
        for key, value in (('command', 'true'), ('token', 'secret'), ('approved', True)):
            with self.assertRaises(subject.Refused):
                subject.validate(dict(self.policy, **{key: value}))
        invalid = copy.deepcopy(self.policy)
        invalid['activation'] = subject.promoted_policy(self.policy)
        with self.assertRaises(subject.Refused):
            subject.validate(invalid)

    def test_unit_credentials_are_files_not_argv_or_environment(self):
        units = subject.units(self.policy)
        tunnel = units['hyprn-tunnel.service']
        self.assertIn('LoadCredential=tunnel-token:/run/hyprn-tunnel/tunnel-token', tunnel)
        self.assertIn('--token-file %d/tunnel-token', tunnel)
        self.assertNotIn('--token ', tunnel)
        self.assertNotIn('Environment=', tunnel)
        self.assertIn('--no-autoupdate', tunnel)
        self.assertIn('--protocol http2 --edge-ip-version 4', tunnel)
        self.assertIn('Slice=hyprn-tunnel.slice', tunnel)
        self.assertIn('169.254.0.0/16', units['hyprn-tunnel.slice'])
        self.assertIn('Slice=hyprn-tunnel.slice', units['hyprn-tunnel-boundary-probe.service'])
        self.assertIn('/opt/hyprn/platform/release/host/activation.py',
                      units['hyprn-qualification-access.service'])

    def test_unprivileged_probe_reads_only_installed_nonsecret_code(self):
        self.policy['platform_root'] = '/private/deployment/release'
        unit = subject.units(self.policy)['hyprn-tunnel-boundary-probe.service']
        self.assertIn('ExecStart=/usr/bin/python3 -I -B /usr/lib/hyprn-tunnel-boundary-probe.py', unit)
        self.assertNotIn('/private/', unit)
        raw, mode = subject.files(self.policy)[str(subject.PROBE)]
        self.assertEqual(raw, (ROOT / 'host/tunnel_boundary_probe.py').read_bytes())
        self.assertEqual(mode, 0o644)
        self.assertNotIn(b'import activation', raw)
        self.assertIn('User=10006', unit)
        self.assertIn('ProtectSystem=strict', unit)

    def test_connector_uses_local_dns_without_access_to_metadata_dns(self):
        unit = subject.units(self.policy)['hyprn-tunnel.service']
        self.assertIn('BindReadOnlyPaths=/etc/hyprn/tunnel-resolv.conf:/etc/resolv.conf', unit)
        raw, mode = subject.files(self.policy)['/etc/hyprn/tunnel-resolv.conf']
        self.assertEqual(raw, b'nameserver 127.0.0.53\noptions timeout:2 attempts:2\n')
        self.assertEqual(mode, 0o644)
        self.assertNotIn('169.254.169.254', raw.decode())

    def test_connector_accepts_only_the_exact_nat_origin_among_private_addresses(self):
        unit = subject.units(self.policy)['hyprn-tunnel.slice']
        allowed = next(line.split('=', 1)[1].split() for line in unit.splitlines()
                       if line.startswith('IPAddressAllow='))
        app = subject.contract.service_networks('app')['application']['ipv4_address']
        self.assertEqual(set(allowed), {'127.0.0.1/32', '127.0.0.53/32', app + '/32'})
        self.assertIn('169.254.0.0/16', unit)
        self.assertIn('172.16.0.0/12', unit)

    def test_unreachable_origin_has_specific_diagnostic(self):
        with patch.object(subject.os, 'getuid', return_value=subject.UID), \
                patch.object(subject.Path, 'read_text', return_value='0::/hyprn-tunnel.slice/probe'), \
                patch.object(subject.socket, 'create_connection', side_effect=TimeoutError()), \
                self.assertRaises(subject.Refused) as caught:
            subject.boundary_probe()
        self.assertEqual(caught.exception.reason, 'tunnel_origin_unreachable')

    def test_probe_requires_origin_success_and_metadata_denial(self):
        from unittest.mock import MagicMock
        with patch.object(subject.os, 'getuid', return_value=subject.UID), \
                patch.object(subject.Path, 'read_text', return_value='0::/hyprn-tunnel.slice/probe'), \
                patch.object(subject.socket, 'create_connection',
                             side_effect=[MagicMock(), PermissionError(13, 'denied')]):
            self.assertEqual(subject.boundary_probe()['metadata'], 'blocked-from-connector-slice')
        for second, reason in ((MagicMock(), 'tunnel_metadata_reachable'),
                               (ConnectionRefusedError(111, 'refused'),
                                'tunnel_metadata_denial_unproven')):
            with self.subTest(reason=reason), \
                    patch.object(subject.os, 'getuid', return_value=subject.UID), \
                    patch.object(subject.Path, 'read_text', return_value='0::/hyprn-tunnel.slice/probe'), \
                    patch.object(subject.socket, 'create_connection', side_effect=[MagicMock(), second]), \
                    self.assertRaises(subject.Refused) as caught:
                subject.boundary_probe()
            self.assertEqual(caught.exception.reason, reason)

    def test_access_projection_requires_one_exact_origin_and_access_jwt(self):
        target = SimpleNamespace(runtime={'external_origin': 'https://staging.example.test',
            'access': {'issuer': 'https://test.cloudflareaccess.com', 'audience': 'abc'}})
        value = {'schema': 'hyprn-tunnel-readback/v1', 'account_id': self.policy['account_id'],
            'tunnel_id': self.policy['tunnel_id'], 'origin': target.runtime['external_origin'],
            'issuer': target.runtime['access']['issuer'], 'audience': 'abc',
            'ingress': [{'hostname': 'staging.example.test', 'service': 'http://127.0.0.1:8080',
                'originRequest': {'access': {'required': True, 'teamName': 'test', 'audTag': ['abc']}}},
                {'service': 'http_status:404'}]}
        with patch.object(subject.bootstrap, 'read_pinned', return_value=json.dumps(value).encode()):
            subject.access_readback(self.policy, target)
        for mutation in ('disable_access', 'remote_origin', 'wildcard'):
            wrong = copy.deepcopy(value)
            if mutation == 'disable_access':
                wrong['ingress'][0]['originRequest']['access']['required'] = False
            elif mutation == 'remote_origin':
                wrong['ingress'][0]['service'] = 'http://169.254.169.254'
            else:
                wrong['ingress'][1] = {'service': 'http://127.0.0.1:8080'}
            with patch.object(subject.bootstrap, 'read_pinned', return_value=json.dumps(wrong).encode()), \
                    self.assertRaises(subject.Refused):
                subject.access_readback(self.policy, target)

    def test_ongoing_mode_keeps_fresh_expiring_lease_checks(self):
        policy = subject.promoted_policy(self.policy)
        subject.activation.validate_policy(policy)
        subject.activation.window(policy, 99999999)
        with self.assertRaises(subject.Refused):
            subject.activation.window(policy, 999)
        with self.assertRaises(subject.Refused):
            subject.activation.validate_policy(dict(policy, not_after=99999999))
        self.assertEqual(subject.activation.LEASE_SECONDS, 240)


if __name__ == '__main__':
    unittest.main()
