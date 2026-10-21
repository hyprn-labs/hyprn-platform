"""Operator cloud mutations are pinned, redacted, single-attempt and reconciled."""
import base64
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import database_operator as operator
from test_database_setup import policy as database_policy
from contract import digest, Invalid


class GoogleFixture:
    def __init__(self, policy):
        self.policy = policy
        self.calls = []
        self.users = []
        self.secret_versions = {}
        self.payloads = {}
        self.operations = {}
        self.lose = None
        self.ca = b'fixture-ca'
        self.state = 'RUNNABLE'
        self.public = False

    def request(self, host, method, path, body=None):
        self.calls.append((host, method, path, body))
        db = self.policy['database']
        if host == 'sqladmin.googleapis.com':
            if '/operations/' in path:
                return self.operations[path.rsplit('/', 1)[-1]]
            if path.endswith('/instances/' + db['instance']):
                return {'project': db['project_id'], 'name': db['instance'], 'state': self.state,
                        'databaseVersion': 'POSTGRES_17',
                        'ipAddresses': [{'type': 'PRIVATE', 'ipAddress': db['private_ip']}],
                        'dnsNames': [{'connectionType': 'PRIVATE_SERVICES_ACCESS',
                                      'dnsScope': 'INSTANCE', 'name': db['server_name'] + '.'}],
                        'settings': {'ipConfiguration': {'ipv4Enabled': self.public,
                                     'sslMode': 'ENCRYPTED_ONLY',
                                     'serverCaMode': 'GOOGLE_MANAGED_CAS_CA'}},
                        'serverCaCert': {'cert': self.ca.decode()}}
            if method == 'GET':
                return {'items': self.users}
            name = 'fixture-operation-' + str(len(self.operations))
            value = {'name': name, 'targetProject': db['project_id'], 'targetId': db['instance'],
                     'operationType': 'CREATE_USER' if method == 'POST' else 'DELETE_USER',
                     'status': 'DONE'}
            self.operations[name] = value
            if method == 'POST':
                self.users.append({'name': body['name'], 'type': body['type']})
            else:
                self.users.clear()
            if self.lose == method:
                raise Invalid('synthetic_lost_response')
            return value
        name = path.removeprefix('/v1/')
        if name.endswith('/versions?pageSize=1000'):
            return {'versions': self.secret_versions.get(name.removesuffix('/versions?pageSize=1000'), [])}
        if name.endswith(':addVersion'):
            secret = name.removesuffix(':addVersion')
            record = {'name': secret + '/versions/1', 'state': 'ENABLED'}
            self.secret_versions.setdefault(secret, []).append(record)
            self.payloads[record['name']] = body['payload']
            if self.lose == 'secret':
                raise Invalid('synthetic_lost_response')
            return record
        if name.endswith(':access'):
            version = name.removesuffix(':access')
            return {'name': version, 'payload': self.payloads[version]}
        return {'name': name, 'state': 'ENABLED'}


class DatabaseOperatorTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(prefix='hyprn-db-operator-')
        self.addCleanup(self.scope.cleanup)
        self.root = Path(self.scope.name).resolve()
        self.private = self.root / 'private'
        self.private.mkdir(mode=0o700)
        self.db = database_policy()
        self.policy = dict(schema='hyprn-database-operator/v1', database=self.db,
            database_plan_sha256=digest(operator.database.plan(self.db)), project_number='123456789012',
            operator_account='operator@example.invalid', gcloud='/fixture/gcloud',
            gcloud_sha256='a'*64, gcloud_config='/fixture/config')
        self.approved = digest(operator.plan(self.policy))
        self.google = GoogleFixture(self.policy)
        self.passwords = {}
        for alias in operator.database.ROLES:
            path = self.root / alias
            path.write_text(hashlib.sha256(alias.encode()).hexdigest())
            path.chmod(0o600)
            self.passwords[alias] = path
        self.receipt = self.root / 'roles.json'
        self.receipt.write_text(json.dumps(dict(plan_sha256=self.policy['database_plan_sha256'],
            status='roles_verified', roles=operator.database.ROLES,
            credential_sha256={alias: hashlib.sha256(path.read_bytes()).hexdigest()
                               for alias, path in self.passwords.items()})))
        self.receipt.chmod(0o600)

    def operation(self):
        return operator.Operation(self.policy, self.private, self.google, self.approved)

    def create(self):
        with self.operation() as operation:
            operation.preflight()
            return operation.create_user()

    def test_plan_has_nine_empty_version_preconditions_and_preserves_assistant(self):
        value = operator.plan(self.policy)
        self.assertEqual(len(value['secret_versions']), 9)
        self.assertFalse(value['assistant_secret_change'])
        self.assertFalse(value['secret_iam_change'])
        self.assertFalse(value['automatic_mutation_retries'])
        self.assertTrue(all(v['existing_versions'] == [] for v in value['secret_versions'].values()))
        with self.assertRaises(Invalid):
            operator.plan(dict(self.policy, database_plan_sha256='b' * 64))

    def test_service_secrets_have_bound_receipts_and_no_provider_rewrite(self):
        with self.operation() as operation:
            auth = operation.prepare_secret('modeling-auth')
            rails = operation.prepare_secret('modeling-rails')
            self.assertNotEqual(Path(auth['password_file']).read_bytes(),
                                Path(rails['password_file']).read_bytes())
            for value in (auth, rails):
                result = operation.publish(value['alias'], value['password_file'],
                                           value['preparation_receipt'])
                self.assertEqual(result['status'], 'published')
            with self.assertRaises(Invalid):
                operation.prepare_secret('modeling-auth')
            with self.assertRaises(Invalid):
                operation.prepare_secret('assistant-provider')
            token = self.root / 'tunnel-token'
            token.write_bytes(b'synthetic opaque existing tunnel token')
            token.chmod(0o600)
            receipt = self.root / 'tunnel-receipt'
            receipt.write_text(json.dumps(dict(schema='hyprn-prepared-secret/v1',
                plan_sha256=self.approved, alias='cloudflare-tunnel',
                payload_sha256=hashlib.sha256(token.read_bytes()).hexdigest())))
            receipt.chmod(0o600)
            self.assertEqual(operation.publish('cloudflare-tunnel', token, receipt)['status'],
                             'published')
        self.assertFalse(any('assistant-provider' in c[2] for c in self.google.calls))

    def test_instance_drift_refuses_before_cloud_mutation(self):
        for field, value in [('state', 'STOPPED'), ('public', True), ('ca', b'other')]:
            with self.subTest(field=field):
                prior = getattr(self.google, field)
                setattr(self.google, field, value)
                with self.operation() as operation, self.assertRaises(Invalid):
                    operation.preflight()
                setattr(self.google, field, prior)
        self.assertTrue(all(call[1] == 'GET' for call in self.google.calls))

    def test_user_create_uses_body_secret_and_single_attempt(self):
        self.assertEqual(self.create()['status'], 'created')
        secret = operator.database.protected(self.private / 'bootstrap-password').decode()
        posts = [call for call in self.google.calls if call[1] == 'POST']
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][3]['password'], secret)
        self.assertNotIn(secret, posts[0][2])
        with self.assertRaises(Invalid):
            self.create()
        with self.operation() as operation:
            self.assertEqual(operation.create_user(reconcile=True)['status'], 'created')
        self.assertEqual(len([c for c in self.google.calls if c[1] == 'POST']), 1)

    def test_omitted_default_user_type_reconciles_without_second_creation(self):
        self.assertEqual(self.create()['status'], 'created')
        del self.google.users[0]['type']
        with self.operation() as operation:
            self.assertTrue(operation.user())
            self.assertEqual(operation.create_user(reconcile=True)['status'], 'created')
        self.assertEqual(len([call for call in self.google.calls if call[1] == 'POST']), 1)

    def test_explicit_invalid_user_type_and_duplicate_identity_are_rejected(self):
        name = self.policy['database']['bootstrap_role']
        for value in (None, '', 'CLOUD_IAM_USER', 'CLOUD_IAM_SERVICE_ACCOUNT', 0, False):
            with self.subTest(value=value), self.operation() as operation:
                self.google.users = [{'name': name, 'type': value}]
                with self.assertRaisesRegex(Invalid, 'database_operator_user_identity'):
                    operation.user()
        self.google.users = [{'name': name}, {'name': name, 'type': 'BUILT_IN'}]
        with self.operation() as operation:
            with self.assertRaisesRegex(Invalid, 'database_operator_user_identity'):
                operation.user()
        self.assertTrue(all(call[1] == 'GET' for call in self.google.calls))

    def test_lost_user_create_response_never_creates_again(self):
        self.google.lose = 'POST'
        with self.assertRaises(Invalid):
            self.create()
        self.google.lose = None
        with self.operation() as operation:
            result = operation.create_user(reconcile=True)
        self.assertEqual(result['status'], 'pending_or_uncertain')
        self.assertTrue(result['user_present'])
        with self.assertRaises(Invalid):
            self.create()
        self.assertEqual(len([c for c in self.google.calls if c[1] == 'POST']), 1)

    def test_secret_publication_reads_back_crc_and_exact_bytes(self):
        self.create()
        with self.operation() as operation:
            result = operation.publish('db-app-request', self.passwords['db-app-request'], self.receipt)
        self.assertEqual(result['status'], 'published')
        self.assertTrue(result['version'].endswith('/versions/1'))
        self.assertNotIn('a' * 64, json.dumps(result))
        with self.operation() as operation, self.assertRaises(Invalid):
            operation.publish('db-app-request', self.passwords['db-app-request'], self.receipt)

    def test_lost_secret_response_reconciles_without_adding_another_version(self):
        self.create()
        self.google.lose = 'secret'
        with self.operation() as operation, self.assertRaises(Invalid):
            operation.publish('db-app-auth', self.passwords['db-app-auth'], self.receipt)
        self.google.lose = None
        with self.operation() as operation:
            result = operation.publish('db-app-auth', self.passwords['db-app-auth'], self.receipt, reconcile=True)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(len([c for c in self.google.calls if c[2].endswith(':addVersion')]), 1)

    def test_wrong_role_password_refuses_before_secret_mutation(self):
        self.create()
        with self.operation() as operation, self.assertRaisesRegex(Invalid, 'role_password_mismatch'):
            operation.publish('db-app-auth', self.passwords['db-app-request'], self.receipt)
        self.assertFalse(any(c[2].endswith(':addVersion') for c in self.google.calls))

    def test_existing_version_or_wrong_alias_prevents_publication(self):
        self.create()
        with self.operation() as operation:
            name = operation.secret_name('db-app-auth')
            self.google.secret_versions[name] = [{'name': name + '/versions/1', 'state': 'DISABLED'}]
            with self.assertRaises(Invalid):
                operation.publish('db-app-auth', self.passwords['db-app-auth'], self.receipt)
            with self.assertRaises(Invalid):
                operation.publish('assistant-provider', self.passwords['db-app-auth'], self.receipt)
        self.assertFalse(any(c[2].endswith(':addVersion') for c in self.google.calls))

    def test_changed_secret_payload_cannot_be_adopted_after_uncertain_write(self):
        self.create()
        self.google.lose = 'secret'
        with self.operation() as operation, self.assertRaises(Invalid):
            operation.publish('db-app-auth', self.passwords['db-app-auth'], self.receipt)
        self.google.lose = None
        version = next(iter(self.google.payloads))
        self.google.payloads[version]['data'] = base64.b64encode(b'different').decode()
        with self.operation() as operation, self.assertRaisesRegex(Invalid, 'secret_readback'):
            operation.publish('db-app-auth', self.passwords['db-app-auth'], self.receipt, reconcile=True)

    def test_delete_requires_role_receipt_and_all_numeric_secret_pins(self):
        self.create()
        receipt = self.receipt
        with self.operation() as operation:
            with self.assertRaises(FileNotFoundError):
                operation.delete_user(receipt)
            self.assertFalse(any(c[1] == 'DELETE' for c in self.google.calls))
            for alias in operator.database.ROLES:
                operation.publish(alias, self.passwords[alias], self.receipt)
            result = operation.delete_user(receipt)
        self.assertEqual(result['status'], 'deleted')
        self.assertTrue(result['database_authority_verification_required'])
        with self.operation() as operation:
            self.assertEqual(operation.delete_user(None, reconcile=True)['status'], 'deleted')
        self.assertEqual(len([c for c in self.google.calls if c[1] == 'DELETE']), 1)

    def test_cli_approval_gate_does_not_obtain_an_identity(self):
        path = self.root / 'policy.json'
        path.write_text(json.dumps(self.policy))
        with patch.object(operator, 'Google') as google, patch('sys.stdout', StringIO()) as output:
            status = operator.main(['create-user', '--policy', str(path), '--private-root',
                                    str(self.private), '--approve-sha256', '0' * 64])
        self.assertEqual(status, 3)
        google.assert_not_called()
        self.assertIn('exact_approval', output.getvalue())

    def test_http_boundary_has_fixed_destination_body_and_no_redirect(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_POST(self):
                captured.append((self.path, self.headers['Authorization'],
                                 self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"name":"fixture-operation"}')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        original = http.client.HTTPConnection
        google = operator.Google.__new__(operator.Google)
        google.token = 'synthetic-token'
        def https(host, **kwargs):
            self.assertEqual(host, 'sqladmin.googleapis.com')
            return original('127.0.0.1', server.server_port, **kwargs)
        try:
            with patch.object(operator.http.client, 'HTTPSConnection', https):
                self.assertEqual(google.request('sqladmin.googleapis.com', 'POST', '/fixture',
                    {'password': 'synthetic-password'})['name'], 'fixture-operation')
            self.assertEqual(captured, [('/fixture', 'Bearer synthetic-token',
                                        b'{"password":"synthetic-password"}')])
            with self.assertRaises(Invalid):
                google.request('attacker.invalid', 'POST', '/fixture', {})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
