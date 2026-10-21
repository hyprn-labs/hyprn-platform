"""The deployment preview grants only the declared service connections."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import contract
import service_network as network


class ServiceNetworkTests(unittest.TestCase):
    def setUp(self):
        runtime = json.loads((ROOT / 'contracts/v1/fixtures.json').read_text())['valid']['runtime']
        self.policy = contract.network_policy(runtime)

    def test_cli_previews_without_applying_or_exposing_admission(self):
        with tempfile.TemporaryDirectory(prefix='hyprn-service-policy-') as directory:
            path = Path(directory) / 'policy.json'
            path.write_text(json.dumps(self.policy))
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'host/service_network.py'),
                                     '--policy', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertFalse(value['applied'])
            self.assertEqual(value['admission'], 'closed')
            self.assertEqual(value, network.plan(self.policy))
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_rejects_extra_authority_and_topology_changes(self):
        changes = [
            lambda p: p['proxy'].update(hosts=['api.anthropic.com', '*.cloudflareaccess.com']),
            lambda p: p['proxy'].update(hosts=['api.anthropic.com', 'a.cloudflareaccess.com.evil']),
            lambda p: p['proxy'].update(source='0.0.0.0/0'),
            lambda p: p['proxy'].update(target_port=80),
            lambda p: p.update(metadata='allow'),
            lambda p: p.update(ipv6='enabled'),
            lambda p: p.update(unreviewed=True),
            lambda p: p['database'].update(address='169.254.169.254'),
            lambda p: p['database'].update(address='8.8.8.8'),
            lambda p: p['database'].update(address='172.29.81.5'),
        ]
        for change in changes:
            value = copy.deepcopy(self.policy)
            change(value)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'invalid_service'):
                network.plan(value)

    def test_proxy_has_exact_connect_routes_without_dynamic_authority_or_admin(self):
        config = network.proxy_config(self.policy)
        self.assertEqual(set(config), {'static_resources'})
        resources = config['static_resources']
        listener, = resources['listeners']
        self.assertEqual(listener['address']['socket_address'],
                         {'address': '172.29.81.1', 'port_value': 3128})
        manager = listener['filter_chains'][0]['filters'][0]['typed_config']
        hosts = manager['route_config']['virtual_hosts']
        self.assertEqual([h['domains'] for h in hosts],
                         [['api.anthropic.com:443'], ['fixture.cloudflareaccess.com:443']])
        for host in hosts:
            route, = host['routes']
            self.assertEqual(route['match'], {'connect_matcher': {}})
        for cluster in resources['clusters']:
            self.assertEqual(cluster['type'], 'LOGICAL_DNS')
            self.assertEqual(cluster['dns_lookup_family'], 'V4_ONLY')
            self.assertNotIn('transport_socket', cluster)  # TLS belongs to the client.

    def test_firewall_denies_metadata_before_connections_and_has_no_catchall_accept(self):
        rules = network.filter_rules(self.policy)
        forward = rules['DOCKER-USER']
        self.assertEqual(forward[0], ['-d', '169.254.169.254/32', '-j', 'DROP'])
        self.assertEqual(forward[-1], ['-j', 'DROP'])
        for rule in forward[1:-1]:
            self.assertIn('-s', rule)
            self.assertIn('-d', rule)
            self.assertIn('--ctstate', rule)
            self.assertIn('--dport' if 'NEW,ESTABLISHED' in rule else '--sport', rule)
        self.assertFalse(any('443' in rule for rule in forward))
        incoming = rules['HYPRN-SERVICE-IN']
        proxy = [row for row in incoming if '3128' in row]
        self.assertEqual(len(proxy), 1)
        self.assertIn('172.29.81.2/32', proxy[0])
        outgoing = rules['HYPRN-PROXY-OUT']
        public = outgoing.index(['-p', 'tcp', '--dport', '443', '-j', 'RETURN'])
        for cidr in network.NON_PUBLIC:
            self.assertLess(outgoing.index(['-d', cidr, '-j', 'REJECT']), public)
        self.assertEqual(outgoing[-1], ['-j', 'REJECT'])

    def test_proxy_is_unprivileged_bounded_and_requires_network_guard(self):
        unit = network.proxy_unit()
        self.assertIn('User=10005', unit)
        self.assertIn('BindsTo=hyprn-service-network.service', unit)
        self.assertIn('MemoryMax=256M', unit)
        self.assertIn('NoNewPrivileges=true', unit)
        self.assertIn('CapabilityBoundingSet=\n', unit)
        self.assertNotIn('Environment=', unit)
