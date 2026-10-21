"""Reviewed host network installation stays bound and closes on drift."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import contract
import service_network_install as installer


def policy():
    runtime = json.loads((ROOT / 'contracts/v1/fixtures.json').read_text())['valid']['runtime']
    return {'schema': 'hyprn-service-network-install/v1',
        'host': {'schema': 'hyprn-host-setup/v1', 'project_id': 'hyprn-staging',
            'project_number': '123456789', 'zone': 'europe-west1-b', 'host_id': 'hyprn-staging-host',
            'instance_id': '1234', 'disk_id': '4567', 'disk_name': 'hyprn-staging-data',
            'device_name': 'hyprn-data', 'disk_bytes': 100 * 1024**3,
            'disk_uuid': '11111111-1111-4111-8111-111111111111'},
        'setup_plan_sha256': 'a' * 64, 'installation_id': runtime['installation_id'],
        'network': contract.network_policy(runtime)}


class ServiceInstallTests(unittest.TestCase):
    def test_exact_plan_includes_all_generated_bytes_without_apply(self):
        first = installer.plan(policy())
        self.assertEqual(first, installer.plan(policy()))
        self.assertFalse(first['product_started'])
        self.assertFalse(first['secrets_transferred'])
        self.assertEqual(first['admission'], 'closed')
        raw = {k: v for k, v in first.items() if k != 'plan_sha256'}
        self.assertEqual(first['plan_sha256'], contract.digest(raw))
        for name, (data, mode) in installer.files(policy()).items():
            self.assertEqual(first['files'][name],
                             {'sha256': installer.setup.digest(data), 'mode': mode})

    def test_docker_restart_applies_closed_guard_before_service_rules(self):
        files = installer.files(policy())
        unit = files['/etc/systemd/system/hyprn-service-network.service'][0].decode()
        self.assertIn('After=docker.service network-online.target', unit)
        self.assertIn('PartOf=docker.service', unit)
        self.assertIn('ExecStop=/etc/hyprn/host-setup/container-guard', unit)
        self.assertIn('enforce --policy', unit)
        self.assertIn('Wants=hyprn-service-network.service',
            files['/etc/systemd/system/docker.service.d/hyprn-network.conf'][0].decode())

    def test_external_compose_networks_reuse_platform_ownership(self):
        runtime = json.loads((ROOT / 'contracts/v1/fixtures.json').read_text())['valid']['runtime']
        expected = contract.external_networks(runtime)
        for name, row in expected.items():
            self.assertEqual(row, {'external': True, 'name': runtime['installation_id'] + '_' + name})

    def test_actual_bridge_requires_exact_owner_options_and_address(self):
        p = policy()
        config = p['network']['bridges']['application']
        row = {'Name': p['installation_id'] + '_application', 'Driver': 'bridge',
            'Internal': False, 'EnableIPv6': False, 'Scope': 'local', 'Id': 'fixed-id',
            'Options': config['driver_opts'], 'Labels': {'org.hyprn.installation': p['installation_id'],
                'org.hyprn.network': 'application'},
            'IPAM': {'Config': [{'Subnet': '172.29.81.0/24', 'Gateway': '172.29.81.1'}]}}
        with patch.object(installer, 'docker', return_value=json.dumps([row]).encode()):
            self.assertEqual(installer.inspect_bridge(p, 'application'), 'fixed-id')
        for key, value in [('Labels', {}), ('EnableIPv6', True), ('Options', {})]:
            changed = dict(row, **{key: value})
            with patch.object(installer, 'docker', return_value=json.dumps([changed]).encode()), \
                    self.assertRaisesRegex(installer.setup.reconcile.Refused, 'network_identity'):
                installer.inspect_bridge(p, 'application')

    def test_owned_rule_order_and_first_jumps_are_verified(self):
        p = policy()
        expected = installer.network.plan(p['network'])
        rows = []
        for chain, rules in expected['filter_chains'].items():
            rows.extend('-A ' + chain + ' ' + ' '.join(row) for row in rules)
        for chain, jump in expected['required_jumps'].items():
            rows.append('-A ' + chain + ' ' + ' '.join(jump))
        raw = ('\n'.join(rows) + '\n').encode()
        with patch.object(installer, 'run', return_value=raw):
            self.assertRegex(installer.verify_rules(p), '[0-9a-f]{64}')
        for altered in (raw + b'-A DOCKER-USER -j ACCEPT\n',
                        raw.replace(b'-A INPUT -j HYPRN-SERVICE-IN', b'-A INPUT -j ACCEPT\n-A INPUT -j HYPRN-SERVICE-IN'),
                        raw.replace(b'169.254.169.254/32', b'169.254.169.253/32')):
            with patch.object(installer, 'run', return_value=altered), \
                    self.assertRaisesRegex(installer.setup.reconcile.Refused, 'firewall'):
                installer.verify_rules(p)

    def test_kernel_rule_normalization_preserves_authority(self):
        a = ['-p', 'tcp', '--dport', '443', '-m', 'conntrack', '--ctstate', 'NEW,ESTABLISHED', '-j', 'RETURN']
        b = ['-p', 'tcp', '-m', 'tcp', '--dport', '443', '-m', 'conntrack', '--ctstate', 'ESTABLISHED,NEW', '-j', 'RETURN']
        self.assertEqual(installer.normalize(a), installer.normalize(b))
        self.assertEqual(installer.normalize(['-j', 'REJECT', '--reject-with', 'icmp-port-unreachable']), ['-j', 'REJECT'])
        self.assertNotEqual(installer.normalize(['-j', 'REJECT', '--reject-with', 'tcp-reset']), ['-j', 'REJECT'])

    def test_unknown_policy_and_nonmatching_installation_rejected(self):
        p = policy()
        p['command'] = 'unreviewed'
        with self.assertRaises(installer.setup.reconcile.Refused):
            installer.plan(p)
        p = policy()
        p['installation_id'] = 'a;echo bypass'
        with self.assertRaises(installer.setup.reconcile.Refused):
            installer.plan(p)
