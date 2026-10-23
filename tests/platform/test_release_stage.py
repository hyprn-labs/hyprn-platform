"""Reviewed object bytes stage create-only; host identity precedes every download."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('release_stage', Path(__file__).parents[2] / 'host/release_stage.py')
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


def manifest():
    return {'schema': 'hyprn-release-stage/v1', 'release_sha256': 'a' * 64,
            'bucket': stage.BUCKET, 'identity': {
                'project_id': 'hyprn-staging', 'project_number': '649400303564',
                'instance_id': '3112612718549037193', 'instance_name': 'hyprn-staging-host',
                'zone': 'europe-west1-b',
                'service_account': 'hyprn-staging-runtime@hyprn-staging.iam.gserviceaccount.com'},
            'files': [{'destination': stage.PLATFORM_ROOT + '/host/example.py',
                       'object': 'release/example.py', 'sha256': hashlib.sha256(b'abc').hexdigest(),
                       'size_bytes': 3, 'mode': 0o644}]}


class StageTests(unittest.TestCase):
    def test_manifest_refuses_escapes_duplicates_unbounded_and_privileged_modes(self):
        mutations = [lambda v: v.update(bucket='other'),
                     lambda v: v['files'][0].update(destination='/etc/passwd'),
                     lambda v: v['files'][0].update(destination=stage.PLATFORM_ROOT + '/../outside'),
                     lambda v: v['files'][0].update(object='../secret'),
                     lambda v: v['files'][0].update(mode=0o4755),
                     lambda v: v['files'][0].update(size_bytes=True),
                     lambda v: v['files'][0].update(size_bytes=stage.MAX_BYTES + 1),
                     lambda v: v['files'].append(copy.deepcopy(v['files'][0])),
                     lambda v: v['identity'].update(project_id='production')]
        stage.validate(manifest())
        for mutate in mutations:
            value = manifest(); mutate(value)
            with self.subTest(value=value), self.assertRaises(stage.Refused):
                stage.validate(value)

    def test_total_budget_and_exact_release_destination_are_enforced(self):
        value = manifest(); row = copy.deepcopy(value['files'][0])
        value['files'][0]['size_bytes'] = stage.MAX_BYTES
        row.update(destination=stage.DEPLOYMENT_ROOT + '/' + 'a' * 64 + '/control.json',
                   object='release/control.json')
        value['files'].append(row)
        with self.assertRaisesRegex(stage.Refused, 'download_budget'):
            stage.validate(value)
        value['files'][0]['size_bytes'] = 3
        stage.validate(value)
        row['destination'] = row['destination'].replace('a' * 64, 'b' * 64)
        with self.assertRaisesRegex(stage.Refused, 'file_location'):
            stage.validate(value)

    def test_data_disk_manifest_keeps_legacy_destinations_frozen(self):
        value = manifest()
        value['files'][0]['destination'] = stage.DATA_DEPLOYMENT_ROOT + '/' + 'a' * 64 + '/payload.json'
        with self.assertRaisesRegex(stage.Refused, 'file_location'):
            stage.validate(value)
        value['schema'] = 'hyprn-release-stage/v2'
        stage.validate(value)
        value['files'][0]['destination'] = stage.DEPLOYMENT_ROOT + '/' + 'a' * 64 + '/payload.json'
        with self.assertRaisesRegex(stage.Refused, 'file_location'):
            stage.validate(value)

    def test_unmounted_data_disk_refuses_before_downloading_or_writing(self):
        value = manifest(); value['schema'] = 'hyprn-release-stage/v2'
        host = Mock()
        with patch.object(stage, 'mounted_data', side_effect=stage.Refused('missing_mount')), \
                patch.object(stage, 'stage') as write:
            with self.assertRaisesRegex(stage.Refused, 'missing_mount'):
                stage.apply(value, stage.digest(value), host)
            write.assert_not_called()
        with patch.object(stage.os.path, 'ismount', return_value=False):
            with self.assertRaisesRegex(stage.Refused, 'deployment_data_mount_required'):
                stage.mounted_data()

    def test_identity_mismatch_never_requests_token(self):
        host = stage.AttachedHost()
        host.metadata = Mock(return_value='wrong-project')
        with self.assertRaisesRegex(stage.Refused, 'attached_host_mismatch'):
            host.verify(manifest()['identity'])
        host.metadata.assert_called_once_with('project/project-id')
        self.assertIsNone(host.token)

    def verified_host(self, lifetime=740):
        host = stage.AttachedHost()
        identity = manifest()['identity']
        host.metadata = Mock(side_effect=[*identity.values(), json.dumps({
            'token_type': 'Bearer', 'expires_in': lifetime, 'access_token': 'test-token'})])
        host.verify(identity)
        return host

    def test_valid_short_lived_token_is_refreshed_before_later_download(self):
        with patch.object(stage.time, 'monotonic', return_value=100) as clock:
            host = self.verified_host()
            host.opener = Mock()
            host.download('first')
            self.assertEqual(host.opener.open.call_args.args[0].headers['Authorization'],
                             'Bearer test-token')
            clock.return_value = 800
            host.metadata = Mock(return_value=json.dumps({
                'token_type': 'Bearer', 'expires_in': 3600, 'access_token': 'replacement'}))
            host.download('second')
            host.metadata.assert_called_once_with('instance/service-accounts/default/token')
            self.assertEqual(host.opener.open.call_args.args[0].headers['Authorization'],
                             'Bearer replacement')

    def test_invalid_refresh_or_changed_identity_cannot_reuse_previous_token(self):
        for invalid in (True, -1, 0, 59, '3600'):
            with self.subTest(lifetime=invalid), \
                    self.assertRaisesRegex(stage.Refused, 'attached_token_invalid'):
                self.verified_host(invalid)
        with patch.object(stage.time, 'monotonic', return_value=100) as clock:
            host = self.verified_host()
            host.opener = Mock()
            clock.return_value = 800
            host.metadata = Mock(return_value=json.dumps({
                'token_type': 'Bearer', 'expires_in': 0, 'access_token': 'expired'}))
            with self.assertRaisesRegex(stage.Refused, 'attached_token_invalid'):
                host.download('object')
            host.opener.open.assert_not_called()
            host.metadata = Mock(return_value='wrong-project')
            with self.assertRaisesRegex(stage.Refused, 'attached_host_mismatch'):
                host.verify(manifest()['identity'])
            with self.assertRaisesRegex(stage.Refused, 'unverified'):
                host.download('object')

    def test_redirects_cannot_send_attached_token_to_another_origin(self):
        with self.assertRaisesRegex(stage.Refused, 'redirect_refused'):
            stage.NoRedirect().redirect_request(None, None, None, None, None, None)
        with self.assertRaisesRegex(stage.Refused, 'unverified'):
            stage.AttachedHost().download('object')

    def test_approval_and_verified_host_precede_file_changes(self):
        value = manifest(); host = Mock()
        with patch.object(stage.os, 'geteuid', return_value=stage.OWNER), \
                patch.object(stage, 'stage') as write:
            with self.assertRaises(stage.Refused):
                stage.apply(value, 'b' * 64, host)
            host.verify.assert_not_called(); write.assert_not_called()
            host.verify.side_effect = stage.Refused('attached_host_mismatch')
            with self.assertRaises(stage.Refused):
                stage.apply(value, stage.digest(value), host)
            write.assert_not_called()

    def setUp(self):
        scope = tempfile.TemporaryDirectory(prefix='hyprn-stage-')
        self.addCleanup(scope.cleanup)
        self.root = Path(scope.name).resolve()
        self.row = manifest()['files'][0]
        self.row['destination'] = str(self.root / 'example.py')
        self.owner = patch.object(stage, 'OWNER', os.getuid()); self.owner.start()
        self.addCleanup(self.owner.stop)
        self.directories = patch.object(stage, 'directory',
            side_effect=lambda *args, **kwargs: os.open(self.root, os.O_RDONLY | os.O_DIRECTORY))
        self.directories.start(); self.addCleanup(self.directories.stop)

    def response(self, content=b'abc'):
        reply = io.BytesIO(content)
        reply.status = 200; reply.headers = {'Content-Length': '3'}
        return Mock(download=Mock(return_value=reply))

    def test_exact_bytes_stage_once_then_skip_network(self):
        host = self.response()
        self.assertEqual(stage.stage(self.row, host, time.monotonic() + 5), 'staged')
        target = self.root / 'example.py'
        self.assertEqual(target.read_bytes(), b'abc')
        self.assertEqual(target.stat().st_mode & 0o777, 0o644)
        self.assertEqual(stage.stage(self.row, host, time.monotonic() + 5), 'already_present')
        host.download.assert_called_once()

    def test_changed_bytes_and_symlink_destinations_never_get_overwritten(self):
        target = self.root / 'example.py'; target.write_bytes(b'bad'); target.chmod(0o644)
        host = self.response()
        with self.assertRaisesRegex(stage.Refused, 'existing_file_differs'):
            stage.stage(self.row, host, time.monotonic() + 5)
        self.assertEqual(target.read_bytes(), b'bad'); host.download.assert_not_called()
        target.unlink(); target.symlink_to(self.root / 'unrelated')
        with self.assertRaises(OSError):
            stage.stage(self.row, host, time.monotonic() + 5)
        self.assertFalse((self.root / 'unrelated').exists())

    def test_failed_hash_keeps_partial_and_refuses_automatic_retry(self):
        with self.assertRaisesRegex(stage.Refused, 'download_digest'):
            stage.stage(self.row, self.response(b'bad'), time.monotonic() + 5)
        self.assertFalse((self.root / 'example.py').exists())
        host = self.response()
        with self.assertRaisesRegex(stage.Refused, 'interrupted_download'):
            stage.stage(self.row, host, time.monotonic() + 5)
        host.download.assert_not_called()
        self.assertEqual(next(self.root.glob('.stage-*.partial')).read_bytes(), b'bad')

    def test_special_file_is_refused_without_blocking(self):
        os.mkfifo(self.root / 'example.py')
        host = self.response()
        with self.assertRaisesRegex(stage.Refused, 'existing_file_differs'):
            stage.stage(self.row, host, time.monotonic() + 5)
        host.download.assert_not_called()

    def test_reconcile_leaves_interrupted_download_unchanged(self):
        with self.assertRaises(stage.Refused):
            stage.stage(self.row, self.response(b'bad'), time.monotonic() + 5)
        partial = next(self.root.glob('.stage-*.partial'))
        before = (partial.read_bytes(), partial.stat().st_mtime_ns)
        value = manifest(); value['files'] = [self.row]
        with patch.object(stage, 'PLATFORM_ROOT', str(self.root)):
            result = stage.reconcile(value)
        self.assertFalse(result['changed'])
        self.assertEqual(result['files'][0]['state'], 'interrupted_download_requires_review')
        self.assertEqual((partial.read_bytes(), partial.stat().st_mtime_ns), before)

    def test_download_length_and_deadline_refuse_final_installation(self):
        for content, deadline in ((b'abcd', time.monotonic() + 5), (b'abc', 0)):
            with self.assertRaises(stage.Refused):
                stage.stage(self.row, self.response(content), deadline)
            self.assertFalse((self.root / 'example.py').exists())
            # Fixture-only cleanup, never performed by the production stager.
            for partial in self.root.glob('.stage-*.partial'):
                partial.unlink()


if __name__ == '__main__':
    unittest.main()
