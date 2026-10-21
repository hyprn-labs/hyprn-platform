"""Bootstrap policy, exact bytes and lock tests; no live provider or product calls."""
from contextlib import contextmanager
import copy
import hashlib
import importlib.util
import json
import io
import tarfile
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('bootstrap_subject', ROOT / 'host/bootstrap.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        scope = tempfile.TemporaryDirectory(prefix='hyprn-bootstrap-')
        self.addCleanup(scope.cleanup)
        self.root = Path(scope.name).resolve()
        self.policy = {'schema': 'hyprn-bootstrap/v1', 'binding': str(self.root / 'binding.json'),
            'desired_sha256': 'a' * 64, 'initialize': True, 'active': None,
            'journal_root': str(self.root / 'journal'),
            'disk': {'disk_name': 'hyprn-staging-data', 'device_name': 'hyprn-data', 'retired_hosts': []},
            'images': {'docker': str(self.root / 'docker'), 'docker_sha256': 'b' * 64,
                       'config_root': str(self.root / 'registry')},
            'secret_versions': {'modeling-auth': 3},
            'controls': {key: {'path': str(self.root / (key + '.json')), 'sha256': 'c' * 64}
                         for key in subject.CONTROL_NAMES},
            'backup': None, 'minimum_free_bytes': 1024,
            'preflight': {'policy': str(self.root / 'preflight.json'), 'sha256': 'd' * 64}}

    def save(self, name, value, mode=0o600):
        path = self.root / name
        path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
        path.chmod(mode)
        return path

    def target(self):
        desired = {'sequence': 1, 'purpose': 'protocol-fixture'}
        self.policy['desired_sha256'] = subject.contract.digest(desired)
        return SimpleNamespace(path=Path(self.policy['binding']), desired=desired,
            identity={'installation_id': 'test-install', 'release_sha256': 'e' * 64, 'config_sha256': 'f' * 64},
            binding_sha256='1' * 64,
            binding={'control_root': str(self.root / 'control'), 'payload_inventory': str(self.root / 'payload.json')},
            release={'stores': {}},
            runtime={'installation_id': 'test-install', 'project_id': 'hyprn-staging-fixture',
                     'project_number': '123456789012', 'disk_uuid': 'test-disk', 'store_ids': {},
                     'secrets': {'modeling-auth': {'name': 'hyprn-staging-modeling-auth', 'version': 3}},
                     'mounts': {name: str(self.root / name)
                                for name in ('application', 'modeling', 'execution', 'secrets')},
                     'database': {'ca_sha256': 'c' * 64}})

    def test_loads_exact_private_policy_without_effects(self):
        path = self.save('bootstrap.json', self.policy)
        self.assertEqual(subject.load_policy(path), self.policy)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_policy_forbids_executable_hooks_and_unknown_fields(self):
        self.policy['command'] = 'echo should-never-run'
        path = self.save('bootstrap.json', self.policy)
        with self.assertRaisesRegex(subject.Refused, '^bootstrap_policy$'):
            subject.load_policy(path)

    def test_missing_explicit_initialization_is_not_inferred(self):
        del self.policy['initialize']
        with self.assertRaisesRegex(subject.Refused, '^bootstrap_policy$'):
            subject.validate_policy(self.policy)

    def test_initialization_never_accepts_an_active_binding(self):
        self.policy['active'] = {'binding': str(self.root / 'old.json'), 'desired_sha256': 'a' * 64}
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_initialization_policy'):
            subject.validate_policy(self.policy)

    def test_updates_require_complete_explicit_backup_approval(self):
        self.policy['initialize'] = False
        self.policy['active'] = {'binding': str(self.root / 'old.json'), 'desired_sha256': 'a' * 64}
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_update_policy'):
            subject.validate_policy(self.policy)
        self.policy['backup'] = {'policy': str(self.root / 'backup.json'),
            'root': str(self.root / 'backup-sets'), 'approve_resource': 'projects/hyprn-staging-fixture/instances/test-db'}
        self.assertEqual(subject.validate_policy(self.policy), self.policy)

    def test_secret_versions_reject_booleans_aliases_and_zero(self):
        for value in (True, 0, 'latest', '3', 2**53):
            with self.subTest(value=value):
                self.policy['secret_versions']['modeling-auth'] = value
                with self.assertRaisesRegex(subject.Refused, 'bootstrap_secret_policy'):
                    subject.validate_policy(self.policy)

    def test_policy_permissions_links_and_duplicate_keys_are_rejected(self):
        path = self.save('bootstrap.json', self.policy, 0o644)
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_private_authority'):
            subject.load_policy(path)
        path.chmod(0o600)
        link = self.root / 'link.json'
        link.symlink_to(path)
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_path_authority'):
            subject.load_policy(link)
        path.write_bytes(b'{"schema":"first","schema":"second"}')
        with self.assertRaises(subject.contract.Invalid):
            subject.load_policy(path)

    def test_scope_paths_reject_relative_and_parent_traversal(self):
        for path in ('relative/path', '/tmp/../other', '/tmp//double'):
            with self.subTest(path=path):
                self.policy['journal_root'] = path
                with self.assertRaisesRegex(subject.Refused, 'bootstrap_policy'):
                    subject.validate_policy(self.policy)

    def test_desired_digest_and_secret_versions_must_match_target(self):
        target = self.target()
        subject.bind_policy(self.policy, target)
        self.policy['desired_sha256'] = '0' * 64
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_desired_pin'):
            subject.bind_policy(self.policy, target)
        self.policy['desired_sha256'] = subject.contract.digest(target.desired)
        self.policy['secret_versions']['modeling-auth'] = 4
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_secret_pin'):
            subject.bind_policy(self.policy, target)

    def test_journal_cannot_populate_or_share_an_owned_store(self):
        target = self.target()
        for owner in ('application', 'modeling', 'execution'):
            for suffix in ('', '/deployment-journal'):
                with self.subTest(owner=owner, suffix=suffix):
                    self.policy['journal_root'] = target.runtime['mounts'][owner] + suffix
                    with self.assertRaisesRegex(subject.Refused, 'bootstrap_journal_inside_owner_store'):
                        subject.bind_policy(self.policy, target)
        self.policy['journal_root'] = str(self.root / 'deployment-journal')
        subject.bind_policy(self.policy, target)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_registry_credentials_cannot_share_runtime_secret_scope(self):
        target = self.target()
        for root in (target.runtime['mounts']['secrets'], target.runtime['mounts']['secrets'] + '/registry'):
            with self.subTest(root=root):
                self.policy['images']['config_root'] = root
                with self.assertRaisesRegex(subject.Refused, 'bootstrap_registry_secret_scope'):
                    subject.bind_policy(self.policy, target)

    def test_runtime_secret_sources_cannot_be_published_as_shared_controls(self):
        target = self.target()
        self.policy['controls']['assistant_plan']['path'] = target.runtime['mounts']['secrets'] + '/app/assistant-provider'
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_control_secret_scope'):
            subject.bind_policy(self.policy, target)

    def test_update_refuses_secret_rotation_before_any_mutation(self):
        target = self.target()
        active = copy.deepcopy(target)
        active.path = self.root / 'old-binding.json'
        active.desired = {'sequence': 0}
        self.policy['initialize'] = False
        self.policy['active'] = {'binding': str(active.path), 'desired_sha256': subject.contract.digest(active.desired)}
        target.runtime['secrets']['modeling-auth']['version'] = 4
        self.policy['secret_versions']['modeling-auth'] = 4
        with self.assertRaisesRegex(subject.Refused, 'secret_rotation_requires_reviewed_hook'):
            subject.bind_policy(self.policy, target, active)

    def test_update_refuses_database_rebinding_before_any_mutation(self):
        target = self.target()
        active = copy.deepcopy(target)
        active.path = self.root / 'old-binding.json'
        active.desired = {'sequence': 0}
        self.policy['initialize'] = False
        self.policy['active'] = {'binding': str(active.path), 'desired_sha256': subject.contract.digest(active.desired)}
        target.runtime['database']['host'] = '10.0.0.2'
        with self.assertRaisesRegex(subject.Refused, 'database_binding_change_requires_recovery'):
            subject.bind_policy(self.policy, target, active)

    def test_controls_are_checked_by_bytes_before_copy(self):
        for key in subject.CONTROL_NAMES:
            raw = b'certificate fixture' if key == 'database_ca' else b'{"version":1}'
            path = self.save(key + '.json', raw)
            self.policy['controls'][key] = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}
        checked = subject.control_inputs(self.policy)
        self.assertEqual(checked['database_ca'], b'certificate fixture')
        Path(self.policy['controls']['assistant_plan']['path']).write_bytes(b'{"version":2}')
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_control_bytes'):
            subject.control_inputs(self.policy)

    def test_controls_from_another_release_are_refused_before_publication(self):
        target = SimpleNamespace(identity={'installation_id': 'test',
            'release_sha256': 'a' * 64, 'config_sha256': 'b' * 64},
            binding={'control_root': '/unused'})
        values = {'assistant_continuity': subject.contract.canonical({
            **target.identity, 'release_sha256': 'c' * 64}),
            'assistant_plan': b'{}', 'database_ca': b'certificate'}
        with patch.object(subject, 'control_inputs', return_value=values), \
                patch.object(subject, 'write_bytes') as write, \
                patch.object(subject, 'public_control_directory') as directory:
            with self.assertRaisesRegex(subject.Refused, 'bootstrap_continuity_identity'):
                subject.publish_controls(target, self.policy)
            write.assert_not_called()
            directory.assert_not_called()
            values['assistant_continuity'] = subject.contract.canonical(target.identity)
            subject.publish_controls(target, self.policy)
            self.assertEqual(write.call_count, 3)

    def test_atomic_control_copy_preserves_exact_bytes_and_readability(self):
        path = self.root / 'control.json'
        subject.write_bytes(path, b'{"value":"retained"}\n')
        self.assertEqual(path.read_bytes(), b'{"value":"retained"}\n')
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_control_copy_refuses_link_without_changing_destination(self):
        original = self.save('original.json', b'keep')
        link = self.root / 'control.json'
        link.symlink_to(original)
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_path_authority'):
            subject.write_bytes(link, b'changed')
        self.assertEqual(original.read_bytes(), b'keep')

    def test_public_certificate_directory_is_readable_under_private_umask(self):
        path = self.root / 'trust'
        previous = os.umask(0o077)
        try:
            subject.public_control_directory(path)
        finally:
            os.umask(previous)
        self.assertEqual(path.stat().st_mode & 0o777, 0o755)
        subject.write_bytes(path / 'ca.pem', b'public certificate')
        subject.public_control_directory(path)
        self.assertEqual((path / 'ca.pem').read_bytes(), b'public certificate')

    def test_public_certificate_directory_rejects_links_and_unsafe_modes(self):
        actual = self.root / 'actual'
        actual.mkdir(mode=0o755)
        link = self.root / 'trust'
        link.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(subject.Refused):
            subject.public_control_directory(link)
        actual.chmod(0o777)
        with self.assertRaises(subject.Refused):
            subject.public_control_directory(actual)
        self.assertEqual(actual.stat().st_mode & 0o777, 0o777)

    def artifact_target(self):
        parent = self.root / 'application'
        parent.mkdir(mode=0o700)
        # macOS uses a shared primary group; Linux production requires uid == gid.
        # Keep real descriptor/path/mode observations, substitute only ownership.
        from unittest.mock import patch
        real_stat = os.fstat
        def owner_stat(fd):
            info = real_stat(fd)
            return SimpleNamespace(st_uid=info.st_uid, st_gid=info.st_uid,
                                   st_mode=info.st_mode)
        ownership = patch.object(subject.os, 'fstat', side_effect=owner_stat)
        chown = patch.object(subject.os, 'fchown')
        ownership.start()
        self.addCleanup(ownership.stop)
        self.assigned_owner = chown.start()
        self.addCleanup(chown.stop)
        return SimpleNamespace(runtime={'mounts': {'application': str(parent)},
                                       'service_users': {'app': os.getuid()}}), parent

    def test_artifact_directory_is_private_and_existing_content_is_preserved(self):
        target, parent = self.artifact_target()
        previous = os.umask(0o077)
        try:
            subject.application_artifacts(target)
        finally:
            os.umask(previous)
        from unittest.mock import ANY
        self.assigned_owner.assert_called_once_with(ANY, os.getuid(), os.getuid())
        folder = parent / 'artifacts'
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        item = folder / 'record'
        item.write_bytes(b'preserve')
        subject.application_artifacts(target)
        self.assertEqual(item.read_bytes(), b'preserve')

    def test_artifact_preparation_refuses_links_foreign_owner_and_open_directory(self):
        target, parent = self.artifact_target()
        folder = parent / 'artifacts'
        external = self.root / 'external'
        external.mkdir(mode=0o700)
        folder.symlink_to(external, target_is_directory=True)
        with self.assertRaises(OSError):
            subject.application_artifacts(target)
        folder.unlink()
        folder.mkdir(mode=0o755)
        folder.chmod(0o755)
        with self.assertRaises(subject.Refused):
            subject.application_artifacts(target)
        self.assertEqual(folder.stat().st_mode & 0o777, 0o755)
        target.runtime['service_users']['app'] += 1
        with self.assertRaises(subject.Refused):
            subject.application_artifacts(target)

    def test_isolated_preflight_loads_reviewed_service_network_module(self):
        code = (
            'import importlib.util,sys,pathlib; '
            'path=pathlib.Path(sys.argv[1]); '
            'spec=importlib.util.spec_from_file_location("subject",path); '
            'module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); '
            'preflight=module.load_preflight(); '
            'import service_network_install; '
            'assert pathlib.Path(service_network_install.__file__)==path.parent/"service_network_install.py"; '
            'assert pathlib.Path(preflight.__file__)==path.parent/"preflight.py"'
        )
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code,
                                 str(ROOT / 'host/bootstrap.py')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_archive_requires_exact_release_pin_and_relative_inventory(self):
        target = self.target()
        target.release = {'native_bundle': {'sha256': 'b' * 64, 'size_bytes': 7}}
        archive = self.save('bundle.tar.gz', b'fixture')
        inventory = {'schema': 'hyprn-hosted-payload/v1', 'release_sha256': target.identity['release_sha256'],
                     'files': {'native_bundle': {'path': archive.name, 'sha256': 'b' * 64, 'size_bytes': 7}}}
        self.save('payload.json', inventory)
        self.assertEqual(subject.native_archive(target), archive)
        for value in ('../bundle.tar.gz', str(archive), 'folder/../bundle.tar.gz'):
            with self.subTest(value=value):
                inventory['files']['native_bundle']['path'] = value
                self.save('payload.json', inventory)
                with self.assertRaisesRegex(subject.Refused, 'bootstrap_native_inventory'):
                    subject.native_archive(target)

    def packaged_target(self):
        target = self.target()
        parent = self.root / 'releases'
        parent.mkdir(mode=0o700)
        commit = 'a' * 40
        destination = parent / commit
        target.preview = {'execution': {'configuration': {
            'source': str(destination / 'source'), 'python': str(destination / 'native/bin/python')}}}
        entries = {'build.json': json.dumps({'source_commit': commit, 'prefix': str(destination),
                                           'target': 'linux/amd64'}).encode(),
            'source/deployment/cloud_lifecycle.py': b'raise RuntimeError("must never execute during preparation")',
            'source/deployment/cloud_release.py': b'raise RuntimeError("must never execute during preparation")',
            'native/bin/python': b'fixture only, not an executable interpreter'}
        inventory = {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
                     for name, raw in entries.items()}
        entries['bundle-inventory.json'] = json.dumps(inventory).encode()
        archive = self.root / 'bundle.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            for name, raw in entries.items():
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                member.mode = 0o755 if name == 'native/bin/python' else 0o644
                stream.addfile(member, io.BytesIO(raw))
        specification = {'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                         'size_bytes': archive.stat().st_size}
        target.release = {'source_commit': commit, 'native_bundle': specification}
        self.save('payload.json', {'schema': 'hyprn-hosted-payload/v1',
            'release_sha256': target.identity['release_sha256'],
            'files': {'native_bundle': {'path': archive.name, **specification}}})
        return target, destination, inventory

    def test_prepares_authenticated_native_bytes_without_executing_product(self):
        target, destination, inventory = self.packaged_target()
        product = subject.prepared_product(target, install=True)
        self.assertEqual(product.python, str(destination / 'native/bin/python'))
        self.assertEqual(product.pins[destination / 'source/deployment/cloud_lifecycle.py'],
                         inventory['source/deployment/cloud_lifecycle.py']['sha256'])
        self.assertEqual((destination / 'native/bin/python').read_bytes(),
                         b'fixture only, not an executable interpreter')
        # Reuse reauthenticates the installed bytes against the original archive.
        reused = subject.prepared_product(target, install=False)
        self.assertEqual(reused.pins, product.pins)

    def test_tampered_installed_release_is_refused_before_product_execution(self):
        target, destination, _inventory = self.packaged_target()
        subject.prepared_product(target, install=True)
        (destination / 'source/deployment/cloud_lifecycle.py').write_bytes(b'changed')
        with self.assertRaises(subject.installer.contract.Invalid):
            subject.prepared_product(target, install=False)

    def test_missing_active_release_is_never_installed_implicitly(self):
        target, destination, _inventory = self.packaged_target()
        with self.assertRaisesRegex(subject.Refused, 'active_release_missing'):
            subject.prepared_product(target, install=False)
        self.assertFalse(destination.exists())

    def test_held_journal_keeps_the_original_exclusive_lock(self):
        journal = subject.reconcile.Journal(self.root)
        with journal.lock():
            original = journal.fd
            with subject.HeldJournal(journal).lock() as held:
                self.assertEqual(held.fd, original)
                with self.assertRaisesRegex(subject.Refused, 'deployment_conflict'):
                    with subject.reconcile.Journal(self.root).lock():
                        self.fail('second writer acquired deployment lock')
        with self.assertRaisesRegex(subject.Refused, 'bootstrap_deployment_hold_lost'):
            with subject.HeldJournal(journal).lock():
                self.fail('released descriptor accepted')

    def test_uncertain_prior_attempt_refuses_before_any_preparation(self):
        target = self.target()
        journal = subject.reconcile.Journal(self.root)
        with journal.lock():
            journal.accept(1, subject.contract.digest(target.desired))
            with self.assertRaisesRegex(subject.Refused, 'operator_recovery_required'):
                subject.check_attempt(journal, target, None)

    def test_completed_sequence_requires_exact_installed_identity(self):
        target = self.target()
        journal = subject.reconcile.Journal(self.root)
        with journal.lock():
            record = journal.accept(1, subject.contract.digest(target.desired))
            record.update(stage='installed_closed', installed={**target.identity, 'binding_sha256': target.binding_sha256})
            journal.write(record)
            self.assertTrue(subject.check_attempt(journal, target, None))
            target.binding_sha256 = '2' * 64
            with self.assertRaisesRegex(subject.Refused, 'active_release_mismatch'):
                subject.check_attempt(journal, target, None)

    def test_cli_has_sanitized_refusal_and_no_effect_without_valid_arguments(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'host/bootstrap.py'),
                                 '--unexpected', 'DO-NOT-PRINT-PAYLOAD'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('DO-NOT-PRINT-PAYLOAD', result.stderr)
        self.assertEqual(json.loads(result.stderr), {'status': 'refused', 'admission': 'unverified',
                                                    'reason_code': 'bootstrap_arguments'})

    def test_import_preserves_standard_library_secrets(self):
        code = ('import secrets,importlib.util,sys; original=secrets; '
                'spec=importlib.util.spec_from_file_location("subject",sys.argv[1]); '
                'module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); '
                'assert sys.modules["secrets"] is original; assert len(secrets.token_hex(8))==16')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(ROOT / 'host/bootstrap.py')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
