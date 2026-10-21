"""Database provisioning refuses drift and uncertain writes; no cloud mutation."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import database_setup as setup
from contract import Invalid, digest


def policy():
    return dict(schema='hyprn-database-setup/v1', project_id='hyprn-staging-fixture',
                instance='hyprn-staging-app', installation_id='fixture-staging',
                database='hyprn_app', private_ip='10.82.0.3',
                server_name='abcdef.abcdef.europe-west1.sql-psa.goog',
                ca_sha256=hashlib.sha256(b'fixture-ca').hexdigest(),
                bootstrap_role='hyprn_bootstrap_01234567')


class Cursor:
    description = None

    def __init__(self, db):
        self.db = db
        self.result = []

    def execute(self, statement):
        store = self.db.store
        store.calls.append(statement)
        self.description = None
        if statement.startswith('SELECT'):
            self.description = [('value',)]
            self.result = []
        if statement == setup.ROLE_SQL:
            self.result = sorted(store.roles.values())
        elif statement == setup.MEMBER_SQL:
            self.result = store.members
        elif statement.startswith('SELECT current_database'):
            self.result = [(store.policy['database'], self.db.role)]
        elif statement.startswith('SELECT pg_has_role'):
            self.result = [(True,)]
        elif statement.startswith("SELECT 1 FROM pg_roles WHERE rolname="):
            self.result = [(1,)] if store.bootstrap_present else []
        elif statement.startswith('SELECT ssl'):
            self.result = [(store.tls,)]
        elif statement.startswith('SELECT has_database_privilege'):
            self.result = [(True, False, False, True, self.db.role == 'hyprn_migration')]
        elif statement.startswith('SELECT 1 FROM pg_class') and store.occupied:
            self.result = [(1,)]
        elif statement.startswith('CREATE ROLE '):
            # An intent and all passwords must already exist before the first side effect.
            assert (store.root / 'intent.json').exists()
            assert all((store.root / alias).exists() for alias in setup.ROLES)
            role = statement.split()[2]
            store.roles[role] = (role, False, False, False, False, True, False, False, None)
        elif statement.startswith('COMMENT ON ROLE '):
            role = statement.split()[3]
            marker = statement.split("'")[1]
            store.roles[role] = (*store.roles[role][:-1], marker)

    def fetchall(self):
        return self.result

    def close(self):
        pass


class Connection:
    def __init__(self, store, role):
        self.store = store
        self.role = role

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.store.commits += 1
        if self.store.lost_commit:
            raise RuntimeError('synthetic-secret-in-driver-error')

    def close(self):
        pass


class Store:
    def __init__(self, policy, root):
        self.policy, self.root = policy, root
        self.calls, self.roles, self.members = [], {}, []
        self.commits = 0
        self.lost_commit = self.occupied = False
        self.tls = True
        self.bootstrap_present = True
        self.passwords = {}

    def connect(self, policy, ca, role, password):
        assert policy == self.policy
        assert ca == b'fixture-ca'
        if role in self.passwords and self.passwords[role] != password:
            raise RuntimeError('password mismatch')
        self.passwords[role] = password
        return Connection(self, role)


class DatabaseSetupTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(prefix='hyprn-database-fixture-')
        self.addCleanup(self.scope.cleanup)
        self.root = Path(self.scope.name).resolve()
        self.private = self.root / 'private'
        self.private.mkdir(mode=0o700)
        self.ca = self.root / 'ca.pem'
        self.ca.write_bytes(b'fixture-ca')
        self.ca.chmod(0o600)
        self.admin = self.root / 'admin'
        self.admin.write_bytes(b'fixture-bootstrap-password')
        self.admin.chmod(0o600)
        self.policy = policy()
        self.approved = digest(setup.plan(self.policy))
        self.store = Store(self.policy, self.private)

    def run_setup(self, **kwargs):
        return setup.execute(self.policy, self.ca, self.admin, self.private,
                             self.approved, connector=self.store.connect,
                             require_memory=False, **kwargs)

    def test_plan_is_fixed_to_private_verified_tls_and_exact_ordinary_roles(self):
        plan = setup.plan(self.policy)
        self.assertEqual(plan['tls'], 'verify-full')
        self.assertEqual(plan['driver'], 'pg8000==1.31.5')
        self.assertEqual(len(plan['roles']), 6)
        self.assertEqual(plan['schema_grants']['public']['CREATE'], ['hyprn_migration'])
        self.assertIn('NOINHERIT', plan['authority'])
        self.assertIn('NOBYPASSRLS', plan['authority'])
        self.assertEqual(set(plan['sources']), {'database_setup.py', 'contract.py', 'secrets.py'})
        self.assertFalse(plan['product_started'])

    def test_unknown_policy_or_public_endpoint_is_rejected(self):
        for key, value in [('extra', True), ('private_ip', '169.254.169.254'),
                           ('private_ip', '8.8.8.8'), ('private_ip', '127.0.0.1'),
                           ('bootstrap_role', 'postgres'), ('database', "bad'; DROP ROLE x;"),
                           ('server_name', 'evil.example'), ('ca_sha256', 'x')]:
            with self.subTest(key=key, value=value), self.assertRaises(Invalid):
                setup.plan(dict(self.policy, **{key: value}))

    def test_exact_approval_precedes_any_connection(self):
        self.approved = '0' * 64
        with self.assertRaisesRegex(Invalid, 'exact_approval'):
            self.run_setup()
        self.assertEqual(self.store.calls, [])

    def test_ca_pin_precedes_any_connection(self):
        self.ca.write_bytes(b'changed')
        with self.assertRaisesRegex(Invalid, 'ca_pin'):
            self.run_setup()
        self.assertEqual(self.store.calls, [])

    def test_success_uses_distinct_secrets_and_confirms_authority(self):
        result = self.run_setup()
        passwords = [setup.protected(self.private / alias) for alias in setup.ROLES]
        self.assertEqual(len(set(passwords)), 6)
        self.assertEqual(self.store.commits, 1)
        self.assertEqual(result['status'], 'roles_verified')
        self.assertFalse(result['secrets_uploaded'])
        self.assertFalse(result['bootstrap_admin_removed'])
        statements = '\n'.join(self.store.calls)
        for password in passwords:
            self.assertNotIn(password.decode(), statements)
            self.assertNotIn(password.decode(), json.dumps(result))
        self.assertEqual(statements.count('CREATE ROLE '), 6)
        self.assertIn('REVOKE ALL ON DATABASE hyprn_app FROM PUBLIC', statements)
        self.assertIn('GRANT CREATE ON SCHEMA public TO hyprn_migration', statements)

    def test_a_second_apply_refuses_without_changing_roles(self):
        self.run_setup()
        count = len(self.store.calls)
        with self.assertRaisesRegex(Invalid, 'attempt_exists'):
            self.run_setup()
        self.assertEqual(len(self.store.calls), count)

    def test_reconcile_after_lost_commit_only_reads_and_authenticates(self):
        self.store.lost_commit = True
        with self.assertRaises(RuntimeError):
            self.run_setup()
        self.store.calls.clear()
        self.store.lost_commit = False
        self.assertEqual(self.run_setup(reconcile=True)['status'], 'roles_verified')
        self.assertEqual(self.store.commits, 1)
        self.assertFalse(any(c.startswith(('CREATE', 'GRANT', 'REVOKE', 'COMMENT'))
                             for c in self.store.calls))

    def test_reconcile_uncommitted_transaction_never_retries(self):
        self.run_setup()
        self.store.roles.clear()
        self.assertEqual(self.run_setup(reconcile=True)['status'], 'not_committed')
        self.assertEqual(self.store.commits, 1)

    def test_drifted_role_membership_blocks_reconciliation(self):
        self.run_setup()
        self.store.members = [('cloudsqlsuperuser', 'hyprn_request', False, True, True)]
        with self.assertRaisesRegex(Invalid, 'role_membership'):
            self.run_setup(reconcile=True)

    def test_final_verification_rejects_temporary_membership_until_admin_removed(self):
        self.run_setup()
        self.store.members = [('hyprn_request', self.policy['bootstrap_role'], True, False, False)]
        self.assertEqual(self.run_setup(reconcile=True)['status'], 'roles_verified')
        with self.assertRaisesRegex(Invalid, 'role_membership'):
            self.run_setup(verify=True)
        self.store.members.clear()
        with self.assertRaisesRegex(Invalid, 'bootstrap_admin_still_exists'):
            self.run_setup(verify=True)
        self.store.bootstrap_present = False
        self.assertTrue(self.run_setup(verify=True)['bootstrap_admin_removed'])

    def test_drifted_role_flags_or_marker_block_reconciliation(self):
        self.run_setup()
        row = self.store.roles['hyprn_request']
        self.store.roles['hyprn_request'] = (row[0], True, *row[2:])
        with self.assertRaisesRegex(Invalid, 'authority_or_marker'):
            self.run_setup(reconcile=True)

    def test_existing_objects_or_unencrypted_connection_block_mutation(self):
        for field in ('occupied', 'tls'):
            with self.subTest(field=field):
                self.store.occupied = field == 'occupied'
                self.store.tls = field != 'tls'
                with self.assertRaises(Invalid):
                    self.run_setup()
                self.assertEqual(self.store.commits, 0)
                self.assertFalse((self.private / 'intent.json').exists())

    def test_private_files_reject_world_readable_symlink_and_hardlink(self):
        self.admin.chmod(0o644)
        with self.assertRaises(Invalid):
            setup.protected(self.admin)
        self.admin.chmod(0o600)
        link = self.root / 'link'
        link.symlink_to(self.admin)
        with self.assertRaises(Invalid):
            setup.protected(link)
        link.unlink()
        os.link(self.admin, link)
        with self.assertRaises(Invalid):
            setup.protected(self.admin)

    def test_scram_verifier_matches_postgresql_password_algorithm(self):
        password = b'synthetic fixture secret'
        verifier = setup.scram(password)
        mechanism, iterations_salt, keys = verifier.split('$')
        iterations, salt = iterations_salt.split(':')
        stored, server = map(base64.b64decode, keys.split(':'))
        derived = hashlib.pbkdf2_hmac('sha256', password, base64.b64decode(salt), int(iterations))
        self.assertEqual(mechanism, 'SCRAM-SHA-256')
        self.assertEqual(stored, hashlib.sha256(hmac.digest(derived, b'Client Key', 'sha256')).digest())
        self.assertEqual(server, hmac.digest(derived, b'Server Key', 'sha256'))

    def test_cli_sanitizes_unexpected_errors(self):
        path = self.root / 'policy.json'
        path.write_text(json.dumps(self.policy))
        with patch.object(setup, 'execute', side_effect=RuntimeError('secret-value')):
            from io import StringIO
            output = StringIO()
            with patch('sys.stdout', output):
                status = setup.main(['apply', '--policy', str(path), '--ca-file', str(self.ca),
                                     '--admin-password-file', str(self.admin), '--private-root',
                                     str(self.private), '--approve-sha256', self.approved])
        self.assertEqual(status, 3)
        self.assertNotIn('secret-value', output.getvalue())
        self.assertIn('database_operation_uncertain', output.getvalue())


if __name__ == '__main__':
    unittest.main()
