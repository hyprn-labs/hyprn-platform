"""Only verified duplicate transfer archives can be removed; recovery inputs remain present."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location('cleanup_subject', ROOT / 'host/deployment_archive_cleanup.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class StorageTests(unittest.TestCase):
    def setUp(self):
        scope = tempfile.TemporaryDirectory(prefix='hyprn-archive-cleanup-')
        self.addCleanup(scope.cleanup)
        self.root = Path(scope.name).resolve()
        self.old, self.data = self.root / 'legacy', self.root / 'data'
        self.old.mkdir(); self.data.mkdir()
        self.current, self.previous, self.obsolete = 'a' * 64, 'b' * 64, 'c' * 64
        for release in (self.current, self.previous, self.obsolete):
            (self.old / release).mkdir()
        self.control = self.root / 'identity.json'
        self.control.write_text(json.dumps({'release_sha256': self.current}))
        self.journal = MagicMock()
        self.journal.read.return_value = dict(stage='installed_closed',
            installed={'release_sha256': self.current},
            backup={'identity': {'release_sha256': self.previous}})
        self.journal.lock.return_value.__enter__ = Mock(return_value=self.journal)
        self.journal.lock.return_value.__exit__ = Mock(return_value=False)
        for target, key, value in ((subject.stage, 'DEPLOYMENT_ROOT', str(self.old)),
                (subject.stage, 'DATA_DEPLOYMENT_ROOT', str(self.data)),
                (subject.stage, 'OWNER', os.getuid()), (subject, 'IDENTITY', str(self.control)),
                (subject, 'JOURNAL', str(self.root))):
            active = patch.object(target, key, value); active.start(); self.addCleanup(active.stop)
        active = patch.object(subject.stage, 'directory',
            side_effect=lambda path, **kwargs: os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        active.start(); self.addCleanup(active.stop)
        active = patch.object(subject.reconcile, 'Journal', return_value=self.journal)
        active.start(); self.addCleanup(active.stop)
        self.row = self.archive('worker.oci.tar', b'example verified archive')
        self.value = dict(schema='hyprn-deployment-archive-cleanup/v1', identity={
            'project_id': 'hyprn-staging', 'project_number': '649400303564',
            'instance_id': '3112612718549037193', 'instance_name': 'hyprn-staging-host',
            'zone': 'europe-west1-b',
            'service_account': 'hyprn-staging-runtime@hyprn-staging.iam.gserviceaccount.com'},
            retained_releases=[self.current, self.previous], archives=[self.row])

    def archive(self, name, content):
        sha = hashlib.sha256(content).hexdigest()
        hashes = []
        for release in (self.obsolete, self.current):
            path = self.old / release / name
            path.write_bytes(content); path.chmod(0o644)
            manifest = path.parent / 'payload.json'
            value = json.loads(manifest.read_text()) if manifest.exists() else dict(
                schema='hyprn-hosted-payload/v1', release_sha256=release, files={})
            value['files'][subject.NAMES[name]] = dict(path=name, sha256=sha, size_bytes=len(content))
            manifest.write_bytes(subject.stage.canonical(value)); manifest.chmod(0o644)
            hashes.append(hashlib.sha256(manifest.read_bytes()).hexdigest())
        return dict(path=str(self.old / self.obsolete / name),
            retained_copy=str(self.old / self.current / name), sha256=sha,
            size_bytes=len(content), mode=0o644,
            inventory_sha256=hashes[0], retained_inventory_sha256=hashes[1])

    def test_plan_changes_nothing_apply_removes_only_duplicate_and_repeats_safely(self):
        host = Mock()
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subject.run(self.value, host=host)
        self.assertEqual(result['reclaimable_bytes'], self.row['size_bytes'])
        self.assertEqual(result['removed'], [])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        approved = result['plan_sha256']
        result = subject.run(self.value, approved, host=host)
        self.assertEqual(result['removed'], [self.row['path']])
        self.assertFalse(Path(self.row['path']).exists())
        self.assertTrue(Path(self.row['retained_copy']).exists())
        self.assertTrue((self.old / self.obsolete / 'payload.json').exists())
        self.assertEqual(subject.run(self.value, approved, host=host)['removed'], [])
        self.assertFalse(result['product_records_changed'])

    def test_active_or_backup_sources_and_unlisted_names_are_never_candidates(self):
        for change in ({'path': self.row['retained_copy']},
                {'path': str(self.old / self.obsolete / 'database.sqlite')},
                {'retained_copy': self.row['path']},
                {'path': str(self.old / self.obsolete / 'nested' / 'worker.oci.tar')}):
            value = copy.deepcopy(self.value); value['archives'][0].update(change)
            with self.subTest(change=change), self.assertRaises(subject.Refused):
                subject.validate(value)
        self.journal.read.return_value['backup']['identity']['release_sha256'] = 'd' * 64
        with self.assertRaisesRegex(subject.Refused, 'not_retained'):
            subject.run(self.value, subject.stage.digest(self.value), host=Mock())
        self.assertTrue(Path(self.row['path']).exists())

    def test_missing_or_changed_retained_copy_never_removes_source(self):
        kept = Path(self.row['retained_copy']); kept.write_bytes(b'changed')
        with self.assertRaisesRegex(subject.Refused, 'differs'):
            subject.run(self.value, subject.stage.digest(self.value), host=Mock())
        kept.unlink()
        with self.assertRaisesRegex(subject.Refused, 'retained_copy_missing'):
            subject.run(self.value, subject.stage.digest(self.value), host=Mock())
        self.assertTrue(Path(self.row['path']).exists())

    def test_changed_inventory_or_symlink_is_refused(self):
        source = Path(self.row['path'])
        source.unlink(); source.symlink_to(self.row['retained_copy'])
        with self.assertRaises(OSError):
            subject.run(self.value, subject.stage.digest(self.value), host=Mock())
        source.unlink(); source.write_bytes(Path(self.row['retained_copy']).read_bytes())
        manifest = source.parent / 'payload.json'
        manifest.write_text(manifest.read_text() + ' ')
        with self.assertRaisesRegex(subject.Refused, 'inventory_changed'):
            subject.run(self.value, subject.stage.digest(self.value), host=Mock())
        self.assertTrue(source.exists())

    def test_approval_and_host_identity_precede_mutation(self):
        host = Mock()
        with self.assertRaisesRegex(subject.Refused, 'approval_mismatch'):
            subject.run(self.value, 'd' * 64, host=host)
        host.verify.assert_not_called()
        host.verify.side_effect = subject.Refused('identity_mismatch')
        with self.assertRaisesRegex(subject.Refused, 'identity_mismatch'):
            subject.run(self.value, subject.stage.digest(self.value), host=host)
        self.assertTrue(Path(self.row['path']).exists())

    def test_replacement_after_verification_is_detected_before_unlink(self):
        for key in ('path', 'retained_copy'):
            with self.subTest(changed=key):
                original = subject.inspect
                path = Path(self.row[key])
                original_bytes = path.read_bytes()
                def changed(row, verified):
                    result = original(row, verified)
                    path.write_bytes(b'x' * len(original_bytes))
                    return result
                with patch.object(subject, 'inspect', side_effect=changed):
                    with self.assertRaisesRegex(subject.Refused, 'verified_archive_changed'):
                        subject.run(self.value, subject.stage.digest(self.value), host=Mock())
                self.assertTrue(Path(self.row['path']).exists())
                path.write_bytes(original_bytes)

    def test_all_candidates_are_verified_before_first_removal(self):
        second = self.archive('modeling.oci.tar', b'different verified archive')
        for row in (self.row, second):
            row['inventory_sha256'] = second['inventory_sha256']
            row['retained_inventory_sha256'] = second['retained_inventory_sha256']
        self.value['archives'].append(second)
        Path(second['path']).write_bytes(b'bad')
        with self.assertRaisesRegex(subject.Refused, 'differs'):
            subject.run(self.value, subject.stage.digest(self.value), host=Mock())
        self.assertTrue(Path(self.row['path']).exists())


if __name__ == '__main__':
    unittest.main()
