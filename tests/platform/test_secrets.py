"""CLI/filesystem acceptance with synthetic cloud responses and explicit host seams.

Darwin cannot prove Linux tmpfs or root-to-service UID assignment. The harness
replaces only those two host facts; production CLI has no bypass flag.
"""
import copy
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "host/secrets.py"
SYNTHETIC = b"synthetic-provider-secret-\x00\xff"
STUB = r'''
import base64, json, os, pathlib, sys
assert os.environ['CLOUDSDK_CORE_DISABLE_FILE_LOGGING'] == 'true'
assert os.environ['CLOUDSDK_CORE_LOG_HTTP'] == 'false'
assert 'CLOUDSDK_API_ENDPOINT_OVERRIDES_SECRET_MANAGER' not in os.environ
root = pathlib.Path(__file__).parent
mode = (root / 'mode').read_text()
args = sys.argv[1:]
with (root / 'calls').open('a') as stream:
    stream.write(json.dumps(args) + '\n')
if 'projects' in args:
    print('999999999999' if mode == 'project' else '123456789012')
elif 'describe' in args:
    print('projects/123456789012/secrets/' + ('wrong' if mode == 'identity' else 'hyprn-staging-assistant-provider'))
elif 'access' in args:
    if mode == 'fetch-fail' and '--secret=hyprn-staging-assistant-provider' in args:
        print('synthetic-provider-secret', file=sys.stderr)
        sys.exit(1)
    print('!!!' if mode == 'bad-base64' else base64.urlsafe_b64encode(b'synthetic-provider-secret-\x00\xff').decode())
elif 'add' in args:
    assert sys.stdin.buffer.read() == b'synthetic-provider-secret-\x00\xff'
    assert '--data-file=-' in args
    if mode == 'uncertain':
        print('synthetic-provider-secret', file=sys.stderr)
        sys.exit(1)
    print('projects/123456789012/secrets/hyprn-staging-assistant-provider/versions/7')
else:
    sys.exit(3)
'''
HARNESS = '''
import sys, os, json, base64
sys.path.insert(0, sys.argv.pop(1))
import secrets as subject
subject.require_tmpfs = lambda fd: None
subject.owner = lambda runtime, consumer: os.geteuid()
if '--identity-mode' in sys.argv and 'attached-service-account' in sys.argv:
    root = __import__('pathlib').Path(os.environ['HOME'])
    runtime = json.loads((root / 'runtime.json').read_text())
    mode = (root / 'mode').read_text()
    def request(metadata, path, token=None):
        with (root / 'metadata-calls').open('a') as stream:
            stream.write(path + '\\n')
        if metadata:
            assert token is None
            if path.endswith('/numeric-project-id'): return b'123456789012'
            if path.endswith('/project-id'): return runtime['project_id'].encode()
            if path.endswith('/email'):
                return (('wrong' if mode == 'principal' else 'hyprn-staging-runtime') + '@' + runtime['project_id'] + '.iam.gserviceaccount.com').encode()
            if path.endswith('/token'):
                return json.dumps({'access_token': 'synthetic-token', 'token_type': 'Bearer', 'expires_in': 3600}).encode()
            raise AssertionError(path)
        assert token == 'synthetic-token'
        return json.dumps({'name': path[4:-7], 'payload': {'data': 'MTIzNDU2Nzg5', 'dataCrc32c': '0' if mode == 'crc' else '3808858755'}}).encode()
    subject.request_google = request
raise SystemExit(subject.main())
'''


class SecretTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(prefix="hyprn-secrets-")
        self.addCleanup(self.scope.cleanup)
        self.root = Path(self.scope.name).resolve()
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.receipts = self.root / "receipts"
        self.receipts.mkdir(mode=0o700)
        self.key = self.root / "provider.key"
        self.key.write_bytes(SYNTHETIC)
        self.key.chmod(0o600)
        self.runtime = copy.deepcopy(json.loads((ROOT / "contracts/v1/fixtures.json").read_text())["valid"]["runtime"])
        self.runtime["project_number"] = "123456789012"
        self.document = self.root / "runtime.json"
        self.gcloud = self.root / "gcloud"
        self.gcloud.write_text("#!" + sys.executable + "\n" + STUB)
        self.gcloud.chmod(0o700)
        self.mode = self.root / "mode"
        self.mode.write_text("ok")
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.root),
                    "CLOUDSDK_CONFIG": str(self.root / "cloud-config"),
                    "GOOGLE_APPLICATION_CREDENTIALS": str(self.root / "no-live-credentials")}
        self.env['CLOUDSDK_API_ENDPOINT_OVERRIDES_SECRET_MANAGER'] = 'https://invalid.test'

    def command(self, operation="deliver", consumer="app", native=False, extra=()):
        self.document.write_text(json.dumps(self.runtime))
        args = ([sys.executable, "-B", str(CLI)] if native else
                [sys.executable, "-B", "-c", HARNESS, str(ROOT / "host")])
        args += [operation, "--runtime", str(self.document), "--project-id", self.runtime["project_id"],
                 "--project-number", "123456789012"]
        if operation != "cleanup":
            args += ["--gcloud", str(self.gcloud)]
        if operation == "deliver":
            args += ["--identity-mode", "dedicated-operator"]
        if operation == "transfer-provider":
            args += ["--key-file", str(self.key), "--receipt-root", str(self.receipts),
                     "--approve-resource", "projects/123456789012/secrets/hyprn-staging-assistant-provider"]
        else:
            args += ["--root", str(self.private), "--consumer", consumer]
        return subprocess.run(args + list(extra), env=self.env, capture_output=True, timeout=15)

    def success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertNotIn(b"synthetic-provider-secret", result.stdout)
        return json.loads(result.stdout)

    def rejected(self, result, code=None):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertNotIn(b"synthetic-provider-secret", result.stderr)
        if code:
            self.assertEqual(json.loads(result.stderr)["error"], code)

    def calls(self):
        path = self.root / "calls"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_deliver_is_exact_binary_private_and_component_scoped(self):
        self.success(self.command())
        expected = {"modeling-auth", "assistant-provider", "db-app-request", "db-app-auth", "db-assistant-background"}
        self.assertEqual(set(p.name for p in (self.private / "app").iterdir()), expected)
        for path in (self.private / "app").iterdir():
            self.assertEqual(path.read_bytes(), SYNTHETIC)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_uid, os.geteuid())
        self.assertEqual((self.private / "app").stat().st_mode & 0o777, 0o700)
        self.success(self.command(consumer="dispatcher"))
        self.assertEqual(set(p.name for p in (self.private / "dispatcher").iterdir()),
                         {"modeling-auth", "db-app-request", "db-dispatcher-background"})
        for args in self.calls():
            self.assertNotIn("synthetic-provider-secret", " ".join(args))
            self.assertFalse(any(a in ("latest", "--log-http") for a in args))
        self.success(self.command("cleanup"))
        self.assertFalse((self.private / "app").exists())
        self.assertTrue((self.private / "dispatcher").exists())

    def test_operation_consumers_get_only_their_own_credential(self):
        for consumer, alias in (("migration", "db-app-migration"), ("backup", "db-app-backup")):
            self.success(self.command(consumer=consumer))
            self.assertEqual([p.name for p in (self.private / consumer).iterdir()], [alias])
            self.success(self.command("cleanup", consumer))

    def test_numeric_rotation_requires_cleanup_and_fetches_exact_pin(self):
        self.success(self.command())
        self.runtime["secrets"]["assistant-provider"]["version"] = 42
        self.rejected(self.command(), "consumer_exists_cleanup_required")
        self.success(self.command("cleanup"))
        self.success(self.command())
        matching = [a for a in self.calls() if "--secret=hyprn-staging-assistant-provider" in a]
        self.assertEqual(matching[-1][matching[-1].index("access") + 1], "42")

    def test_invalid_binding_rejected_before_google(self):
        for value in ("latest", True, 0):
            self.runtime["secrets"]["assistant-provider"]["version"] = value
            self.rejected(self.command())
        self.runtime["secrets"]["assistant-provider"]["version"] = 1
        self.runtime["secrets"]["assistant-provider"]["name"] = "hyprn-prod-assistant-provider"
        self.rejected(self.command(), "secret_binding")
        self.assertEqual(self.calls(), [])

    def test_project_mismatch_and_unknown_consumer_do_not_fetch(self):
        self.mode.write_text("project")
        self.rejected(self.command(), "project_mismatch")
        self.assertFalse(any("access" in a for a in self.calls()))
        self.rejected(self.command(consumer="worker"))

    def test_fetch_failure_removes_partial_directory_and_redacts_stderr(self):
        self.mode.write_text("fetch-fail")
        self.rejected(self.command(), "google_operation_failed")
        self.assertEqual(list(self.private.iterdir()), [])
        self.mode.write_text("bad-base64")
        self.rejected(self.command(), "secret_payload")
        self.assertEqual(list(self.private.iterdir()), [])

    def test_symlink_or_unexpected_root_fails_without_touching_target(self):
        outside = self.root / "outside"
        outside.mkdir(mode=0o700)
        (self.private / "app").symlink_to(outside)
        self.rejected(self.command("cleanup"))
        self.assertTrue(outside.is_dir())
        (self.private / "app").unlink()
        (self.private / "unexpected").write_text("preserve")
        self.rejected(self.command(), "unexpected_root_entry")
        self.assertEqual((self.private / "unexpected").read_text(), "preserve")

    def test_cleanup_validates_entire_inventory_before_deletion(self):
        self.success(self.command())
        (self.private / "app/extra").write_text("preserve")
        self.rejected(self.command("cleanup"), "unexpected_secret_file")
        self.assertEqual(len(list((self.private / "app").iterdir())), 6)
        (self.private / "app/extra").unlink()
        path = self.private / "app/assistant-provider"
        path.unlink()
        path.symlink_to(self.key)
        self.rejected(self.command("cleanup"), "unsafe_secret_file")
        self.assertEqual(self.key.read_bytes(), SYNTHETIC)

    def test_root_permissions_and_symlink_ancestor_are_rejected(self):
        self.private.chmod(0o755)
        self.rejected(self.command(), "private_mode")
        self.private.chmod(0o700)
        link = self.root / "linked"
        link.symlink_to(self.private)
        self.rejected(self.command(extra=("--root", str(link))))
        self.assertEqual(self.calls(), [])

    def test_unmodified_cli_refuses_unqualified_host(self):
        self.rejected(self.command(native=True))
        self.assertEqual(self.calls(), [])

    def test_transfer_uses_stdin_and_receipt_prevents_duplicate(self):
        result = self.success(self.command("transfer-provider", native=True))
        self.assertTrue(result["version"].endswith("/versions/7"))
        receipt = self.receipts / "assistant-provider-transfer.json"
        self.assertEqual(json.loads(receipt.read_text()), result)
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.key.read_bytes(), SYNTHETIC)
        self.rejected(self.command("transfer-provider", native=True), "transfer_already_attempted_reconcile_receipt")
        self.assertEqual(sum("add" in c for c in self.calls()), 1)

    def test_uncertain_transfer_is_never_automatically_retried(self):
        self.mode.write_text("uncertain")
        self.rejected(self.command("transfer-provider", native=True), "transfer_uncertain_reconcile_receipt")
        self.rejected(self.command("transfer-provider", native=True), "transfer_already_attempted_reconcile_receipt")
        self.assertEqual(sum("add" in c for c in self.calls()), 1)
        receipt = (self.receipts / "assistant-provider-transfer.json").read_bytes()
        self.assertNotIn(SYNTHETIC, receipt)
        self.assertIn(b"attempted-reconcile-before-retry", receipt)

    def test_transfer_preflight_and_file_modes_fail_before_write(self):
        self.mode.write_text("identity")
        self.rejected(self.command("transfer-provider", native=True), "secret_identity")
        self.mode.write_text("ok")
        self.key.chmod(0o644)
        self.rejected(self.command("transfer-provider", native=True), "private_key_file")
        self.assertFalse(any("add" in c for c in self.calls()))
        self.assertEqual(list(self.receipts.iterdir()), [])

    def test_concurrent_delivery_is_refused_before_any_fetch(self):
        fd = os.open(self.private, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            self.rejected(self.command(), "secret_operation_failed")
            self.assertEqual(self.calls(), [])
        finally:
            os.close(fd)

    def test_transfer_approval_and_key_links_fail_before_version_creation(self):
        self.rejected(self.command("transfer-provider", native=True,
                                  extra=("--approve-resource", "projects/123456789012/secrets/wrong")),
                      "explicit_transfer_approval_required")
        self.assertEqual(self.calls(), [])
        source = self.root / "source"
        self.key.rename(source)
        self.key.symlink_to(source)
        self.rejected(self.command("transfer-provider", native=True))
        self.assertFalse(any("add" in c for c in self.calls()))
        self.assertEqual(source.read_bytes(), SYNTHETIC)

    def test_missing_dedicated_identity_and_runtime_project_mismatch_fail_closed(self):
        self.env.pop("CLOUDSDK_CONFIG")
        self.rejected(self.command(), "dedicated_identity_required")
        self.runtime["project_number"] = "999999999999"
        self.rejected(self.command(), "project_mismatch")
        self.assertEqual(self.calls(), [])

    def test_attached_service_account_requires_exact_principal_without_adc(self):
        self.env.pop('GOOGLE_APPLICATION_CREDENTIALS')
        self.env.pop('CLOUDSDK_CONFIG')
        args = ('--identity-mode', 'attached-service-account')
        self.mode.write_text('principal')
        self.rejected(self.command(extra=args), 'attached_identity_mismatch')
        calls = (self.root / 'metadata-calls').read_text()
        self.assertNotIn('/token', calls)
        self.mode.write_text('ok')
        self.success(self.command(extra=args))
        self.assertEqual((self.private / 'app/assistant-provider').read_bytes(), b'123456789')
        self.assertEqual(self.calls(), [])
        self.success(self.command('cleanup'))
        self.mode.write_text('crc')
        self.rejected(self.command(extra=args), 'secret_payload')
        self.assertEqual(list(self.private.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
