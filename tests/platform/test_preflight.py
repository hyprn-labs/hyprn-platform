"""Read-only preflight decisions over explicit OS/daemon doubles, not host qualification."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import preflight

RULES = b'''*filter
:FORWARD DROP [0:0]
:DOCKER-USER - [0:0]
-A FORWARD -j DOCKER-USER
-A DOCKER-USER -d 169.254.169.254/32 -j DROP
-A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A DOCKER-USER -j DROP
COMMIT
'''


def target():
    values = copy.deepcopy(json.loads((ROOT / 'contracts/v1/fixtures.json').read_bytes())['valid'])
    runtime, release = values['runtime'], values['release']
    runtime['execution_host']['docker_endpoint'] = 'unix:///run/docker.sock'
    return SimpleNamespace(runtime=runtime, desired=values['desired'],
        identity=dict(installation_id=runtime['installation_id'], release_sha256='a' * 64, config_sha256='b' * 64),
        preview=preflight.reconcile.contract.render(release, runtime), protect=Mock(), unchanged=Mock())


def policy(value, ca):
    return dict(schema='hyprn-host-preflight/v1', identity=value.identity,
        desired_sha256=preflight.reconcile.contract.digest(value.desired), database_ca_source=str(ca),
        docker=dict(sha256='c' * 64, version='27.5.1'), compose=dict(sha256='d' * 64, version='2.32.4'))


class PolicyAndCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hyprn-preflight-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.target = target()
        self.ca = self.root / 'database-ca.pem'
        self.ca.write_bytes(b'nonsecret synthetic CA fixture')
        self.target.runtime['database']['ca_sha256'] = hashlib.sha256(self.ca.read_bytes()).hexdigest()
        self.path = self.root / 'policy.json'
        self.policy = policy(self.target, self.ca)
        self.write()
        self.authority = patch.object(preflight.reconcile, 'protected', side_effect=lambda path, **kwargs: Path(path))
        self.authority.start()
        self.addCleanup(self.authority.stop)

    def write(self):
        self.path.write_text(json.dumps(self.policy))

    def test_policy_binds_exact_target_and_never_accepts_success_or_command_receipts(self):
        self.assertEqual(preflight.policy_at(self.target, self.path), self.policy)
        for extra in ('firewall_sha256', 'success', 'command', 'admission_ready'):
            self.policy[extra] = True
            self.write()
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'policy_binding'):
                preflight.policy_at(self.target, self.path)
            del self.policy[extra]
        self.policy['desired_sha256'] = '0' * 64
        self.write()
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'policy_binding'):
            preflight.policy_at(self.target, self.path)

    def test_tool_versions_and_hashes_must_be_explicit_reviewed_values(self):
        for field, value in (('sha256', 'latest'), ('version', 'latest')):
            changed = copy.deepcopy(self.policy)
            changed['docker'][field] = value
            self.path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'host_tool_policy'):
                preflight.policy_at(self.target, self.path)
        self.policy['compose']['version'] = '1.29.2'
        self.write()
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'compose_v2_required'):
            preflight.policy_at(self.target, self.path)

    def test_observed_prerequisites_only_allow_closed_bootstrap(self):
        host = SimpleNamespace(check=Mock(return_value={'fixture': 'live-boundary-observation'}))
        docker = dict(path='/usr/bin/docker', sha256='c' * 64, version='27.5.1', endpoint='unix:///run/docker.sock')
        with patch.object(preflight, 'operating_system'), patch.object(preflight, 'docker_observation', return_value=docker), \
                patch.object(preflight, 'owners_and_paths'), patch.object(preflight, 'network_observation',
                return_value={'assurance': 'minimum-structure-only', 'live_container_probe': False}):
            result = preflight.check(self.target, self.path, host=host)
        host.check.assert_called_once_with()
        self.assertTrue(result['bootstrap_ready'])
        self.assertFalse(result['admission_ready'])
        self.assertFalse(result['network_containment_qualified'])
        self.assertEqual(result['docker'], docker)
        self.assertIn('cloudflare_connector_activation_required', result['admission_blockers'])
        self.assertIn('live_container_network_probe_required', result['admission_blockers'])

    def test_failed_real_fence_stops_before_daemon_or_secret_inspection(self):
        host = SimpleNamespace(check=Mock(side_effect=preflight.reconcile.Refused('exclusive_disk_ownership_unproven')))
        with patch.object(preflight, 'operating_system'), patch.object(preflight, 'docker_observation') as docker:
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'exclusive_disk'):
                preflight.check(self.target, self.path, host=host)
            docker.assert_not_called()

    def test_supplied_ca_source_must_match_runtime_before_network_observation(self):
        self.ca.write_bytes(b'wrong CA')
        with patch.object(preflight, 'operating_system'), patch.object(preflight, 'docker_observation'), \
                patch.object(preflight, 'owners_and_paths'), patch.object(preflight, 'network_observation') as network:
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'database_ca_source_mismatch'):
                preflight.check(self.target, self.path, host=SimpleNamespace(check=Mock()))
            network.assert_not_called()


class ToolTests(unittest.TestCase):
    def test_executable_hash_is_observed_not_accepted_from_policy(self):
        with tempfile.TemporaryDirectory(prefix='hyprn-tool-pin-') as temporary:
            path = Path(temporary).resolve() / 'tool'
            path.write_bytes(b'reviewed fixture executable bytes')
            path.chmod(0o755)
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            with patch.object(preflight.reconcile, 'protected', side_effect=lambda value, **kw: Path(value)), \
                    patch.object(preflight.Path, 'lstat', return_value=SimpleNamespace(st_uid=0)):
                self.assertEqual(preflight.tool(path, expected), expected)
                with self.assertRaisesRegex(preflight.reconcile.Refused, 'host_tool_pin_mismatch'):
                    preflight.tool(path, '0' * 64)


class OperatingSystemTests(unittest.TestCase):
    def test_unsupported_platform_and_architecture_are_actionable(self):
        with patch.object(preflight.sys, 'platform', 'darwin'), self.assertRaisesRegex(preflight.reconcile.Refused, 'linux_root'):
            preflight.operating_system()
        with patch.object(preflight.sys, 'platform', 'linux'), patch.object(preflight.os, 'geteuid', return_value=0), \
                patch.object(preflight.platform, 'machine', return_value='aarch64'), \
                self.assertRaisesRegex(preflight.reconcile.Refused, 'linux_amd64'):
            preflight.operating_system()

    def test_only_debian12_and_active_docker_systemd_units_are_supported(self):
        with patch.object(preflight.sys, 'platform', 'linux'), patch.object(preflight.os, 'geteuid', return_value=0), \
                patch.object(preflight.platform, 'machine', return_value='x86_64'), \
                patch.object(preflight.platform, 'freedesktop_os_release', create=True, return_value={'ID': 'debian', 'VERSION_ID': '12'}), \
                patch.object(preflight.Path, 'is_dir', return_value=True), patch.object(preflight, 'tool') as tool, \
                patch.object(preflight, 'observe', return_value=b'active\n') as observe:
            preflight.operating_system()
            self.assertEqual(tool.call_count, len(preflight.UTILITIES))
            self.assertEqual(observe.call_count, 2)
            observe.return_value = b'inactive\n'
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'docker_systemd_inactive'):
                preflight.operating_system()
        with patch.object(preflight.sys, 'platform', 'linux'), patch.object(preflight.os, 'geteuid', return_value=0), \
                patch.object(preflight.platform, 'machine', return_value='x86_64'), \
                patch.object(preflight.platform, 'freedesktop_os_release', create=True, return_value={'ID': 'debian', 'VERSION_ID': '13'}), \
                self.assertRaisesRegex(preflight.reconcile.Refused, 'debian12_required'):
            preflight.operating_system()


class DockerTests(unittest.TestCase):
    def setUp(self):
        self.target = target()
        self.policy = policy(self.target, '/reviewed/ca.pem')
        self.info = dict(OSType='linux', Architecture='x86_64', CgroupVersion='2', ServerVersion='27.5.1',
            LiveRestoreEnabled=False, MemoryLimit=True, CpuCfsPeriod=True, CpuCfsQuota=True, PidsLimit=True,
            Swarm={'LocalNodeState': 'inactive'}, SecurityOptions=['name=seccomp,profile=builtin'],
            ClientInfo={'Plugins': [dict(Name='compose', Version='v2.32.4', Path='/usr/libexec/docker/cli-plugins/docker-compose')]})
        self.stat = SimpleNamespace(st_mode=stat.S_IFSOCK | 0o660, st_uid=0, st_gid=998)
        self.calls = []
        for context in (patch.object(preflight, 'tool', return_value='c' * 64),
                patch.object(preflight.Path, 'is_symlink', return_value=False),
                patch.object(preflight.Path, 'lstat', side_effect=lambda: self.stat),
                patch.object(preflight.reconcile, 'protected', side_effect=lambda path, **kw: Path(path)),
                patch.object(preflight, 'observe', side_effect=self.command)):
            context.start()
            self.addCleanup(context.stop)

    def command(self, command, reason):
        self.calls.append(command)
        self.assertEqual(command[:3], ['/usr/bin/docker', '--host', 'unix:///run/docker.sock'])
        if command[3] == 'info':
            return json.dumps(self.info).encode()
        self.assertEqual(command[3:], ['compose', 'version', '--short'])
        return b'2.32.4\n'

    def test_exact_daemon_and_plugin_are_read_without_loading_images_or_starting_containers(self):
        result = preflight.docker_observation(self.target, self.policy)
        self.assertEqual(result['endpoint'], 'unix:///run/docker.sock')
        self.assertEqual(result['socket_gid'], 998)
        self.assertEqual(len(self.calls), 2)

    def test_missing_resource_limit_or_wrong_runtime_refuses(self):
        for key, bad in (('PidsLimit', False), ('MemoryLimit', False), ('CgroupVersion', '1'),
                         ('LiveRestoreEnabled', True), ('ServerVersion', 'unreviewed')):
            previous = self.info[key]
            self.info[key] = bad
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'docker_runtime_prerequisites'):
                preflight.docker_observation(self.target, self.policy)
            self.info[key] = previous

    def test_seccomp_and_compose_plugin_bytes_cannot_be_substituted(self):
        self.info['SecurityOptions'] = []
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'docker_seccomp_required'):
            preflight.docker_observation(self.target, self.policy)
        self.info['SecurityOptions'] = ['name=seccomp,profile=builtin']
        self.info['ClientInfo']['Plugins'][0]['Path'] = '/root/.docker/cli-plugins/docker-compose'
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'compose_v2_pin_mismatch'):
            preflight.docker_observation(self.target, self.policy)

    def test_linked_or_world_accessible_daemon_socket_refuses(self):
        with patch.object(preflight.Path, 'is_symlink', return_value=True), \
                self.assertRaisesRegex(preflight.reconcile.Refused, 'canonical_socket'):
            preflight.docker_observation(self.target, self.policy)
        self.stat.st_mode = stat.S_IFSOCK | 0o666
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'docker_socket_authority'):
            preflight.docker_observation(self.target, self.policy)


class NetworkTests(unittest.TestCase):
    def test_metadata_guard_and_default_drop_must_be_effective_chain_rules(self):
        self.assertEqual(preflight.firewall_structure(RULES), hashlib.sha256(RULES).hexdigest())
        cases = ((b'-A FORWARD -j DOCKER-USER\n', b'', 'forward_guard'),
                 (b'-d 169.254.169.254/32', b'-d 169.254.169.253/32', 'metadata_drop'),
                 (b'-A DOCKER-USER -j DROP\n', b'', 'default_deny'),
                 (b'-m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT', b'-j ACCEPT', 'unconditional_bypass'))
        for old, new, code in cases:
            with self.assertRaisesRegex(preflight.reconcile.Refused, code):
                preflight.firewall_structure(RULES.replace(old, new))

    def test_live_structural_check_remains_distinct_from_container_probe(self):
        knobs = [SimpleNamespace(parent=SimpleNamespace(name=name), read_text=lambda: '1') for name in ('all', 'default', 'eth0')]
        output = {'/usr/sbin/iptables': b'iptables v1.8.9 (nf_tables)\n',
                  '/usr/sbin/iptables-save': RULES,
                  '/usr/bin/ss': b'LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 64 127.0.0.1:8000 0.0.0.0:*\n'}
        with patch.object(preflight.Path, 'glob', return_value=knobs), \
                patch.object(preflight, 'observe', side_effect=lambda command, reason: output[command[0]]):
            result = preflight.network_observation()
            self.assertEqual(result['assurance'], 'minimum-structure-only')
            self.assertFalse(result['live_container_probe'])
            knobs[-1].read_text = lambda: '0'
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'ipv6_must_be_disabled'):
                preflight.network_observation()
            knobs[-1].read_text = lambda: '1'
            output['/usr/bin/ss'] = b'LISTEN 0 128 0.0.0.0:8000 0.0.0.0:*\n'
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'unexpected_public_listener'):
                preflight.network_observation()
            output['/usr/bin/ss'] = b'LISTEN 0 128 127.0.0.1:2375 0.0.0.0:*\n'
            with self.assertRaisesRegex(preflight.reconcile.Refused, 'docker_tcp_listener_forbidden'):
                preflight.network_observation()


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.target = target()
        runtime = self.target.runtime
        self.users = {uid: SimpleNamespace(pw_uid=uid, pw_gid=uid, pw_name=owner,
            pw_dir=runtime['execution_host']['host_home'] if owner == 'execution' else '/nonexistent')
            for owner, uid in runtime['service_users'].items()}
        self.groups = {uid: SimpleNamespace(gr_gid=uid, gr_mem=[]) for uid in self.users}
        self.groups[998] = SimpleNamespace(gr_gid=998, gr_mem=[])
        self.infos = {runtime['mounts'][area]: SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=uid, st_gid=uid)
            for area, uid in (('application', 10002), ('modeling', 10001), ('execution', 10003))}
        self.infos[runtime['execution_host']['host_home']] = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=10003, st_gid=10003)
        self.null = os.open(os.devnull, os.O_RDONLY)
        self.closed = False
        def release():
            if not self.closed:
                os.close(self.null)
        self.addCleanup(release)
        def observed_path(path):
            try:
                return self.infos[str(path)]
            except KeyError:
                raise FileNotFoundError(str(path)) from None
        for context in (patch.object(preflight.pwd, 'getpwuid', side_effect=lambda uid: self.users[uid]),
                patch.object(preflight.grp, 'getgrgid', side_effect=lambda gid: self.groups[gid]),
                patch.object(preflight.Path, 'is_symlink', return_value=False),
                patch.object(preflight.Path, 'lstat', autospec=True, side_effect=observed_path),
                patch.object(preflight.reconcile._secret_loader, 'private_directory', return_value=self.null),
                patch.object(preflight.reconcile._secret_loader, 'require_tmpfs')):
            context.start()
            self.addCleanup(context.stop)

    def test_exact_owner_paths_and_private_tmpfs_are_checked_and_descriptor_released(self):
        preflight.owners_and_paths(self.target, dict(socket_gid=998))
        self.closed = True
        with self.assertRaises(OSError):
            os.fstat(self.null)

    def test_initial_empty_store_does_not_require_precreated_native_home(self):
        del self.infos[self.target.runtime['execution_host']['host_home']]
        preflight.owners_and_paths(self.target, dict(socket_gid=998))
        self.closed = True

    def test_container_numeric_uids_need_no_host_login_accounts(self):
        for uid in (10001, 10002, 65534):
            self.users.pop(uid)
        preflight.owners_and_paths(self.target, dict(socket_gid=998))
        self.closed = True

    def test_wrong_owner_missing_user_and_docker_privilege_refuse(self):
        native = self.users.pop(10003)
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'service_account_missing'):
            preflight.owners_and_paths(self.target, dict(socket_gid=998))
        self.users[10003] = native
        self.groups[998].gr_mem = ['app']
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'untrusted_owner_has_docker_group'):
            preflight.owners_and_paths(self.target, dict(socket_gid=998))
        self.groups[998].gr_mem = []
        self.infos[self.target.runtime['mounts']['execution']].st_uid = 0
        with self.assertRaisesRegex(preflight.reconcile.Refused, 'store_path_ownership'):
            preflight.owners_and_paths(self.target, dict(socket_gid=998))


if __name__ == '__main__':
    unittest.main()
