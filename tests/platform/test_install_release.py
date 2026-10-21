"""Actual extraction and byte verification; no product interpreter is executed."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('install_subject', ROOT / 'host/install_release.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class InstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='hyprn-install-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.parent = self.root / 'releases'
        self.parent.mkdir(mode=0o700)
        self.commit = 'a' * 40
        self.target = self.parent / self.commit

    def bundle(self, *, wrong_hash=False, extra=False, prefix=None, unsafe=False):
        entries = {'build.json': json.dumps({'source_commit': self.commit,
            'prefix': str(prefix or self.target), 'target': 'linux/amd64'}).encode(),
            'source/deployment/probe.py': b'raise RuntimeError("must not execute")\n',
            'native/bin/python': b'not an executable interpreter\n'}
        if unsafe:
            entries['../outside'] = b'forbidden'
        inventory = {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
                     for name, raw in entries.items()}
        if wrong_hash:
            inventory['native/bin/python']['sha256'] = '0' * 64
        entries['bundle-inventory.json'] = json.dumps(inventory).encode()
        if extra:
            entries['unlisted'] = b'not permitted'
        path = self.root / 'native.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            for name, raw in entries.items():
                item = tarfile.TarInfo(name)
                item.size = len(raw)
                item.mode = 0o755 if name == 'native/bin/python' else 0o644
                archive.addfile(item, io.BytesIO(raw))
        path.chmod(0o600)
        return path, {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                      'size_bytes': path.stat().st_size}

    def install(self, path, specification):
        return subject.install_native(path, specification, self.target, source_commit=self.commit)

    def test_installs_exact_bytes_and_modes_without_executing_sources(self):
        path, specification = self.bundle()
        result = self.install(path, specification)
        self.assertFalse(result['product_code_executed'])
        self.assertEqual(result['bundle_sha256'], specification['sha256'])
        self.assertEqual(result['files'], 3)
        self.assertEqual((self.target / 'native/bin/python').read_bytes(), b'not an executable interpreter\n')
        self.assertEqual((self.target / 'native/bin/python').stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.target / 'source/deployment/probe.py').stat().st_mode & 0o777, 0o644)
        self.assertEqual(list(self.parent.iterdir()), [self.target])

    def test_wrong_archive_digest_never_creates_release(self):
        path, specification = self.bundle()
        specification['sha256'] = '0' * 64
        with self.assertRaises(subject.contract.Invalid):
            self.install(path, specification)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_bad_inventory_removes_only_its_incomplete_staging_tree(self):
        path, specification = self.bundle(wrong_hash=True)
        retained = self.parent / 'retained'
        retained.mkdir()
        (retained / 'sentinel').write_text('unchanged')
        with self.assertRaises(subject.contract.Invalid):
            self.install(path, specification)
        self.assertEqual(list(self.parent.iterdir()), [retained])
        self.assertEqual((retained / 'sentinel').read_text(), 'unchanged')

    def test_unlisted_file_is_refused(self):
        with self.assertRaises(subject.contract.Invalid):
            self.install(*self.bundle(extra=True))
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_wrong_final_prefix_is_refused(self):
        with self.assertRaises(subject.contract.Invalid):
            self.install(*self.bundle(prefix=self.parent / 'foreign'))
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_traversal_is_rejected_before_extraction(self):
        with self.assertRaises(subject.contract.Invalid):
            self.install(*self.bundle(unsafe=True))
        self.assertFalse((self.parent / 'outside').exists())
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_existing_release_is_never_replaced(self):
        self.target.mkdir()
        sentinel = self.target / 'sentinel'
        sentinel.write_text('retained')
        with self.assertRaises(subject.contract.Invalid):
            self.install(*self.bundle())
        self.assertEqual(sentinel.read_text(), 'retained')

    def test_symlink_destination_or_bundle_is_refused(self):
        path, specification = self.bundle()
        link = self.root / 'link'
        link.symlink_to(path)
        with self.assertRaises(subject.contract.Invalid):
            self.install(link, specification)
        self.target.symlink_to(self.root / 'not-present')
        with self.assertRaises(subject.contract.Invalid):
            self.install(path, specification)

    def test_writable_installation_parent_is_refused(self):
        path, specification = self.bundle()
        self.parent.chmod(0o777)
        with self.assertRaises(subject.contract.Invalid):
            self.install(path, specification)
        self.assertEqual(list(self.parent.iterdir()), [])

    def test_writable_archive_is_refused(self):
        path, specification = self.bundle()
        path.chmod(0o666)
        with self.assertRaises(subject.contract.Invalid):
            self.install(path, specification)
        self.assertEqual(list(self.parent.iterdir()), [])


class VerifyInstalledTests(unittest.TestCase):
    setUp = InstallTests.setUp
    bundle = InstallTests.bundle
    install = InstallTests.install
    def test_verifies_existing_tree_without_replacing_or_executing_it(self):
        path, specification = self.bundle()
        self.install(path, specification)
        before = (self.target / 'build.json').stat().st_mtime_ns
        inventory = subject.verify_native(path, specification, self.target, source_commit=self.commit)
        self.assertEqual(set(inventory), {'build.json', 'source/deployment/probe.py', 'native/bin/python'})
        self.assertEqual((self.target / 'build.json').stat().st_mtime_ns, before)

    def test_modified_missing_extra_and_linked_files_are_refused(self):
        path, specification = self.bundle()
        self.install(path, specification)
        item = self.target / 'source/deployment/probe.py'
        original = item.read_bytes()
        for change in ('modified', 'missing', 'extra', 'symlink', 'mode', 'hardlink'):
            with self.subTest(change=change):
                extra = self.target / 'extra'
                if change == 'modified': item.write_bytes(b'changed')
                elif change == 'missing': item.unlink()
                elif change == 'extra': extra.write_bytes(b'unlisted')
                elif change == 'symlink':
                    item.unlink()
                    item.symlink_to(path)
                elif change == 'mode': item.chmod(0o666)
                elif change == 'hardlink': os.link(item, self.root / 'hardlink')
                with self.assertRaises(subject.contract.Invalid):
                    subject.verify_native(path, specification, self.target, source_commit=self.commit)
                extra.unlink(missing_ok=True)
                (self.root / 'hardlink').unlink(missing_ok=True)
                item.unlink(missing_ok=True)
                item.write_bytes(original)
                item.chmod(0o644)
