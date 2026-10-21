"""Durable orchestration tests; external host/product adapters are explicit doubles."""
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import reconcile


class JournalTests(unittest.TestCase):
    def test_same_sequence_cannot_change_desired_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = reconcile.Journal(Path(directory))
            with journal.lock():
                journal.accept(7, 'a' * 64)
            with journal.lock(), self.assertRaisesRegex(reconcile.Refused, 'sequence_conflict'):
                journal.accept(7, 'b' * 64)




from contextlib import contextmanager
import copy
import hashlib
import json
import os
import subprocess


class ProductBoundary:
    """A protocol peer double, not evidence that product stores work."""
    def __init__(self, target):
        self.target = target
        self.calls = []
        self.fail = None

    def preflight(self):
        self.target.unchanged()

    def compatibility(self, target):
        pass  # Explicit protocol peer; no live-owner compatibility claimed.

    def call(self, operation, operation_id, **_kwargs):
        self.calls.append(operation)
        if operation == self.fail:
            raise reconcile.Refused('operation_outcome_uncertain')
        return {'operation_id': operation_id, 'operation': operation,
                'installation_id': self.target.runtime['installation_id'],
                'status': 'success', 'reason_code': 'completed',
                'observed_schema_versions': None, 'evidence_refs': []}


class HostBoundary:
    """External metadata/kernel/GCS boundary; never used by production wiring."""
    def __init__(self):
        self.boot = 'boot-a'
        self.reject = None

    def check(self):
        if self.reject:
            raise reconcile.Refused(self.reject)
        return {'host_id': 'host-a', 'instance_id': '123', 'boot_id': self.boot, 'disk_uuid': 'disk-a'}

    def desired(self):
        return '12345'


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(prefix='hyprn-reconcile-')
        self.addCleanup(self.scope.cleanup)
        self.root = Path(self.scope.name)
        self.control = self.root / 'control'
        self.control.mkdir()
        self.journal = reconcile.Journal(self.root)
        self.host = HostBoundary()
        self.target = self.make_target(1)
        self.product = ProductBoundary(self.target)

    def make_target(self, sequence, mutate=None):
        directory = self.root / ('release-' + str(sequence))
        directory.mkdir()
        documents = copy.deepcopy(json.loads((ROOT / 'contracts/v1/fixtures.json').read_text())['valid'])
        release, runtime = documents['release'], documents['runtime']
        release['platform_contract']['schema_sha256'] = hashlib.sha256(reconcile.contract.SCHEMA_PATH.read_bytes()).hexdigest()
        release['platform_contract']['renderer_sha256'] = hashlib.sha256((ROOT / 'host/contract.py').read_bytes()).hexdigest()
        if mutate:
            mutate(documents)
        documents['desired']['sequence'] = sequence
        documents['desired']['release_sha256'] = reconcile.contract.digest(release)
        documents['desired']['config_sha256'] = reconcile.contract.digest(reconcile.contract.render(release, runtime))
        for name, value in documents.items():
            (directory / (name + '.json')).write_text(json.dumps(value))
        binding = {'schema': 'hyprn-product-binding/v1', 'platform_root': str(ROOT),
                   'control_root': str(self.control), 'payload_inventory': str(directory / 'payload.json'),
                   **{key: str(directory / (key + '.json')) for key in ('workload', 'release', 'runtime', 'desired')}}
        path = directory / 'binding.json'
        path.write_text(json.dumps(binding))
        return reconcile.Target(path)

    @contextmanager
    def migration(self, target):
        yield target.path

    def run_reconcile(self, product=None, **kwargs):
        product = product or self.product
        return reconcile.reconcile(product.target, journal=self.journal, host=self.host,
                                   product=product, migration_scope=self.migration,
                                   minimum_free_bytes=1, **kwargs)

    def record(self):
        with self.journal.lock():
            return self.journal.read()

    def test_initial_installation_stays_closed_and_does_not_claim_applied(self):
        result = self.run_reconcile(initialize=True)
        self.assertEqual(result, {'status': 'qualification_pending', 'admission': 'closed', 'sequence': 1})
        self.assertEqual(self.record()['migration']['state'], 'complete')
        admission = json.loads((self.control / 'admission.json').read_text())
        self.assertFalse(admission['browser'])
        self.assertFalse(admission['scientific'])
        self.assertEqual(os.stat(self.control / 'runtime-identity.json').st_mode & 0o777, 0o644)

    def test_repeating_installed_sequence_does_not_repeat_product_mutation(self):
        self.run_reconcile(initialize=True)
        calls = list(self.product.calls)
        self.run_reconcile(initialize=True)
        self.assertEqual(self.product.calls, calls)

    def test_second_sequence_requires_backup_before_mutation(self):
        self.run_reconcile(initialize=True)
        candidate = ProductBoundary(self.make_target(2))
        with self.assertRaisesRegex(reconcile.Refused, 'coherent_backup_adapter_required'):
            self.run_reconcile(candidate, active_product=self.product)
        self.assertNotIn('migrate', candidate.calls)
        self.assertEqual(self.record()['installed']['binding_sha256'], self.target.binding_sha256)
        self.assertEqual(json.loads((self.control / 'runtime-identity.json').read_text()), self.target.identity)

    def test_second_closed_activation_records_backup_and_new_binding(self):
        self.run_reconcile(initialize=True)
        candidate = ProductBoundary(self.make_target(2))
        def backup(active, journal, operations, check):
            self.assertEqual(operations['stop']['state'], 'complete')
            self.assertEqual(operations['drain']['state'], 'complete')
            self.assertIsNotNone(journal.fd)
            check()
            return {'test_protocol_peer': 'not-a-real-backup'}
        self.run_reconcile(candidate, active_product=self.product, backup=backup)
        self.assertIn('migrate', candidate.calls)
        self.assertEqual(self.record()['installed']['binding_sha256'], candidate.target.binding_sha256)
        self.assertEqual(self.record()['stage'], 'installed_closed')

    def test_ambiguous_migration_never_retries_even_with_higher_sequence(self):
        self.product.fail = 'initialize'
        with self.assertRaisesRegex(reconcile.Refused, 'operation_outcome_uncertain'):
            self.run_reconcile(initialize=True)
        first = self.record()
        self.assertTrue(first['mutation'])
        self.assertEqual(first['migration']['state'], 'intent')
        self.assertIsNone(first['installed'])
        candidate = ProductBoundary(self.make_target(2))
        with self.assertRaisesRegex(reconcile.Refused, 'operator_recovery_required'):
            self.run_reconcile(candidate, initialize=True)
        self.assertEqual(candidate.calls, [])

    def test_failed_native_qualification_never_starts_the_product(self):
        self.product.fail = 'qualify'
        with self.assertRaises(reconcile.Refused):
            self.run_reconcile(initialize=True)
        self.assertNotIn('start', self.product.calls)
        self.assertEqual(self.record()['migration']['state'], 'complete')
        self.assertEqual(self.record()['stage'], 'qualifying')

    def test_mount_drift_blocks_all_product_operations(self):
        self.host.reject = 'store_mount_identity_mismatch'
        with self.assertRaisesRegex(reconcile.Refused, 'store_mount_identity_mismatch'):
            self.run_reconcile(initialize=True)
        self.assertEqual(self.product.calls, [])
        self.assertFalse(self.journal.path.exists())

    def test_full_disk_blocks_before_identity_creation(self):
        with self.assertRaisesRegex(reconcile.Refused, 'insufficient_disk_space'):
            reconcile.reconcile(self.target, journal=self.journal, host=self.host,
                product=self.product, migration_scope=self.migration,
                initialize=True, minimum_free_bytes=10**30)
        self.assertFalse((self.control / 'runtime-identity.json').exists())

    def test_initialization_requires_explicit_action(self):
        with self.assertRaisesRegex(reconcile.Refused, 'explicit_initialization_required'):
            self.run_reconcile()
        self.assertEqual(self.product.calls, [])

    def test_changed_store_contract_refuses_unproven_compatibility(self):
        self.run_reconcile(initialize=True)
        def mutation(documents):
            documents['release']['stores']['execution']['read_max'] = 2
        candidate = ProductBoundary(self.make_target(2, mutation))
        with self.assertRaisesRegex(reconcile.Refused, 'owner_schema_compatibility_unproven'):
            self.run_reconcile(candidate, active_product=self.product)
        self.assertEqual(candidate.calls, [])

    def test_changed_store_identity_refuses_before_drain(self):
        self.run_reconcile(initialize=True)
        def mutation(documents):
            documents['runtime']['store_ids']['application'] = 'other-application'
        candidate = ProductBoundary(self.make_target(2, mutation))
        old_calls = list(self.product.calls)
        with self.assertRaisesRegex(reconcile.Refused, 'installation_identity_changed'):
            self.run_reconcile(candidate, active_product=self.product)
        self.assertEqual(self.product.calls, old_calls)

    def test_descriptor_changes_after_validation_are_detected(self):
        desired = Path(self.target.binding['desired'])
        value = json.loads(desired.read_text())
        value['sequence'] = 3
        desired.write_text(json.dumps(value))
        with self.assertRaisesRegex(reconcile.Refused, 'staged_documents_changed'):
            self.run_reconcile(initialize=True)
        self.assertEqual(self.product.calls, [])

    def test_backup_failure_never_switches_active_identity(self):
        self.run_reconcile(initialize=True)
        candidate = ProductBoundary(self.make_target(2))
        def failed(*_args):
            raise reconcile.Refused('backup_partial')
        with self.assertRaisesRegex(reconcile.Refused, 'backup_partial'):
            self.run_reconcile(candidate, active_product=self.product, backup=failed)
        self.assertFalse(self.record()['mutation'])
        self.assertEqual(json.loads((self.control / 'runtime-identity.json').read_text()), self.target.identity)

    def test_fence_loss_during_backup_blocks_migration(self):
        self.run_reconcile(initialize=True)
        candidate = ProductBoundary(self.make_target(2))
        def lost(*_args):
            self.host.boot = 'boot-b'
            return {'test_protocol_peer': 'not-a-real-backup'}
        with self.assertRaisesRegex(reconcile.Refused, 'host_fence_changed'):
            self.run_reconcile(candidate, active_product=self.product, backup=lost)
        self.assertNotIn('migrate', candidate.calls)


class BoundaryTests(unittest.TestCase):
    def test_two_processes_cannot_own_deployment_lock(self):
        with tempfile.TemporaryDirectory(prefix='hyprn-lock-') as directory:
            journal = reconcile.Journal(directory)
            code = "import sys; sys.path.insert(0, sys.argv[1]); import reconcile\ntry:\n with reconcile.Journal(sys.argv[2]).lock(): pass\nexcept reconcile.Refused: sys.exit(4)"
            with journal.lock():
                result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT / 'host'), directory], timeout=10)
            self.assertEqual(result.returncode, 4)

    def test_timeout_refuses_uncertain_result(self):
        with self.assertRaisesRegex(reconcile.Refused, 'operation_outcome_uncertain'):
            reconcile.bounded([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=0.05)

    def test_excessive_output_is_bounded(self):
        with self.assertRaisesRegex(reconcile.Refused, 'operation_output_invalid'):
            reconcile.bounded([sys.executable, '-c', 'print("x" * 3000000)'], timeout=5)

    def test_child_failure_never_exposes_payload(self):
        with self.assertRaisesRegex(reconcile.Refused, '^operation_refused$'):
            reconcile.bounded([sys.executable, '-c', 'print("secret-payload"); raise SystemExit(6)'], timeout=5)

    def test_duplicate_product_fields_are_rejected(self):
        with self.assertRaisesRegex(reconcile.Refused, 'invalid_json'):
            reconcile.decode(b'{"status":"success","status":"failed"}')

    def test_stale_sequence_is_rejected_across_new_journal_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            with reconcile.Journal(directory).lock() as first:
                first.accept(3, 'a' * 64)
            with reconcile.Journal(directory).lock() as second:
                with self.assertRaisesRegex(reconcile.Refused, 'stale_sequence'):
                    second.accept(2, 'a' * 64)

    def test_corrupt_journal_is_not_treated_as_empty_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = reconcile.Journal(directory)
            reconcile.atomic(journal.path, {'stage': 'applied'})
            with journal.lock(), self.assertRaisesRegex(reconcile.Refused, 'journal_corrupt'):
                journal.accept(3, 'a' * 64)


class HTTPBoundaryTests(unittest.TestCase):
    setUp = ReconcileTests.setUp
    make_target = ReconcileTests.make_target
    # Only the HTTP boundary is substituted. Reuse fixture setup but avoid
    # inheriting protocol journey tests into this class's test inventory.
    def response(self, status, body):
        class Response:
            def read(self, _maximum):
                return body
        response = Response()
        response.status = status
        return response

    def test_desired_content_is_requested_at_checked_generation(self):
        from unittest.mock import patch
        requests = []
        target = self.target
        responses = iter([self.response(200, json.dumps({
            'bucket': target.runtime['desired_bucket'], 'name': 'current.json', 'generation': '779'}).encode()),
            self.response(200, reconcile.contract.canonical(target.desired))])
        class Connection:
            def __init__(self, host, timeout):
                self.host = host
            def request(self, method, path, headers):
                requests.append((self.host, method, path))
            def getresponse(self):
                return next(responses)
            def close(self):
                pass
        host = reconcile.GoogleHost(target, disk_name='test-disk')
        host.principal.token = 'nonsecret-test-peer'
        with patch.object(reconcile.http.client, 'HTTPSConnection', Connection):
            self.assertEqual(host.desired(), '779')
        self.assertEqual(len(requests), 2)
        self.assertTrue(all(item[0] == 'storage.googleapis.com' and item[1] == 'GET' for item in requests))
        self.assertTrue(requests[1][2].endswith('?alt=media&generation=779'))

    def test_google_redirects_are_refused(self):
        from unittest.mock import patch
        response = self.response(302, b'{}')
        class Connection:
            def __init__(self, *_args, **_kwargs):
                pass
            def request(self, *_args, **_kwargs):
                pass
            def getresponse(self):
                return response
            def close(self):
                pass
        host = reconcile.GoogleHost(self.target, disk_name='test-disk')
        host.principal.token = 'nonsecret-test-peer'
        with patch.object(reconcile.http.client, 'HTTPSConnection', Connection):
            with self.assertRaisesRegex(reconcile.Refused, 'host_observation_unavailable'):
                host.desired()


if __name__ == '__main__':
    unittest.main()
