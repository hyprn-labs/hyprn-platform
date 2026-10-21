"""Approval pins and fresh-host refusals; no test mutates a host or cloud account."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HOST = Path(__file__).resolve().parents[2] / 'host'
sys.path.insert(0, str(HOST))
import setup


def policy():
    return dict(schema='hyprn-host-setup/v1', project_id='hyprn-staging', project_number='123456789',
                zone='europe-west1-b', host_id='hyprn-staging-host', instance_id='23456789',
                disk_name='hyprn-staging-data', disk_id='34567890', device_name='hyprn-data',
                disk_bytes=100 * 1024**3, disk_uuid='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee')


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        rows = []
        for name in ('containerd.io', 'docker-ce-cli', 'docker-ce', 'docker-compose-plugin', 'cloudflared',
                     'libjansson4', 'libnftables1', 'nftables'):
            raw = name.encode()
            (self.root / (name + '.deb')).write_bytes(raw)
            rows.append(dict(name=name, version='1.0', architecture='amd64', filename=name + '.deb',
                             sha256=hashlib.sha256(raw).hexdigest(), size=len(raw)))
        self.rows = rows
        self.lock = self.root / 'lock.json'
        self.lock.write_text(json.dumps(dict(schema='hyprn-host-packages/v1', os='debian12',
                                            architecture='amd64', packages=rows)))
        self.patch = patch.object(setup, 'LOCK', self.lock)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_plan_is_deterministic_and_grants_no_secret_or_product_start(self):
        a = setup.plan(policy(), self.root)
        self.assertEqual(a, setup.plan(policy(), self.root))
        self.assertFalse(a['product_started'])
        self.assertFalse(a['secrets_transferred'])
        self.assertEqual(a['admission'], 'closed')
        self.assertIn('preflight.py', a['sources'])
        self.assertEqual(len(a['packages']), 8)
        self.assertEqual(a['plan_sha256'], setup.digest(setup.canonical(
            {k: v for k, v in a.items() if k != 'plan_sha256'})))

    def test_plan_change_requires_new_approval(self):
        a = setup.plan(policy(), self.root)
        p = policy()
        p['instance_id'] = '99999999'
        self.assertNotEqual(a['plan_sha256'], setup.plan(p, self.root)['plan_sha256'])
        p = policy()
        p['disk_uuid'] = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeef'
        self.assertNotEqual(a['plan_sha256'], setup.plan(p, self.root)['plan_sha256'])

    def test_no_command_or_foreign_resource_can_be_injected(self):
        for key, value in (('command', 'true'), ('project_id', 'production'), ('disk_bytes', True),
                           ('disk_name', 'boot'), ('instance_id', 123), ('disk_uuid', '../../x')):
            p = policy()
            p[key] = value
            with self.subTest(key=key), self.assertRaises(setup.reconcile.Refused):
                setup.validate(p)

    def test_package_bytes_and_links_refuse_before_planning(self):
        target = self.root / 'docker-ce.deb'
        original = target.read_bytes()
        target.write_bytes(b'x' * len(original))
        with self.assertRaisesRegex(setup.reconcile.Refused, 'package_bytes'):
            setup.plan(policy(), self.root)
        target.unlink()
        target.symlink_to(self.root / 'docker-ce-cli.deb')
        with self.assertRaisesRegex(setup.reconcile.Refused, 'package_bytes'):
            setup.plan(policy(), self.root)

    def test_manifest_cannot_add_packages_or_escape_bundle(self):
        value = json.loads(self.lock.read_bytes())
        value['packages'][0]['filename'] = '../escape.deb'
        self.lock.write_text(json.dumps(value))
        with self.assertRaisesRegex(setup.reconcile.Refused, 'package_name'):
            setup.packages(self.root)
        value['packages'].append(copy.deepcopy(value['packages'][1]))
        self.lock.write_text(json.dumps(value))
        with self.assertRaisesRegex(setup.reconcile.Refused, 'package_set'):
            setup.packages(self.root)

    def test_file_templates_keep_disk_pin_and_startup_guard(self):
        value = setup.files(policy())
        mount = value['/etc/systemd/system/' + setup.MOUNT][0]
        self.assertIn(policy()['disk_uuid'], mount)
        self.assertIn('nodev,nosuid', mount)
        daemon = json.loads(value['/etc/docker/daemon.json'][0])
        self.assertFalse(daemon['live-restore'])
        self.assertEqual(daemon['bridge'], 'none')
        self.assertEqual(daemon['data-root'], '/srv/hyprn/staging/docker')
        self.assertNotIn('hosts', daemon)
        service = value['/etc/systemd/system/docker.service.d/hyprn.conf'][0]
        self.assertIn('ExecStartPre=', service)
        self.assertIn('ExecStartPost=', service)
        self.assertIn('Requires=' + setup.MOUNT, service)
        self.assertNotIn('cloudflared.service', '\n'.join(value))

    def test_firewall_script_has_valid_shell_and_fails_closed(self):
        text = setup.files(policy())[str(setup.CONFIG / 'container-guard')][0]
        result = subprocess.run(['/bin/sh', '-n'], input=text, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('169.254.169.254/32 -j DROP', text)
        self.assertIn('-A DOCKER-USER -j DROP', text)
        self.assertNotIn('-j ACCEPT', text)
        self.assertIn('-C INPUT -i "$bridge" -j DROP', text)

    def test_partition_or_mount_on_data_device_is_never_formatted(self):
        for entry in (dict(type='part', size=100 * 1024**3, mountpoints=[]),
                      dict(type='disk', size=100 * 1024**3, mountpoints=['/store']),
                      dict(type='disk', size=100 * 1024**3, mountpoints=[], children=[{}]),
                      dict(type='disk', size=30 * 1024**3, mountpoints=[])):
            with patch.object(setup, 'run', return_value=json.dumps({'blockdevices': [entry]}).encode()) as run:
                with self.assertRaisesRegex(setup.reconcile.Refused, 'disk_not_blank'):
                    setup.blank_device(Path('/dev/fixture'), 100 * 1024**3)
                self.assertEqual(run.call_count, 1)

    def test_existing_signature_is_not_erased(self):
        values = [dict(blockdevices=[dict(type='disk', size=100 * 1024**3, mountpoints=[])]),
                  dict(signatures=[{'type': 'ext4'}])]
        with patch.object(setup, 'run', side_effect=[json.dumps(x).encode() for x in values]) as run:
            with self.assertRaisesRegex(setup.reconcile.Refused, 'disk_has_signatures'):
                setup.blank_device(Path('/dev/fixture'), 100 * 1024**3)
            self.assertEqual(run.call_count, 2)

    def test_even_unrecognised_boot_filesystem_is_never_formatted(self):
        device = self.root / 'disk'
        device.touch()
        values = [dict(blockdevices=[dict(type='disk', size=100 * 1024**3, mountpoints=[])]),
                  dict(signatures=[]), dict(filesystems=[{'source': str(device)}])]
        with patch.object(setup, 'run', side_effect=[*[json.dumps(x).encode() for x in values], b'']):
            with self.assertRaisesRegex(setup.reconcile.Refused, 'boot_disk_forbidden'):
                setup.blank_device(device, 100 * 1024**3)

    def test_package_control_metadata_must_match_reviewed_package(self):
        with patch.object(setup, 'run', return_value=b'foreign\t1.0\tamd64') as run:
            with self.assertRaisesRegex(setup.reconcile.Refused, 'debian_package_identity'):
                setup.package_probe(self.rows, self.root)
            self.assertEqual(run.call_count, 1)

    def test_dependency_probe_precedes_package_installation(self):
        values = []
        for row in self.rows:
            values.extend(['\t'.join(row[k] for k in ('name', 'version', 'architecture')).encode(), b'\t'])
        with patch.object(setup, 'run', side_effect=values + [b'']) as run:
            paths = setup.package_probe(self.rows, self.root)
            self.assertEqual(run.call_args.args[0], ['/usr/bin/dpkg', '--dry-run', '--install', *paths])
            self.assertTrue(run.call_args.kwargs['package_diagnostics'])

    def test_package_dependency_failure_retains_bounded_diagnostics(self):
        result = subprocess.CompletedProcess(['dpkg'], 1, b'x' * 20000, b'missing dependency\xff')
        with patch.object(setup.subprocess, 'run', return_value=result):
            with self.assertRaises(setup.reconcile.Refused) as caught:
                setup.run(['/usr/bin/dpkg', '--dry-run', '--install', '/fixture.deb'],
                          package_diagnostics='package_dry_run')
        diagnostic = caught.exception.diagnostic
        self.assertEqual(diagnostic['stage'], 'package_dry_run')
        self.assertEqual(diagnostic['exit_code'], 1)
        self.assertEqual(len(diagnostic['stdout']), 16384)
        self.assertIn('missing dependency', diagnostic['stderr'])

    def test_other_command_failures_do_not_expose_output(self):
        result = subprocess.CompletedProcess(['command'], 1, b'private', b'private')
        with patch.object(setup.subprocess, 'run', return_value=result):
            with self.assertRaises(setup.reconcile.Refused) as caught:
                setup.run(['/usr/bin/command'])
        self.assertFalse(hasattr(caught.exception, 'diagnostic'))

    def test_missing_configure_dependency_refuses_before_dry_run(self):
        rows = [dict(name='engine', version='1', depends='nftables')]
        with patch.object(setup, 'installed_package_version', return_value=None):
            with self.assertRaisesRegex(setup.reconcile.Refused, 'dependency_missing:nftables'):
                setup.dependencies(rows)

    def test_planned_dependency_does_not_satisfy_predependency(self):
        rows = [dict(name='engine', version='1', pre_depends='helper'),
                dict(name='helper', version='1')]
        with patch.object(setup, 'installed_package_version', return_value=None):
            with self.assertRaisesRegex(setup.reconcile.Refused, 'dependency_missing:helper'):
                setup.dependencies(rows)
        rows[0] = dict(name='engine', version='1', depends='helper')
        setup.dependencies(rows)

    def test_unsupported_dependency_grammar_refuses_instead_of_guessing(self):
        with self.assertRaisesRegex(setup.reconcile.Refused, 'dependency_syntax'):
            setup.dependencies([dict(name='engine', version='1', depends='a | b')])

    def test_versioned_dependency_uses_debian_version_comparison(self):
        result = subprocess.CompletedProcess(['dpkg'], 1, b'', b'')
        with patch.object(setup, 'installed_package_version', return_value='1'), \
                patch.object(setup.subprocess, 'run', return_value=result) as command:
            with self.assertRaisesRegex(setup.reconcile.Refused, 'dependency_version:helper'):
                setup.dependencies([dict(name='engine', version='1', depends='helper (>= 2)')])
        self.assertEqual(command.call_args.args[0],
                         ['/usr/bin/dpkg', '--compare-versions', '1', '>=', '2'])

    def test_apply_refuses_non_linux_without_any_cloud_or_command(self):
        with patch.object(setup.sys, 'platform', 'darwin'), patch.object(setup, 'run') as run, \
                patch.object(setup, 'cloud_device') as cloud:
            with self.assertRaisesRegex(setup.reconcile.Refused, 'linux_root_amd64'):
                setup.apply('/nothing', '/nothing', 'a' * 64)
            cloud.assert_not_called()
            run.assert_not_called()

    def test_interrupted_intent_refuses_before_any_disk_or_package_action(self):
        policy_path = self.root / 'policy.json'
        policy_path.write_text(json.dumps(policy()))
        state = self.root / 'state'
        state.mkdir(mode=0o700)
        (state / 'intent.json').write_text('{}')
        expected = setup.plan(policy(), self.root)
        with patch.object(setup.sys, 'platform', 'linux'), patch.object(setup.os, 'geteuid', return_value=0), \
                patch.object(setup.platform, 'machine', return_value='x86_64'), \
                patch.object(setup.platform, 'freedesktop_os_release', create=True,
                             return_value={'ID': 'debian', 'VERSION_ID': '12'}), \
                patch.object(setup.reconcile, 'protected', side_effect=lambda p, **kw: Path(p)), \
                patch.object(setup, 'mkdir'), patch.object(setup, 'STATE', state), \
                patch.object(setup, 'cloud_device') as cloud, patch.object(setup, 'run') as run, \
                patch.object(Path, 'read_text', return_value='Filename\tType\n'):
            with self.assertRaisesRegex(setup.reconcile.Refused, 'interrupted_requires_reconciliation'):
                setup.apply(policy_path, self.root, expected['plan_sha256'])
            cloud.assert_not_called()
            run.assert_not_called()


class RemoteSetupTests(unittest.TestCase):
    def setUp(self):
        import setup_remote
        self.remote = setup_remote
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def operator(self):
        from unittest.mock import Mock
        op = self.remote.Operator.__new__(self.remote.Operator)
        op.policy = policy()
        op.root = self.root
        op.ssh = ['compute', 'ssh', 'hyprn-staging-host']
        op.record = Mock()
        return op

    def test_success_stops_same_host_and_upload_keeps_expiring_key(self):
        from unittest.mock import Mock
        op = self.operator()
        review = {'plan_sha256': 'a' * 64, 'bundle_sha256': 'b' * 64}
        receipt = {'plan_sha256': review['plan_sha256'], 'admission': 'closed', 'product_started': False}
        op.observe = Mock(side_effect=[{'status': 'TERMINATED'}, {'status': 'RUNNING'},
                                        {'status': 'RUNNING'}, {'status': 'TERMINATED'}])
        op.call = Mock(side_effect=[b'', b'', b'', b'', json.dumps(receipt).encode(), b''])
        result = op.apply(self.root / 'bundle', review, ['policy.json'])
        self.assertTrue(result['setup_completed'])
        self.assertEqual(result['vm_status'], 'TERMINATED')
        commands = [call.args[0] for call in op.call.call_args_list]
        upload = next(c for c in commands if c[:2] == ['compute', 'scp'])
        self.assertIn('--ssh-key-expire-after=30m', upload)
        self.assertIn('--scp-flag=-oStrictHostKeyChecking=yes', upload)
        self.assertEqual(commands[-1][:3], ['compute', 'instances', 'stop'])
        self.assertFalse(op.observe.call_args.kwargs['startup'])

    def test_reviewed_repair_uses_repair_entrypoint_and_still_stops(self):
        from unittest.mock import Mock
        op = self.operator()
        review = {'plan_sha256': 'a'*64, 'bundle_sha256': 'b'*64}
        receipt = {'plan_sha256': 'a'*64, 'admission': 'closed', 'product_started': False}
        op.observe = Mock(side_effect=[{'status':'TERMINATED'}, {'status':'RUNNING'},
                                      {'status':'RUNNING'}, {'status':'TERMINATED'}])
        op.call = Mock(side_effect=[b'', b'', b'', b'', json.dumps(receipt).encode(), b''])
        op.apply(self.root/'bundle', review, ['policy.json', 'platform/repair_setup.py'])
        execution = op.call.call_args_list[4].args[0][-1]
        self.assertIn('platform/repair_setup.py', execution)
        self.assertNotIn('platform/setup.py', execution)
        self.assertEqual(op.call.call_args_list[-1].args[0][:3], ['compute','instances','stop'])

    def test_explicit_keep_running_plan_does_not_restart_or_stop_existing_host(self):
        from unittest.mock import Mock
        op = self.operator()
        review = {'plan_sha256':'a'*64, 'bundle_sha256':'b'*64, 'keep_running':True}
        receipt = {'plan_sha256':'a'*64, 'admission':'closed', 'product_started':False}
        op.observe = Mock(return_value={'status':'RUNNING'})
        op.call = Mock(side_effect=[b'', b'', b'', json.dumps(receipt).encode()])
        result = op.apply(self.root/'bundle', review, ['platform/finalize_setup.py'])
        self.assertEqual(result['vm_status'], 'RUNNING')
        commands = [call.args[0] for call in op.call.call_args_list]
        self.assertFalse(any(c[:2]==['compute','instances'] for c in commands))
        self.assertIn('platform/finalize_setup.py', commands[-1][-1])

    def test_keep_running_failure_records_state_without_relaunch_or_stop(self):
        from unittest.mock import Mock
        op = self.operator()
        op.observe = Mock(return_value={'status':'RUNNING'})
        op.call = Mock(side_effect=[b'', b'', b'', RuntimeError('fixture failure')])
        with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
            op.apply(self.root/'bundle', {'plan_sha256':'a'*64, 'bundle_sha256':'b'*64,
                                         'keep_running':True}, ['platform/finalize_setup.py'])
        self.assertEqual(op.record.call_args.args[1]['vm_status'], 'RUNNING')
        self.assertFalse(op.record.call_args.args[1]['setup_completed'])
        self.assertFalse(any(c.args[0][:2]==['compute','instances'] for c in op.call.call_args_list))

    def test_uncertain_start_is_reconciled_by_observation_and_stop_never_restarted(self):
        from unittest.mock import Mock
        op = self.operator()
        op.observe = Mock(side_effect=[{'status': 'TERMINATED'}, {'status': 'RUNNING'}, {'status': 'TERMINATED'}])
        op.call = Mock(side_effect=[subprocess.TimeoutExpired('gcloud', 1), b''])
        with self.assertRaises(subprocess.TimeoutExpired):
            op.apply(self.root / 'bundle', {'plan_sha256': 'a' * 64}, [])
        self.assertEqual([c.args[0][2] for c in op.call.call_args_list], ['start', 'stop'])
        result = op.record.call_args.args[1]
        self.assertFalse(result['setup_completed'])
        self.assertEqual(result['vm_status'], 'TERMINATED')

    def test_an_already_running_host_is_never_stopped_or_modified(self):
        from unittest.mock import Mock
        op = self.operator()
        op.observe = Mock(return_value={'status': 'RUNNING'})
        op.call = Mock()
        with self.assertRaisesRegex(RuntimeError, 'not_stopped'):
            op.apply(self.root / 'bundle', {}, [])
        op.call.assert_not_called()
        op.record.assert_not_called()

    def test_bundle_changed_after_review_is_refused_before_cloud_access(self):
        path = self.root / 'bundle'
        path.write_bytes(b'wrong')
        review = dict(schema='hyprn-host-setup-deployment/v1', plan_sha256='a' * 64,
                      bundle_sha256='b' * 64, source_commit='c' * 40,
                      controller_sha256=hashlib.sha256(Path(self.remote.__file__).read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, 'bundle_pin'):
            self.remote.reviewed(path, review)

    def test_root_installer_refuses_bad_hash_before_touching_system_paths(self):
        path = self.root / 'bundle'
        path.write_bytes(b'untrusted')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', self.remote.INSTALLER,
            str(path), 'a' * 64, 'b' * 64, '[]'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('AssertionError', result.stderr)


class RepairSetupTests(unittest.TestCase):
    def setUp(self):
        import repair_setup
        self.repair = repair_setup
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_repair_requires_the_exact_original_plan(self):
        with patch.object(setup.reconcile.contract, 'read_json', return_value={
                'plan_sha256': '0' * 64, 'policy': policy()}):
            with self.assertRaisesRegex(setup.reconcile.Refused, 'original_plan_binding'):
                self.repair.plan(policy(), self.root)

    def test_repair_rejects_a_different_original_intent_before_cloud_or_disk_actions(self):
        with patch.object(setup.reconcile.contract, 'read_json', side_effect=[{'wrong':True}, {'expected':True}]), \
                patch.object(setup, 'cloud_device') as cloud:
            with self.assertRaisesRegex(setup.reconcile.Refused, 'original_intent_differs'):
                self.repair.partial_state(policy(), {})
        cloud.assert_not_called()

    def execute(self, *, interrupted=False, installation_fails=False):
        from contextlib import ExitStack
        rows = [dict(name=name, filename=name+'.deb') for name in
                ('libjansson4', 'libnftables1', 'nftables', 'docker-ce')]
        expected = dict(plan_sha256='a'*64, sources={}, packages=rows)
        state = self.root/'state'; state.mkdir(mode=0o700); (state/'lock').touch()
        if interrupted: (state/'repair-intent.json').write_text('{}')
        commands = []
        def run(command, **kwargs):
            commands.append(command)
            if installation_fails and command[0] == '/usr/bin/dpkg':
                raise setup.reconcile.Refused('fixture_installation_failure')
            return b''
        with ExitStack() as stack:
            for target, attribute, value in (
                (self.repair.sys, 'platform', 'linux'), (self.repair.os, 'geteuid', lambda: 0),
                (setup.platform, 'machine', lambda: 'x86_64'), (setup, 'STATE', state),
                (self.repair, 'BLOCKER', self.root/'policy-rc.d'),
                (setup.reconcile, 'protected', lambda p, **kw: Path(p)),
                (setup.reconcile.contract, 'read_json', lambda p: policy()),
                (self.repair, 'plan', lambda *a: expected), (self.repair, 'partial_state', lambda *a: None),
                (setup, 'packages', lambda *a: rows), (setup, 'package_probe', lambda *a: None),
                (setup, 'run', run), (setup, 'verify', lambda *a: dict(plan_sha256='a'*64))):
                stack.enter_context(patch.object(target, attribute, value))
            result = self.repair.apply(self.root/'policy.json', self.root, 'a'*64)
        return commands, result

    def test_repair_only_installs_missing_packages_and_never_formats(self):
        commands, result = self.execute()
        self.assertEqual([c for c in commands if c[0]=='/usr/bin/dpkg'], [
            ['/usr/bin/dpkg', '--force-confold', '--install',
             *[str(self.root/(name+'.deb')) for name in ('libjansson4','libnftables1','nftables')]],
            ['/usr/bin/dpkg', '--configure', 'docker-ce']])
        self.assertFalse(any('mkfs' in c[0] or 'wipefs' in c[0] for c in commands))
        self.assertIn('recovered_from_plan_sha256', result)
        self.assertFalse((self.root/'policy-rc.d').exists())
        self.assertTrue((self.root/'state/completed.json').exists())

    def test_interrupted_repair_refuses_and_never_replays_installation(self):
        with self.assertRaisesRegex(setup.reconcile.Refused, 'interrupted_requires_reconciliation'):
            self.execute(interrupted=True)
        self.assertFalse((self.root/'state/completed.json').exists())

    def test_package_failure_retains_intent_and_removes_temporary_service_blocker(self):
        with self.assertRaisesRegex(setup.reconcile.Refused, 'fixture_installation_failure'):
            self.execute(installation_fails=True)
        self.assertTrue((self.root/'state/repair-intent.json').exists())
        self.assertFalse((self.root/'state/completed.json').exists())
        self.assertFalse((self.root/'policy-rc.d').exists())


class FinalizeSetupTests(unittest.TestCase):
    def setUp(self):
        import finalize_setup
        self.finalize = finalize_setup
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_discovery_is_disabled_without_overriding_dns_servers(self):
        self.assertEqual(setup.files(policy())[str(setup.RESOLVED)],
                         ('[Resolve]\nLLMNR=no\nMulticastDNS=no\n', 0o644))

    def test_only_identified_resolver_listener_can_be_corrected(self):
        error = setup.reconcile.Refused('unexpected_public_listener')
        for address, port, process, allowed in (
                ('0.0.0.0',5355,'systemd-resolve',True),
                ('0.0.0.0',8000,'systemd-resolve',False),
                ('0.0.0.0',5355,'other-daemon',False)):
            error.diagnostic = dict(stage='host_network_listener_check',address=address,port=port)
            line = f'LISTEN 0 4096 {address}:{port} 0.0.0.0:* users:(("{process}",pid=1,fd=1))\n'
            with patch.object(setup.reconcile.contract,'read_json',return_value={}), \
                    patch.object(setup,'verify',side_effect=error), \
                    patch.object(setup,'run',return_value=line.encode()), \
                    patch.object(self.finalize,'RESOLVED',self.root/'new.conf'):
                if allowed:
                    self.finalize.before_change(policy(),{})
                else:
                    with self.assertRaises(setup.reconcile.Refused):
                        self.finalize.before_change(policy(),{})

    def test_existing_resolver_override_is_never_replaced(self):
        path=self.root/'existing.conf';path.write_text('[Resolve]\nDNS=192.0.2.1\n')
        with patch.object(setup.reconcile.contract,'read_json',return_value={}), \
                patch.object(setup,'verify',return_value={}), \
                patch.object(setup.reconcile,'protected',return_value=path), \
                patch.object(self.finalize,'RESOLVED',path):
            with self.assertRaisesRegex(setup.reconcile.Refused,'existing_resolver_override'):
                self.finalize.before_change(policy(),{})
        self.assertEqual(path.read_text(),'[Resolve]\nDNS=192.0.2.1\n')


if __name__ == '__main__':
    unittest.main()
