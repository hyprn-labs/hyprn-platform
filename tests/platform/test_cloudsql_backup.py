"""Real CLI and HTTP boundary doubles; not live Cloud SQL or TLS qualification."""
import copy
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
PROJECT = 'hyprn-staging-fixture'
INSTANCE = 'fixture-db'
RESOURCE = 'projects/' + PROJECT + '/instances/' + INSTANCE
BASE = '/v1/' + RESOURCE
SECRET = 'synthetic-sensitive-token'
HARNESS = '''
import http.client, os, sys
sys.path.insert(0, sys.argv.pop(1))
original = http.client.HTTPConnection
def metadata(host, **kwargs):
    assert host == '169.254.169.254'
    return original('127.0.0.1', int(os.environ['FIXTURE_PORT']), **kwargs)
def api(host, **kwargs):
    assert host == 'sqladmin.googleapis.com'
    return original('127.0.0.1', int(os.environ['FIXTURE_PORT']), **kwargs)
http.client.HTTPConnection = metadata
http.client.HTTPSConnection = api
import cloudsql_backup
raise SystemExit(cloudsql_backup.main())
'''


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(prefix='hyprn-cloudsql-')
        self.addCleanup(self.scope.cleanup)
        self.root = Path(self.scope.name).resolve()
        self.private = self.root / 'private'
        self.private.mkdir(mode=0o700)
        self.calls = []
        self.backups = []
        self.mode = 'ok'
        self.statuses = []
        self.operation_patch = {}
        self.instance_patch = {}
        self.backup_patch = {}
        self.list_patch = {}
        self.post_intent = None
        test = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.dispatch()

            def do_POST(self):
                self.dispatch()

            def dispatch(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                test.calls.append((self.command, self.path, body))
                if self.path.startswith('/computeMetadata/v1/'):
                    if self.headers.get('Metadata-Flavor') != 'Google':
                        return self.answer(400, {})
                    value = {'project-id': PROJECT, 'numeric-project-id': '123456789012',
                             'email': 'hyprn-staging-runtime@' + PROJECT + '.iam.gserviceaccount.com',
                             'token': {'access_token': SECRET, 'token_type': 'Bearer', 'expires_in': 3600}}[self.path.split('/')[-1]]
                    if test.mode == 'principal' and self.path.endswith('/email'):
                        value = 'untrusted@invalid.test'
                    return self.answer(200, value, metadata=True)
                if self.headers.get('Authorization') != 'Bearer ' + SECRET:
                    return self.answer(403, {'secret': SECRET})
                path = urlsplit(self.path)
                if path.path == BASE:
                    value = {'kind': 'sql#instance', 'project': PROJECT, 'name': INSTANCE,
                             'state': 'RUNNABLE', 'databaseVersion': 'POSTGRES_17',
                             'createTime': '2026-01-01T00:00:00Z',
                             'settings': {'backupConfiguration': {'backupTier': 'STANDARD', 'enabled': True},
                                          'ipConfiguration': {'ipv4Enabled': False, 'sslMode': 'ENCRYPTED_ONLY',
                                                              'privateNetwork': 'projects/' + PROJECT + '/global/networks/fixture-net'}}}
                    value.update(test.instance_patch)
                    return self.answer(200, value)
                if path.path == BASE + '/backupRuns' and self.command == 'POST':
                    test.post_intent = json.loads((test.private / 'intent.json').read_text())
                    backup = {'kind': 'sql#backupRun', 'instance': INSTANCE, 'id': '42',
                              'selfLink': 'https://sqladmin.googleapis.com' + BASE + '/backupRuns/42',
                              'type': 'ON_DEMAND', 'status': 'SUCCESSFUL', 'backupKind': 'PHYSICAL',
                              'description': json.loads(body)['description'],
                              'enqueuedTime': '2026-10-21T01:00:00Z',
                              'startTime': '2026-10-21T01:00:01Z', 'endTime': '2026-10-21T01:00:10Z'}
                    test.backups.append(backup)
                    if test.mode == 'lost':
                        self.close_connection = True
                        return
                    if test.mode == 'post-error':
                        return self.answer(503, {'error': {'message': SECRET}})
                    value = {'kind': 'sql#operation', 'targetProject': PROJECT, 'targetId': INSTANCE,
                             'operationType': 'BACKUP_VOLUME', 'status': 'PENDING', 'name': 'operation-42'}
                    value.update(test.operation_patch)
                    return self.answer(200, value)
                if path.path == BASE + '/backupRuns':
                    if test.mode in ('read-error', 'denied'):
                        return self.answer(403 if test.mode == 'denied' else 500, {'error': SECRET})
                    if test.mode == 'redirect':
                        self.send_response(302)
                        self.send_header('Location', 'https://attacker.invalid/' + SECRET)
                        self.end_headers()
                        return
                    if test.mode == 'invalid-json':
                        return self.answer(200, b'{bad sensitive ' + SECRET.encode())
                    if test.mode == 'oversize':
                        return self.answer(200, b'x' * 1100000)
                    items = [] if test.mode in ('zero', 'exhaust') else copy.deepcopy(test.backups)
                    if test.mode == 'ambiguous':
                        items += copy.deepcopy(items)
                    for item in items:
                        item.update(test.backup_patch)
                    page = parse_qs(path.query).get('pageToken')
                    value = {'kind': 'sql#backupRunsList', 'items': items}
                    if test.mode == 'pagination' and not page:
                        value = {'kind': 'sql#backupRunsList', 'items': [], 'nextPageToken': 'page /?two'}
                    if test.mode == 'pagination-ambiguous' and not page:
                        value['nextPageToken'] = 'second'
                    if test.mode == 'exhaust':
                        value['nextPageToken'] = str(int(page[0]) + 1) if page else '1'
                    if test.mode == 'cycle':
                        value['nextPageToken'] = 'same'
                    value.update(test.list_patch)
                    return self.answer(200, value)
                if path.path == BASE + '/backupRuns/42':
                    value = copy.deepcopy(test.backups[0])
                    value.update(test.backup_patch)
                    if test.statuses:
                        value['status'] = test.statuses.pop(0)
                    if test.mode == 'get-wrong':
                        value['id'] = '43'
                    return self.answer(200, value)
                return self.answer(404, {'error': SECRET})

            def answer(self, status, value, metadata=False):
                data = value if isinstance(value, bytes) else (value.encode() if isinstance(value, str) else json.dumps(value).encode())
                self.send_response(status)
                self.send_header('Content-Length', str(len(data)))
                if metadata:
                    self.send_header('Metadata-Flavor', 'Google')
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def command(self, operation='create', extra=()):
        args = [sys.executable, '-B', '-c', HARNESS, str(ROOT / 'host'), operation,
                '--project-id', PROJECT, '--project-number', '123456789012',
                '--instance', INSTANCE, '--installation-id', 'fixture-installation',
                '--private-network', 'projects/' + PROJECT + '/global/networks/fixture-net',
                '--release-digest', 'sha256:' + 'a' * 64,
                '--configuration-digest', 'sha256:' + 'b' * 64,
                '--operation-id', '00000000-0000-4000-8000-000000000001',
                '--state-root', str(self.private), '--poll-attempts', '2', '--poll-seconds', '0']
        if operation == 'create':
            args += ['--approve-resource', RESOURCE]
        env = {'PATH': os.environ['PATH'], 'FIXTURE_PORT': str(self.server.server_port),
               'HTTP_PROXY': 'http://invalid.test', 'HTTPS_PROXY': 'http://invalid.test',
               'GOOGLE_APPLICATION_CREDENTIALS': '/nonexistent/untrusted-credentials'}
        return subprocess.run(args + list(extra), capture_output=True, timeout=15, env=env)

    def success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        value = json.loads(result.stdout)
        self.assertEqual(value['scope'], 'cloudsql-database-only')
        self.assertFalse(value['coherent_installation_backup'])
        self.assertEqual(value['status'], 'complete')
        return value

    def rejected(self, result, code=None):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b'')
        self.assertNotIn(SECRET.encode(), result.stderr)
        if code:
            self.assertEqual(json.loads(result.stderr)['error'], code)

    def posts(self):
        return [call for call in self.calls if call[0] == 'POST']

    def test_intent_is_durable_before_dispatch_and_receipt_is_database_only(self):
        receipt = self.success(self.command())
        self.assertEqual(receipt['backup_id'], '42')
        self.assertEqual(self.post_intent['binding']['instance'], INSTANCE)
        self.assertEqual(len(self.posts()), 1)
        for path in self.private.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(SECRET, path.read_text())
        self.success(self.command())
        self.success(self.command('verify'))
        self.success(self.command('resume'))
        self.assertEqual(len(self.posts()), 1)

    def test_lost_response_resumes_by_reading_all_pages_without_reposting(self):
        self.mode = 'lost'
        self.rejected(self.command(), 'backup_dispatch_uncertain')
        self.mode = 'pagination'
        self.success(self.command('resume'))
        self.assertTrue(any('pageToken=page+%2F%3Ftwo' in c[1] for c in self.calls))
        self.assertEqual(len(self.posts()), 1)

    def test_zero_and_ambiguous_matches_never_repost_or_produce_receipt(self):
        self.mode = 'zero'
        self.rejected(self.command(), 'backup_not_found_reconcile')
        self.rejected(self.command(), 'backup_not_found_reconcile')
        self.mode = 'ambiguous'
        self.rejected(self.command('resume'), 'backup_ambiguous')
        self.assertEqual(len(self.posts()), 1)
        self.assertFalse((self.private / 'receipt.json').exists())

    def test_pending_poll_is_bounded_then_resume_can_complete(self):
        self.statuses = ['ENQUEUED', 'RUNNING']
        self.rejected(self.command(), 'backup_pending')
        self.assertEqual(len([c for c in self.calls if c[1].endswith('/42')]), 2)
        self.success(self.command('resume'))
        self.assertEqual(len(self.posts()), 1)

    def test_failed_deleted_and_unknown_backup_states_are_not_completion(self):
        self.mode = 'lost'
        self.rejected(self.command())
        self.mode = 'ok'
        for status in ('FAILED', 'DELETED', 'DELETION_PENDING', 'SKIPPED', 'OVERDUE', 'unknown'):
            with self.subTest(status=status):
                self.backup_patch = {'status': status, 'error': {'message': SECRET}}
                self.rejected(self.command('resume'))
                self.assertFalse((self.private / 'receipt.json').exists())
        self.assertEqual(len(self.posts()), 1)

    def test_provider_and_transport_errors_are_sanitized_and_do_not_retry_post(self):
        self.mode = 'post-error'
        self.rejected(self.command(), 'backup_dispatch_uncertain')
        for mode in ('read-error', 'denied', 'redirect', 'invalid-json', 'oversize', 'cycle'):
            self.mode = mode
            self.rejected(self.command('resume'))
        self.assertEqual(len(self.posts()), 1)
        self.assertNotIn(SECRET, (self.private / 'status.json').read_text())

    def test_cross_identity_and_malformed_backups_fail_closed(self):
        self.mode = 'lost'
        self.rejected(self.command())
        self.mode = 'ok'
        for patch in ({'instance': 'other'}, {'type': 'AUTOMATED'}, {'id': True}, {'selfLink': []},
                      {'selfLink': 'https://attacker.invalid' + BASE + '/backupRuns/42'},
                      {'selfLink': 'https://sqladmin.googleapis.com' + BASE.replace(PROJECT, 'wrong') + '/backupRuns/42'},
                      {'description': 'unrelated'}, {'kind': 'wrong'}, {'endTime': 'garbage'},
                      {'endTime': '2025-01-01T00:00:00Z'}, {'error': {'message': SECRET}}):
            with self.subTest(patch=patch):
                self.backup_patch = patch
                self.rejected(self.command('resume'))
        self.backup_patch = {}
        self.mode = 'get-wrong'
        self.rejected(self.command('resume'))
        self.assertEqual(len(self.posts()), 1)

    def test_wrong_operation_identity_is_uncertain_and_never_reposted(self):
        self.operation_patch = {'targetProject': 'wrong'}
        self.rejected(self.command(), 'backup_dispatch_uncertain')
        self.success(self.command('resume'))
        self.assertEqual(len(self.posts()), 1)

    def test_wrong_instance_identity_and_nonstandard_tier_stop_before_intent(self):
        for patch in ({'project': 'wrong'}, {'name': 'other'}, {'state': 'FAILED'},
                      {'settings': {'backupConfiguration': {'backupTier': 'ADVANCED'}}}):
            self.instance_patch = patch
            self.rejected(self.command())
            self.assertFalse((self.private / 'intent.json').exists())
        self.assertEqual(self.posts(), [])

    def test_source_requires_reviewed_postgres_and_private_network_policy(self):
        baseline = {'backupConfiguration': {'backupTier': 'STANDARD', 'enabled': True},
                    'ipConfiguration': {'ipv4Enabled': False, 'sslMode': 'ENCRYPTED_ONLY',
                                        'privateNetwork': 'projects/' + PROJECT + '/global/networks/fixture-net'}}
        self.instance_patch = {'databaseVersion': 'POSTGRES_16'}
        self.rejected(self.command(), 'source_database_version')
        for key, value in (('ipv4Enabled', True), ('ipv4Enabled', 0), ('sslMode', 'ALLOW_UNENCRYPTED_AND_ENCRYPTED'),
                           ('privateNetwork', 'projects/other/global/networks/wrong')):
            settings = copy.deepcopy(baseline)
            settings['ipConfiguration'][key] = value
            self.instance_patch = {'settings': settings}
            self.rejected(self.command(), 'source_network_policy')
        settings = copy.deepcopy(baseline)
        settings['backupConfiguration']['enabled'] = False
        self.instance_patch = {'settings': settings}
        self.rejected(self.command(), 'standard_backup_required')
        self.assertEqual(self.posts(), [])
        self.assertFalse((self.private / 'intent.json').exists())

    def test_principal_approval_and_path_validation_happen_before_dispatch(self):
        self.rejected(self.command(extra=('--approve-resource', 'wrong')))
        self.rejected(self.command(extra=('--instance', '../wrong')))
        self.assertEqual(self.calls, [])
        self.mode = 'principal'
        self.rejected(self.command(), 'attached_identity_mismatch')
        self.assertFalse(any(c[1].endswith('/token') for c in self.calls))
        self.assertEqual(self.posts(), [])

    def test_read_only_commands_cannot_create_without_intent(self):
        self.rejected(self.command('resume'), 'backup_intent_missing')
        self.rejected(self.command('verify'), 'backup_intent_missing')
        self.assertEqual(self.calls, [])

    def test_changed_binding_and_replaced_source_stop_before_dispatch(self):
        self.success(self.command())
        before = len(self.calls)
        for flag, value in (('--installation-id', 'other'), ('--release-digest', 'sha256:' + 'c' * 64),
                            ('--configuration-digest', 'sha256:' + 'd' * 64),
                            ('--operation-id', '00000000-0000-4000-8000-000000000002')):
            self.rejected(self.command('resume', extra=(flag, value)), 'backup_intent_mismatch')
        self.assertEqual(len(self.calls), before)
        self.instance_patch = {'createTime': '2026-10-20T00:00:00Z'}
        self.rejected(self.command('resume'), 'source_instance_changed')
        self.assertEqual(len(self.posts()), 1)

    def test_private_state_rejects_symlinks_modes_hardlinks_corruption_and_lock(self):
        self.private.chmod(0o755)
        self.rejected(self.command())
        self.private.chmod(0o700)
        link = self.root / 'linked'
        link.symlink_to(self.private)
        self.rejected(self.command(extra=('--state-root', str(link))))
        fd = os.open(self.private, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self.rejected(self.command())
        finally:
            os.close(fd)
        self.assertEqual(self.calls, [])
        outside = self.root / 'outside'
        outside.write_text('{}')
        outside.chmod(0o600)
        intent = self.private / 'intent.json'
        intent.symlink_to(outside)
        self.rejected(self.command())
        intent.unlink()
        os.link(outside, intent)
        self.rejected(self.command())
        intent.unlink()
        intent.write_text('{corrupt')
        intent.chmod(0o600)
        self.rejected(self.command())
        self.assertEqual(self.calls, [])
        self.assertEqual(outside.read_text(), '{}')

    def test_match_on_first_page_is_not_accepted_before_last_page(self):
        self.mode = 'pagination-ambiguous'
        self.rejected(self.command(), 'backup_ambiguous')
        self.assertFalse((self.private / 'receipt.json').exists())
        self.assertFalse(any(c[1].endswith('/42') for c in self.calls))
        self.mode = 'exhaust'
        self.rejected(self.command('resume'), 'provider_pagination_limit')
        self.assertEqual(len(self.posts()), 1)

    def test_completed_receipt_is_reverified_and_never_trusted_after_deletion(self):
        self.success(self.command())
        receipt = (self.private / 'receipt.json').read_bytes()
        self.backup_patch = {'status': 'DELETED'}
        self.rejected(self.command('verify'), 'backup_unavailable')
        self.assertEqual((self.private / 'receipt.json').read_bytes(), receipt)
        self.assertEqual(json.loads((self.private / 'status.json').read_text())['status'], 'closed')
        self.assertEqual(len(self.posts()), 1)

    def test_malformed_list_and_status_file_fail_without_receipt_or_redispatch(self):
        self.mode = 'lost'
        self.rejected(self.command())
        self.mode = 'ok'
        for patch in ({'kind': 'wrong'}, {'items': {}}, {'nextPageToken': True}):
            self.list_patch = patch
            self.rejected(self.command('resume'))
        self.list_patch = {}
        state = self.private / 'status.json'
        state.chmod(0o644)
        before = len(self.calls)
        self.rejected(self.command('resume'))
        self.assertEqual(len(self.calls), before)
        self.assertEqual(len(self.posts()), 1)

    def test_invalid_poll_limits_and_unsupported_modes_do_not_dispatch(self):
        for extra in (('--poll-attempts', '0'), ('--poll-attempts', '10000'), ('--poll-seconds', '-1')):
            self.rejected(self.command(extra=extra))
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
