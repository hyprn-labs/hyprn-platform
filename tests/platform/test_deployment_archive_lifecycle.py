"""Durable verified transfer caches are disposable; scientific and recovery records are not."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import Mock, patch

from test_deployment_archive_cleanup import StorageTests, subject

spec = importlib.util.spec_from_file_location('cache_lifecycle',
    Path(__file__).parents[2] / 'host/deployment_archive_lifecycle.py')
lifecycle = importlib.util.module_from_spec(spec); spec.loader.exec_module(lifecycle)
lifecycle.cleanup = subject; lifecycle.stage = subject.stage; lifecycle.Refused = subject.Refused


class LifecycleTests(StorageTests):
    # Reuse the protected filesystem fixture, not its test cases.
    def setUp(self):
        super().setUp()
        self.policy = dict(schema='hyprn-deployment-cache-policy/v1', identity=self.value['identity'],
            max_cleanup_bytes=2 * lifecycle.GiB, max_seconds=600,
            max_cache_bytes=12 * lifecycle.GiB, min_free_bytes=4 * lifecycle.GiB)
        self.receipt()
        active = patch.object(subject.stage, 'mounted_data'); active.start(); self.addCleanup(active.stop)
        active = patch.object(subject.stage, 'space_available', return_value=20 * lifecycle.GiB)
        active.start(); self.addCleanup(active.stop)
        self.host = Mock()
        def metadata(obj):
            content = (self.old / self.obsolete / obj.rsplit('/', 1)[1]).read_bytes()
            return dict(size=str(len(content)), generation='1234')
        def download(obj, generation=None):
            self.assertEqual(generation, '1234')
            content = (self.old / self.obsolete / obj.rsplit('/', 1)[1]).read_bytes()
            response = io.BytesIO(content); response.status = 200
            response.headers = {'Content-Length': str(len(content))}
            return response
        self.host.object_version.side_effect = metadata
        self.host.download.side_effect = download

    def receipt(self):
        path = self.old / self.obsolete
        files = []
        for name in subject.NAMES:
            if not (path / name).exists():
                continue
            data = (path / name).read_bytes()
            files.append(dict(destination=str(path / name), object='exact-published/' + name,
                sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data), mode=0o644))
        value = dict(schema='hyprn-release-stage/v1', release_sha256=self.obsolete,
            identity=self.value['identity'], bucket=subject.stage.BUCKET, files=files)
        (path / subject.stage.RECEIPT).write_bytes(subject.stage.canonical(value))

    def test_discovery_is_read_only_and_maintenance_preserves_controls_and_rollback(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = lifecycle.run(self.policy, host=self.host)
        self.assertEqual(result['selected_files'], 1)
        self.host.download.assert_not_called()
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        result = lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertEqual(result['removed'], [self.row['path']])
        self.assertEqual(result['durable_copies'][0]['generation'], '1234')
        self.assertFalse(result['cleanup_pending']); self.assertFalse(result['pressure'])
        self.assertTrue(Path(self.row['retained_copy']).exists())
        self.assertTrue((self.old / self.obsolete / 'payload.json').exists())
        self.assertTrue((self.old / self.obsolete / subject.stage.RECEIPT).exists())
        self.assertEqual(lifecycle.run(self.policy, subject.stage.digest(self.policy),
                                     host=self.host)['removed'], [])

    def test_unreceipted_legacy_archives_are_reported_and_preserved(self):
        (self.old / self.obsolete / subject.stage.RECEIPT).unlink()
        result = lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertEqual(result['unmanaged_archive_bytes'], self.row['size_bytes'])
        self.assertEqual(result['removed'], [])
        self.host.download.assert_not_called()
        self.assertTrue(Path(self.row['path']).exists())

    def test_remote_corruption_and_deadline_preserve_every_candidate(self):
        def corrupt(obj, **kw):
            stream = io.BytesIO(b'x' * self.row['size_bytes']); stream.status = 200
            stream.headers = {'Content-Length': str(self.row['size_bytes'])}
            return stream
        self.host.download.side_effect = corrupt
        with self.assertRaisesRegex(subject.Refused, 'durable_archive_digest'):
            lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertTrue(Path(self.row['path']).exists())
        with patch.object(lifecycle.time, 'monotonic', side_effect=[0, 601]):
            with self.assertRaisesRegex(subject.Refused, 'deadline'):
                lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertTrue(Path(self.row['path']).exists())

    def test_changed_receipt_identity_and_unsettled_deployment_refuse(self):
        path = self.old / self.obsolete / subject.stage.RECEIPT
        value = json.loads(path.read_bytes()); value['identity']['instance_id'] = '999999'
        path.write_bytes(subject.stage.canonical(value))
        with self.assertRaisesRegex(subject.Refused, 'receipt_identity'):
            lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.receipt()
        self.journal.read.return_value['stage'] = 'installing'
        with self.assertRaisesRegex(subject.Refused, 'not_settled'):
            lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertTrue(Path(self.row['path']).exists())

    def test_budget_and_pressure_are_observable(self):
        value = copy.deepcopy(self.policy); value['max_cleanup_bytes'] = 1
        with self.assertRaisesRegex(subject.Refused, 'budget'):
            lifecycle.run(value, subject.stage.digest(value), host=self.host)
        (self.old / self.obsolete / subject.stage.RECEIPT).unlink()
        with patch.object(subject.stage, 'space_available', return_value=0):
            result = lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertEqual(result['removed'], [])
        self.assertTrue(result['pressure']); self.assertEqual(result['free_bytes_after'], 0)
        self.assertEqual(result['root_free_bytes_after'], 0)
        self.assertTrue(Path(self.row['path']).exists())

    def test_every_selected_remote_archive_passes_before_any_local_removal(self):
        second = self.archive('modeling.oci.tar', b'another valid archive')
        self.receipt()
        original = self.host.download.side_effect
        def failing(obj, **kwargs):
            response = original(obj, **kwargs)
            if obj.endswith('worker.oci.tar'):
                response.close()
                raise OSError('remote archive unavailable')
            return response
        self.host.download.side_effect = failing
        with self.assertRaises(OSError):
            lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertTrue(Path(self.row['path']).exists())
        self.assertTrue(Path(second['path']).exists())

    def test_busy_deployment_is_reported_as_a_safe_scheduled_skip(self):
        import contextlib
        import sys
        @contextlib.contextmanager
        def busy():
            raise subject.reconcile.Refused('deployment_conflict')
            yield
        self.journal.lock.side_effect = busy
        with patch.object(subject, 'sibling', return_value=lifecycle), \
                patch.object(subject, 'read_document', return_value=self.policy), \
                patch.object(sys, 'argv', ['cleanup', 'maintain', '--policy', 'policy',
                    '--approve-sha256', subject.stage.digest(self.policy)]), \
                patch.object(lifecycle.stage, 'AttachedHost', return_value=self.host), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            subject.main()
        self.assertEqual(json.loads(output.getvalue()),
                         {'status': 'skipped', 'reason': 'deployment_in_progress'})
        self.assertTrue(Path(self.row['path']).exists())

    def test_data_root_archive_and_unknown_files_remain_scoped(self):
        import shutil
        target = self.data / self.obsolete
        shutil.move(str(self.old / self.obsolete), target)
        receipt = json.loads((target / subject.stage.RECEIPT).read_bytes())
        receipt['schema'] = 'hyprn-release-stage/v2'
        receipt['files'][0]['destination'] = str(target / 'worker.oci.tar')
        (target / subject.stage.RECEIPT).write_bytes(subject.stage.canonical(receipt))
        (target / 'notes.json').write_bytes(b'unchanged')
        self.host.object_version.side_effect = None
        self.host.object_version.return_value = dict(size=str(self.row['size_bytes']), generation='1234')
        content = (target / 'worker.oci.tar').read_bytes()
        stream = io.BytesIO(content); stream.status = 200
        stream.headers = {'Content-Length': str(len(content))}
        self.host.download.side_effect = None; self.host.download.return_value = stream
        result = lifecycle.run(self.policy, subject.stage.digest(self.policy), host=self.host)
        self.assertEqual(result['removed'], [str(target / 'worker.oci.tar')])
        self.assertEqual((target / 'notes.json').read_bytes(), b'unchanged')


# Inherited cases exercise the explicit-manifest command separately in its own group.
for name in vars(StorageTests):
    if name.startswith('test_'):
        setattr(LifecycleTests, name, None)
del StorageTests

class SetupTests(LifecycleTests):
    def setUp(self):
        super().setUp()
        setup_spec = importlib.util.spec_from_file_location('cache_setup_subject',
            Path(__file__).parents[2] / 'host/deployment_cache_setup.py')
        self.setup = importlib.util.module_from_spec(setup_spec)
        setup_spec.loader.exec_module(self.setup)
        self.setup.lifecycle = lifecycle; self.setup.cleanup = subject
        self.setup.stage = subject.stage; self.setup.Refused = subject.Refused
        self.setup.ROOT = self.root / 'installed-code'
        self.setup.UNITS = self.root / 'units'; self.setup.UNITS.mkdir()
        self.setup.RECORD = self.root / 'installation.json'
        self.calls = Mock()
        active = patch.object(subject.stage, 'directory', side_effect=lambda path, **kw: (
            (Path(path).mkdir(parents=True, exist_ok=True) if kw.get('create') else None)
            or __import__('os').open(path, __import__('os').O_RDONLY | __import__('os').O_DIRECTORY
                                   | __import__('os').O_NOFOLLOW)))
        active.start(); self.addCleanup(active.stop)

    def test_installs_immutable_code_policy_timer_and_repeats(self):
        plan = self.setup.plan(self.policy)
        result = self.setup.apply(self.policy, plan['plan_sha256'],
                                  host=self.host, systemctl=self.calls)
        self.assertEqual(result['timer'], 'active'); self.assertFalse(result['cleanup_started'])
        self.assertEqual(json.loads((Path(plan['snapshot']) / 'policy.json').read_bytes()), self.policy)
        self.assertTrue((self.setup.UNITS / 'hyprn-deployment-cache.timer').exists())
        self.assertIn('CPUQuota=25%', plan['units']['hyprn-deployment-cache.service'])
        self.assertIn('OnUnitActiveSec=1h', plan['units']['hyprn-deployment-cache.timer'])
        self.setup.apply(self.policy, plan['plan_sha256'], host=self.host, systemctl=self.calls)
        self.assertTrue(Path(self.row['path']).exists())

    def test_policy_replacement_requires_exact_previous_plan_and_known_unit_bytes(self):
        plan = self.setup.plan(self.policy)
        self.setup.apply(self.policy, plan['plan_sha256'], host=self.host, systemctl=self.calls)
        changed = dict(self.policy, max_cache_bytes=13 * lifecycle.GiB)
        new = self.setup.plan(changed)
        with self.assertRaisesRegex(subject.Refused, 'existing_policy'):
            self.setup.apply(changed, new['plan_sha256'], host=self.host, systemctl=self.calls)
        new = self.setup.plan(changed, plan['plan_sha256'])
        unit = self.setup.UNITS / 'hyprn-deployment-cache.service'
        original = unit.read_bytes(); unit.write_bytes(b'unknown service')
        with self.assertRaisesRegex(subject.Refused, 'unit_changed'):
            self.setup.apply(changed, new['plan_sha256'], plan['plan_sha256'],
                             host=self.host, systemctl=self.calls)
        unit.write_bytes(original)
        self.setup.apply(changed, new['plan_sha256'], plan['plan_sha256'],
                         host=self.host, systemctl=self.calls)
        self.assertTrue(Path(plan['snapshot']).is_dir())


for name in vars(LifecycleTests):
    if name.startswith('test_'):
        setattr(SetupTests, name, None)
