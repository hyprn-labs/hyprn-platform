"""Registry authorization is temporary and cannot change image or daemon identity."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import images


class ImageTests(unittest.TestCase):
    def setUp(self):
        scope = tempfile.TemporaryDirectory(prefix='hyprn-images-')
        self.addCleanup(scope.cleanup)
        self.root = Path(scope.name).resolve()
        self.tool = self.root / 'docker'
        self.tool.write_text('reviewed fixture tool')
        self.pin = hashlib.sha256(self.tool.read_bytes()).hexdigest()
        self.config = self.root / 'config'
        self.config.mkdir(mode=0o700)
        self.refs = {role: 'europe-west1-docker.pkg.dev/hyprn-staging/product/' + role
                     + '@sha256:' + c * 64
                     for role, c in (('app', 'a'), ('modeling', 'b'), ('worker', 'c'))}
        self.target = SimpleNamespace(runtime={'registry': 'europe-west1-docker.pkg.dev/hyprn-staging/product',
            'project_id': 'hyprn-staging', 'project_number': '123'}, release={'images': self.refs},
            protect=lambda: None, unchanged=lambda: None)
        self.calls = []
        self.credentials_used = False
        self.wrong = None
        self.fail = False
        self.addCleanup(patch.stopall)
        patch.object(images.reconcile, 'protected', side_effect=Path).start()
        patch.object(images.reconcile._secret_loader, 'require_tmpfs').start()
        patch.object(images.reconcile, 'AttachedServiceAccount', return_value=SimpleNamespace(
            preflight=self.preflight, token='private-test-token')).start()
        patch.object(images.reconcile, 'bounded', side_effect=self.command).start()

    def preflight(self, args):
        self.assertEqual((args.project_id, args.project_number), ('hyprn-staging', '123'))
        self.credentials_used = True

    def command(self, args, *, timeout):
        self.calls.append(args)
        self.assertEqual(args[:2], [str(self.tool), '--config'])
        self.assertEqual(args[3:5], ['--host', 'unix:///var/run/docker.sock'])
        config = Path(args[2]) / 'config.json'
        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
        auth = json.loads(config.read_text())
        self.assertEqual(set(auth['auths']), {'europe-west1-docker.pkg.dev'})
        self.assertNotIn('private-test-token', str(args))
        if self.fail:
            raise images.reconcile.Refused('operation_outcome_uncertain')
        if args[6] == 'pull':
            self.assertEqual(args[7], '--platform=linux/amd64')
            return b''
        self.assertEqual(args[6], 'inspect')
        item = {'Os': 'linux', 'Architecture': 'amd64', 'RepoDigests': [args[-1]]}
        if self.wrong:
            item[self.wrong[0]] = self.wrong[1]
        return json.dumps([item]).encode()

    def run_images(self):
        return images.ensure_images(self.target, docker=str(self.tool), docker_sha256=self.pin,
                                    config_root=str(self.config))

    def test_exact_three_images_use_temporary_auth_without_starting_containers(self):
        result = self.run_images()
        self.assertEqual(result, {'images': self.refs, 'containers_started': False})
        self.assertEqual(len(self.calls), 6)
        self.assertTrue(self.credentials_used)
        self.assertEqual(list(self.config.iterdir()), [])

    def test_wrong_digest_or_architecture_is_refused_and_auth_removed(self):
        for wrong in [('RepoDigests', []), ('Architecture', 'arm64'), ('Os', 'windows')]:
            with self.subTest(wrong=wrong):
                self.wrong = wrong
                with self.assertRaisesRegex(images.reconcile.Refused, 'installed_image_identity'):
                    self.run_images()
                self.assertEqual(list(self.config.iterdir()), [])

    def test_failed_pull_removes_auth_without_retry(self):
        self.fail = True
        with self.assertRaisesRegex(images.reconcile.Refused, 'operation_outcome_uncertain'):
            self.run_images()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(list(self.config.iterdir()), [])

    def test_foreign_registry_or_mutable_tag_never_fetch_credentials(self):
        for ref in ('foreign.example/app@sha256:' + 'a' * 64,
                    'europe-west1-docker.pkg.dev/hyprn-staging/product/app:latest'):
            with self.subTest(ref=ref):
                self.refs['app'] = ref
                with self.assertRaisesRegex(images.reconcile.Refused, 'registry_policy'):
                    self.run_images()
                self.assertFalse(self.credentials_used)
                self.assertEqual(self.calls, [])

    def test_changed_tool_never_fetches_credentials(self):
        self.tool.write_text('changed')
        with self.assertRaisesRegex(images.reconcile.Refused, 'docker_tool_pin'):
            self.run_images()
        self.assertFalse(self.credentials_used)

    def test_non_tmpfs_refusal_happens_before_credentials(self):
        images.reconcile._secret_loader.require_tmpfs.side_effect = images.reconcile.Refused('tmpfs_required')
        with self.assertRaisesRegex(images.reconcile.Refused, 'tmpfs_required'):
            self.run_images()
        self.assertFalse(self.credentials_used)
        self.assertEqual(list(self.config.iterdir()), [])

    def test_metadata_identity_failure_removes_temporary_directory(self):
        with patch.object(images.reconcile, 'AttachedServiceAccount', side_effect=images.reconcile.Refused('identity')):
            with self.assertRaisesRegex(images.reconcile.Refused, 'identity'):
                self.run_images()
        self.assertEqual(list(self.config.iterdir()), [])

    def test_private_config_directory_is_required(self):
        self.config.chmod(0o755)
        with self.assertRaises(images.reconcile._secret_loader.Invalid):
            self.run_images()
        self.assertFalse(self.credentials_used)
