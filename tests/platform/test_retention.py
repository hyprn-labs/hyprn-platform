"""Operational journal limits never select scientific or deployment data for deletion."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('retention_subject', ROOT / 'host/retention.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class RetentionTests(unittest.TestCase):
    def test_public_plan_is_deterministic_without_privilege_or_mutation(self):
        command = [sys.executable, '-I', '-B', str(ROOT / 'host/retention.py'), 'plan']
        first = subprocess.run(command, capture_output=True, check=True)
        second = subprocess.run(command, capture_output=True, check=True)
        self.assertEqual(first.stdout, second.stdout)
        plan = json.loads(first.stdout)
        self.assertFalse(plan['deletes_product_records'])
        self.assertFalse(plan['deletes_release_artifacts'])
        self.assertEqual(plan['limits']['SystemMaxUse'], '1G')
        self.assertEqual(plan['limits']['MaxRetentionSec'], '30day')
        self.assertEqual(plan['file'], str(subject.PATH))
        self.assertEqual(set(plan['sources']), {
            'retention.py', 'setup.py', 'reconcile.py', 'contract.py', 'secrets.py'})

    def test_fresh_and_existing_host_have_one_policy(self):
        from test_host_setup import policy
        text, mode = subject.setup.files(policy())[str(subject.PATH)]
        self.assertEqual(text, subject.configuration())
        self.assertEqual(mode, 0o644)
        daemon = json.loads(subject.setup.files(policy())['/etc/docker/daemon.json'][0])
        self.assertEqual(daemon['log-opts'], {'max-size': '10m', 'max-file': '3'})

    def test_later_override_or_missing_limit_refuses(self):
        for text in (subject.configuration() + '\n[Journal]\nSystemMaxUse=0\n',
                     subject.configuration().replace('MaxRetentionSec=30day\n', '')):
            with self.subTest(text=text), self.assertRaises(subject.Refused):
                subject.verify_effective(text)
        self.assertEqual(subject.verify_effective(
            '# vendor defaults\n[Journal]\nSystemMaxUse=4G\n' + subject.configuration())[
                'journal_limits'], 'verified')

    def test_wrong_approval_refuses_before_any_host_write(self):
        with patch.object(subject.setup, 'mkdir', side_effect=AssertionError('mutation')):
            with self.assertRaisesRegex(subject.Refused, 'approval_mismatch'):
                subject.apply('0' * 64)

    def apply_scope(self, root, raw=None):
        path = root / '80-hyprn-retention.conf'
        if raw is not None:
            path.write_text(raw)
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            return subject.configuration().encode() if 'cat-config' in command else b''
        stack = __import__('contextlib').ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(subject, 'PATH', path))
        stack.enter_context(patch.object(subject.sys, 'platform', 'linux'))
        stack.enter_context(patch.object(subject.setup.os, 'geteuid', return_value=0))
        stack.enter_context(patch.object(subject.setup.reconcile, 'protected', side_effect=Path))
        stack.enter_context(patch.object(subject.setup, 'mkdir', return_value=None))
        stack.enter_context(patch.object(subject.setup, 'write_new',
            side_effect=lambda name, content, mode: Path(name).write_bytes(content)))
        stack.enter_context(patch.object(subject.setup, 'run', side_effect=run))
        return path, calls

    def test_install_and_repeat_preserve_unrelated_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            retained = root / 'scientific-store'
            retained.write_bytes(b'retained')
            path, calls = self.apply_scope(root)
            for _ in range(2):
                result = subject.apply(subject.plan()['plan_sha256'])
                self.assertEqual(result['journal_limits'], 'verified')
            self.assertEqual(path.read_text(), subject.configuration())
            self.assertEqual(retained.read_bytes(), b'retained')
            self.assertEqual(sum('restart' in command for command in calls), 2)
            self.assertFalse(any('vacuum' in ' '.join(command) for command in calls))

    def test_existing_other_policy_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, calls = self.apply_scope(Path(temporary), '[Journal]\nSystemMaxUse=4G\n')
            before = path.read_bytes()
            with self.assertRaisesRegex(subject.Refused, 'existing_policy'):
                subject.apply(subject.plan()['plan_sha256'])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
