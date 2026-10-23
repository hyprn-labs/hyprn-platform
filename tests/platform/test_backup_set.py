"""Real SQLite/AiiDA + existing managed-backup HTTP fixture, not a Linux/cloud drill."""
import fcntl
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = Path(os.environ['HYPRN_MVP_SOURCE_ROOT']).resolve()


def module(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(specification)
    sys.modules[name] = result
    specification.loader.exec_module(result)
    return result


subject = module('hyprn_backup_set_test_subject', ROOT / 'host/backup_set.py')
owner_tests = module('hyprn_backup_set_owner_fixture', PRODUCT / 'deployment/tests/test_hosted_backup.py')
provider_tests = module('hyprn_backup_set_provider_fixture', ROOT / 'tests/platform/test_cloudsql_backup.py')


class SchemaReceiptTests(unittest.TestCase):
    def test_retained_platform_requires_explicit_identity_and_identical_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            old, new = root / 'old', root / 'new'
            for base in (old, new):
                for name in ('host/contract.py', 'contracts/v1/deployment.schema.json'):
                    path = base / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'identical pinned contract')
                    path.chmod(0o644)
            specification = dict(platform_root=str(old))
            with patch.object(subject, 'HOST', new / 'host'), patch.object(
                    subject, 'secure_path', side_effect=lambda path, **kwargs: Path(path)):
                with self.assertRaisesRegex(subject.Invalid, 'backup_platform_source'):
                    subject.retained_platform(specification)
                with self.assertRaisesRegex(subject.Invalid, 'backup_platform_source'):
                    subject.retained_platform(specification, new)
                self.assertEqual(subject.retained_platform(specification, old), old)
                for name in ('host/contract.py', 'contracts/v1/deployment.schema.json'):
                    path = old / name
                    before = path.read_bytes()
                    path.write_bytes(b'changed contract')
                    with self.assertRaisesRegex(subject.Invalid, 'backup_platform_contract_changed'):
                        subject.retained_platform(specification, old)
                    path.write_bytes(before)

    def test_successful_inspection_is_not_represented_as_a_drain(self):
        for operation in ('inspect', 'drain'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                root.chmod(0o700)
                lifecycle = SimpleNamespace(root=root, identity={'installation_id': 'fixture'},
                                            binding={'schema': 'fixture'})
                identifier = '00000000-0000-4000-8000-000000000002'
                path = root / ('operation-' + identifier + '.json')
                result = dict(operation=operation, operation_id=identifier,
                              installation_id='fixture',
                              status='success', reason_code='completed', evidence_refs=[path.name],
                              observed_schema_versions={'application': 'retained-schema'})
                value = dict(identity_sha256=subject.digest(dict(identity=lifecycle.identity,
                             binding=lifecycle.binding, operation=operation,
                             surface=None, state=None)),
                             state='complete', exit_code=0, result=result)
                path.write_text(json.dumps(value))
                path.chmod(0o600)
                key = operation + '_operation_id'
                selected, receipt, schemas = subject.schema_receipt(lifecycle, **{key: identifier})
                self.assertEqual(selected, operation)
                self.assertEqual(receipt, value)
                self.assertEqual(schemas, result['observed_schema_versions'])
                self.assertEqual(json.loads(path.read_text()), value)
                other = ('drain' if operation == 'inspect' else 'inspect') + '_operation_id'
                with self.assertRaises(subject.Invalid):
                    subject.schema_receipt(lifecycle, **{other: identifier})
                value['result']['status'] = 'failed'
                path.write_text(json.dumps(value))
                with self.assertRaises(subject.Invalid):
                    subject.schema_receipt(lifecycle, **{key: identifier})

    def test_old_product_stop_assertions_are_supplemented_with_detached_worker_checks(self):
        from unittest.mock import Mock
        lifecycle = SimpleNamespace(runtime={'installation_id': 'fixture'},
                                    assert_stopped=Mock(), remaining=lambda: 20)
        with patch.object(subject.subprocess, 'run') as run:
            run.return_value = SimpleNamespace(returncode=0, stdout='')
            subject.stopped_owners(lifecycle)
            lifecycle.assert_stopped.assert_called_once_with()
            self.assertIn('label=org.hyprn-mvp.owner=hyprn-mvp-cloud-fixture',
                          run.call_args.args[0])
            for result in (SimpleNamespace(returncode=0, stdout='running-worker'),
                           SimpleNamespace(returncode=1, stdout='')):
                run.return_value = result
                with self.assertRaises(subject.Invalid):
                    subject.stopped_owners(lifecycle)

    def test_provider_polling_uses_remaining_budget_without_exceeding_provider_bounds(self):
        for remaining, attempts in ((1200, 20), (300, 20), (26, 5), (5, 1), (0.1, 1)):
            with self.subTest(remaining=remaining):
                actual = subject.provider_polling(remaining)
                self.assertEqual(actual, dict(poll_attempts=attempts, poll_seconds=5))
                self.assertLess((actual['poll_attempts'] - 1) * actual['poll_seconds'], remaining)
                self.assertLessEqual(actual['poll_attempts'], 20)
        for remaining in (0, -1, True, float('inf'), float('nan')):
            with self.assertRaises(subject.Invalid):
                subject.provider_polling(remaining)

    def test_schema_receipt_selection_is_explicit_and_exclusive(self):
        with self.assertRaises(subject.Invalid):
            subject.schema_receipt(None)
        with self.assertRaises(subject.Invalid):
            subject.schema_receipt(None, drain_operation_id='one', inspect_operation_id='two')


class CombinedTests(unittest.TestCase):
    def setUp(self):
        self.old_umask = os.umask(0o077)
        self.addCleanup(os.umask, self.old_umask)
        self.owner_fixture = owner_tests.OwnerSnapshotTests()
        self.addCleanup(self.owner_fixture.doCleanups)
        self.owner_fixture.setUp()
        for connection in self.owner_fixture.connections:
            connection.close()
        self.provider = provider_tests.BackupTests()
        self.addCleanup(self.provider.doCleanups)
        self.provider.setUp()
        self.endpoint = dict(host='10.20.0.3', server_name='fixture.europe-west1.sql-psa.goog')
        self.provider.instance_patch = dict(ipAddresses=[dict(type='PRIVATE', ipAddress=self.endpoint['host'])],
            dnsNames=[dict(name=self.endpoint['server_name'] + '.', connectionType='PRIVATE_SERVICES_ACCESS', dnsScope='INSTANCE')])
        self.root = self.owner_fixture.root
        self.set_root = self.root / 'coherent-set'
        self.set_root.mkdir(mode=0o700)
        self.provider.private = self.set_root / 'database'
        self.lock_path = self.root / 'deployment.lock'
        self.lock = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(os.close, self.lock)
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.fence = subject.DeploymentFence(self.lock, self.lock_path)
        identity = self.owner_fixture.identity
        self.args = SimpleNamespace(command='create', state_root=str(self.set_root),
            project_id=provider_tests.PROJECT, project_number='123456789012',
            instance=provider_tests.INSTANCE, private_network='projects/' + provider_tests.PROJECT + '/global/networks/fixture-net',
            installation_id=identity['installation_id'], release_digest='sha256:' + identity['release_sha256'],
            configuration_digest='sha256:' + identity['config_sha256'],
            operation_id='00000000-0000-4000-8000-000000000001', approve_resource=provider_tests.RESOURCE,
            poll_attempts=2, poll_seconds=0)
        self.inspections = 0
        self.timeout = 60
        self.on_inspection = None
        self.on_request = None
        original = http.client.HTTPConnection
        outer = self

        class Connection(original):
            def request(self, method, url, *args, **kwargs):
                if outer.on_request is not None:
                    outer.on_request(method, url)
                return super().request(method, url, *args, **kwargs)

        def connect(expected):
            def factory(host, **kwargs):
                self.assertEqual(host, expected)
                return Connection('127.0.0.1', self.provider.server.server_port, **kwargs)
            return factory
        self.metadata = patch.object(subject.sql.http.client, 'HTTPConnection', connect('169.254.169.254'))
        self.api = patch.object(subject.sql.http.client, 'HTTPSConnection', connect('sqladmin.googleapis.com'))
        self.metadata.start()
        self.api.start()
        self.addCleanup(self.metadata.stop)
        self.addCleanup(self.api.stop)

    def stopped(self):
        # Fixture owners have closed every DB connection and have no service
        # process. Production uses Lifecycle.assert_stopped, tested separately.
        self.inspections += 1
        if self.on_inspection is not None:
            self.on_inspection(self.inspections)

    def run_set(self):
        fixture = self.owner_fixture
        return subject.assemble(files=owner_tests.backup, args=self.args, roots=fixture.roots,
            identity=fixture.identity, owner=fixture.owner,
            schemas={'application': 'fixture-schema', 'modeling': 'fixture-schema'},
            source={'source_commit': 'c' * 40, 'modules': {'cloud_backup.py': hashlib.sha256(
                (PRODUCT / 'deployment/cloud_backup.py').read_bytes()).hexdigest()}},
            fence=self.fence, assert_stopped=self.stopped,
            receipts={'stop': {'fixture': 'stopped-local-owners'}, 'drain': {'fixture': 'no-processes'}}, timeout=self.timeout, expected_endpoint=self.endpoint)

    def incomplete(self):
        self.assertFalse((self.set_root / 'manifest.json').exists())
        value = json.loads((self.set_root / 'failed.json').read_bytes())
        self.assertFalse(value['coherent_installation_backup'])

    def test_managed_backup_and_real_native_snapshot_hold_locks_and_roundtrip(self):
        checked = []
        def request(method, path):
            if method != 'POST':
                return
            for lock in (self.lock_path, self.owner_fixture.roots['execution'] / 'executor.lock'):
                descriptor = os.open(lock, os.O_RDWR)
                try:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                finally:
                    os.close(descriptor)
            script = """import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import cloud_backup
from aiida.manage.profile_access import ProfileAccessManager
from aiida.common.exceptions import LockedProfileError
root=Path(sys.argv[2]);os.environ['AIIDA_PATH']=str(root/'aiida')
try: ProfileAccessManager(cloud_backup.profile_at(root,sys.argv[3])).request_access()
except LockedProfileError: sys.exit(23)
"""
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script,
                str(PRODUCT / 'deployment'), str(self.owner_fixture.roots['execution']), self.owner_fixture.profile.name],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 23, result.stderr)
            checked.append(True)
        self.on_request = request
        manifest = self.run_set()
        self.assertEqual(checked, [True])
        self.assertTrue(manifest['coherent_installation_backup'])
        self.assertEqual(manifest['status'], 'complete')
        self.assertEqual(manifest['managed_database']['resource'], provider_tests.RESOURCE + '/backupRuns/42')
        self.assertEqual(manifest['managed_database']['metadata_sha256'], subject.digest(manifest['managed_database']['metadata']))
        self.assertGreaterEqual(self.inspections, 5)
        self.assertEqual(manifest, json.loads((self.set_root / 'manifest.json').read_bytes()))
        files = json.loads((self.set_root / 'owner-files/manifest.json').read_bytes())
        self.assertEqual(subject.digest(files), manifest['owner_files']['manifest_sha256'])
        self.assertFalse(files['coherent_backup'])
        self.assertFalse(manifest['managed_database']['metadata']['coherent_installation_backup'])
        self.assertNotIn(provider_tests.SECRET, (self.set_root / 'manifest.json').read_text())
        subject.verify_output_authority(self.set_root)
        fixture = self.owner_fixture
        fixture.empty_original_paths()
        owner_tests.backup.restore_files(self.set_root / 'owner-files', roots=fixture.roots,
                                         identity=fixture.identity, owner=fixture.owner, timeout=60)
        self.assertEqual((fixture.roots['artifacts'] / 'historical.bin').read_bytes(), b'\x00\x01exact retained output\xff')
        # The existing native adapter verifies all retained AiiDA objects during restore.
        self.assertTrue((fixture.roots['execution'] / 'profile-identity.json').is_file())
        self.assertFalse((fixture.roots['execution'] / 'evidence/containment.json').exists())

    def test_lost_provider_response_reconciles_read_only_under_original_hold(self):
        self.provider.mode = 'lost'
        self.assertTrue(self.run_set()['coherent_installation_backup'])
        self.assertEqual(len(self.provider.posts()), 1)
        self.assertGreaterEqual(len([call for call in self.provider.calls if '/backupRuns?' in call[1]]), 1)

    def test_lost_deployment_hold_invalidates_successful_database_member(self):
        def release(method, path):
            if method == 'POST':
                fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.on_request = release
        with self.assertRaisesRegex(subject.Invalid, 'deployment_hold_lost'):
            self.run_set()
        self.assertTrue((self.set_root / 'database/receipt.json').exists())
        self.incomplete()
        with self.assertRaisesRegex(subject.Invalid, 'new_scope'):
            self.run_set()
        self.assertEqual(len(self.provider.posts()), 1)
        # Losing the coherent hold must still permit a separate database-only
        # GET reconciliation against the intent's original endpoint binding.
        standalone = SimpleNamespace(**dict(vars(self.args), command='resume',
                                           state_root=str(self.set_root / 'database')))
        managed = subject.sql.backup(standalone)
        self.assertEqual(managed['source']['endpoint'], self.endpoint)
        self.assertFalse(managed['coherent_installation_backup'])
        self.assertEqual(len(self.provider.posts()), 1)
        self.incomplete()

    def test_restarted_writer_invalidates_successful_database_member(self):
        def inspect(count):
            if count == 3:
                raise subject.Invalid('fixture_writer_running')
        self.on_inspection = inspect
        with self.assertRaisesRegex(subject.Invalid, 'writer_running'):
            self.run_set()
        self.assertTrue((self.set_root / 'database/receipt.json').exists())
        self.incomplete()

    def test_expired_native_hold_never_publishes_complete_manifest(self):
        self.timeout = 0.000001
        with self.assertRaises(TimeoutError):
            self.run_set()
        self.incomplete()

    def test_native_lock_conflict_prevents_provider_dispatch(self):
        native = os.open(self.owner_fixture.roots['execution'] / 'executor.lock', os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(native, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.run_set()
        finally:
            os.close(native)
        self.incomplete()
        self.assertEqual(self.provider.posts(), [])

    def test_corrupt_native_object_never_becomes_complete_backup(self):
        container = self.owner_fixture.roots['execution'] / 'aiida-store/container'
        loose = next(path for path in (container / 'loose').rglob('*') if path.is_file()
                     and hashlib.sha256(path.read_bytes()).hexdigest() == self.owner_fixture.loose_hash)
        loose.write_bytes(b'corrupt retained content')
        with self.assertRaisesRegex(ValueError, 'object bytes'):
            self.run_set()
        self.incomplete()
        self.assertFalse((self.set_root / 'owner-files/manifest.json').exists())

    def test_unsafe_owner_filename_cannot_publish_complete_manifest(self):
        (self.owner_fixture.roots['artifacts'] / 'unsafe\\name').write_bytes(b'retained')
        with self.assertRaisesRegex(ValueError, 'Unsafe snapshot entry'):
            self.run_set()
        self.incomplete()

    def test_managed_receipt_tampering_is_detected_before_owner_snapshot(self):
        def inspect(count):
            if count == 3:
                path = self.set_root / 'database/receipt.json'
                value = json.loads(path.read_bytes())
                value['resource'] += '0'
                path.write_text(json.dumps(value))
        self.on_inspection = inspect
        with self.assertRaisesRegex(subject.Invalid, 'database_receipt'):
            self.run_set()
        self.incomplete()
        self.assertFalse((self.set_root / 'owner-files').exists())

    def test_ambiguous_provider_reference_never_reposts_or_snapshots(self):
        self.provider.mode = 'ambiguous'
        with self.assertRaisesRegex(subject.Invalid, 'backup_ambiguous'):
            self.run_set()
        self.incomplete()
        self.assertEqual(len(self.provider.posts()), 1)
        self.assertFalse((self.set_root / 'owner-files').exists())

    def test_private_database_endpoint_mismatch_refuses_before_provider_post(self):
        self.provider.instance_patch['ipAddresses'][0]['ipAddress'] = '10.20.0.4'
        with self.assertRaisesRegex(subject.Invalid, 'source_endpoint_mismatch'):
            self.run_set()
        self.incomplete()
        self.assertEqual(self.provider.posts(), [])

    def test_cluster_dns_cannot_stand_in_for_exact_instance_identity(self):
        self.provider.instance_patch['dnsNames'][0]['dnsScope'] = 'CLUSTER'
        with self.assertRaisesRegex(subject.Invalid, 'source_endpoint_mismatch'):
            self.run_set()
        self.incomplete()
        self.assertEqual(self.provider.posts(), [])

    def test_wrong_tls_server_name_refuses_before_provider_post(self):
        self.provider.instance_patch['dnsNames'][0]['name'] = 'different.europe-west1.sql-psa.goog.'
        with self.assertRaisesRegex(subject.Invalid, 'source_endpoint_mismatch'):
            self.run_set()
        self.incomplete()
        self.assertEqual(self.provider.posts(), [])

    def test_approval_and_binding_failure_cannot_dispatch(self):
        self.args.approve_resource = 'projects/foreign/instances/foreign'
        with self.assertRaisesRegex(subject.Invalid, 'explicit_backup_approval_required'):
            self.run_set()
        self.incomplete()
        self.assertEqual(self.provider.posts(), [])


class ReceiptTests(unittest.TestCase):
    def test_receipt_requires_exact_binding_complete_operation_and_private_file(self):
        with tempfile.TemporaryDirectory(prefix='backup-receipt-') as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            lifecycle = SimpleNamespace(root=root, identity={'installation_id': 'fixture'}, binding={'pin': 'exact'})
            operation = '00000000-0000-4000-8000-000000000001'
            path = root / ('operation-' + operation + '.json')
            value = dict(identity_sha256=subject.digest(dict(identity=lifecycle.identity, binding=lifecycle.binding,
                operation='stop', surface=None, state=None)), state='complete', exit_code=0,
                result=dict(operation='stop', operation_id=operation, installation_id='fixture',
                            status='success', reason_code='completed', evidence_refs=[path.name]))
            path.write_bytes(subject.sql.canonical(value))
            path.chmod(0o600)
            self.assertEqual(subject.receipt(lifecycle, 'stop', operation), value)
            with self.assertRaisesRegex(subject.Invalid, 'stopped_receipt'):
                subject.receipt(lifecycle, 'drain', operation)
            path.chmod(0o644)
            with self.assertRaisesRegex(subject.Invalid, 'file_authority'):
                subject.receipt(lifecycle, 'stop', operation)

    def test_real_cli_refuses_unqualified_host_before_loading_product_or_cloud(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'host/backup_set.py'),
            '--binding', '/nonexistent', '--deployment-fd', '42', '--fence-channel', '43',
            '--deployment-path', '/nonexistent', '--operation-id', 'invalid', '--state-root', '/nonexistent',
            '--stop-operation-id', 'invalid', '--drain-operation-id', 'invalid', '--approve-resource', 'invalid',
            '--backup-policy', '/nonexistent'],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        reason = 'backup_set_incomplete' if sys.platform == 'linux' and os.geteuid() == 0 else 'backup_linux_root_required'
        self.assertEqual(json.loads(result.stderr), {'error': reason})


if __name__ == '__main__':
    unittest.main()
