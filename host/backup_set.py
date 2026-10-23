"""Coherent stopped-owner backup using the managed SQL and product file adapters.

The privileged host launches this fixed bridge in the active release's native
interpreter. An inherited deployment fence, product lock and native/AiiDA locks
span the entire operation. Interruption permanently disqualifies this set; its
SQL intent can still be reconciled separately with cloudsql_backup.py resume.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import socket
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import UUID

# Avoid the host's secrets.py shadowing the standard-library secrets module in
# AiiDA dependencies. These are fixed trusted siblings, never release inputs.
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


HOST = Path(__file__).resolve().parent
contract = load_module('contract', HOST / 'contract.py')
old_secrets = sys.modules.get('secrets')
try:
    load_module('secrets', HOST / 'secrets.py')
    sql = load_module('hyprn_cloudsql_backup', HOST / 'cloudsql_backup.py')
finally:
    if old_secrets is None:
        sys.modules.pop('secrets', None)
    else:
        sys.modules['secrets'] = old_secrets
Invalid = contract.Invalid
SCHEMA = 'hyprn-coherent-backup/v1'


def digest(value):
    return hashlib.sha256(sql.canonical(value)).hexdigest()


def secure_path(path, *, directory=False, owner=None, mode=None):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Invalid('backup_path')
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise Invalid('backup_path')
        if item != path and (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.geteuid())
                             or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
            raise Invalid('backup_parent_authority')
    info = path.lstat()
    if ((not stat.S_ISDIR(info.st_mode) if directory else
         not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)
            or info.st_mode & 0o022
            or owner is not None and info.st_uid != owner
            or mode is not None and stat.S_IMODE(info.st_mode) != mode):
        raise Invalid('backup_file_authority')
    return path


class DeploymentFence:
    """Verify the inherited locked inode; never reacquire a lost lock."""
    def __init__(self, fd, path, parent=None):
        self.fd, self.path, self.parent = fd, Path(path), parent
        info = os.fstat(fd)
        self.identity = (info.st_dev, info.st_ino)
        self.check()

    def check(self):
        path = secure_path(self.path, owner=os.geteuid(), mode=0o600)
        info, descriptor = path.stat(), os.fstat(self.fd)
        if ((info.st_dev, info.st_ino) != self.identity or
                (descriptor.st_dev, descriptor.st_ino) != self.identity):
            raise Invalid('deployment_hold_lost')
        contender = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if self.parent is not None:
                    self.parent.sendall(b'check\n')
                    if self.parent.recv(3) != b'ok\n':
                        raise Invalid('deployment_parent_hold_lost')
                return
            raise Invalid('deployment_hold_lost')
        finally:
            os.close(contender)


def private_document(path):
    path = secure_path(path, owner=os.geteuid(), mode=0o600)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return sql.read_private(directory, path.name)
    finally:
        os.close(directory)


def receipt(lifecycle, operation, operation_id):
    if str(UUID(operation_id)) != operation_id:
        raise Invalid('backup_operation_identity')
    path = lifecycle.root / ('operation-' + operation_id + '.json')
    value = private_document(path)
    expected = digest(dict(identity=lifecycle.identity, binding=lifecycle.binding,
                           operation=operation, surface=None, state=None))
    result = value.get('result', {})
    if (set(value) != {'identity_sha256', 'state', 'result', 'exit_code'} or
            value['identity_sha256'] != expected or value['state'] != 'complete' or
            type(value['exit_code']) is not int or value['exit_code'] != 0 or
            result.get('operation') != operation or result.get('operation_id') != operation_id or
            result.get('installation_id') != lifecycle.identity['installation_id'] or
            result.get('status') != 'success' or result.get('reason_code') != 'completed' or
            result.get('evidence_refs') != [path.name]):
        raise Invalid('backup_stopped_receipt')
    return value


def schema_receipt(lifecycle, *, drain_operation_id=None, inspect_operation_id=None):
    """A stopped-owner snapshot needs observed schemas, not completed work.

    Legacy successful drain receipts remain valid. An explicit inspect receipt
    records only schema observation; it never claims uncertain work reconciled.
    The caller must still hold the deployment fence and prove writers stopped.
    """
    if bool(drain_operation_id) == bool(inspect_operation_id):
        raise Invalid('backup_schema_receipt_selection')
    operation = 'inspect' if inspect_operation_id else 'drain'
    identifier = inspect_operation_id or drain_operation_id
    value = receipt(lifecycle, operation, identifier)
    schemas = value['result'].get('observed_schema_versions')
    if not isinstance(schemas, dict) or not schemas:
        raise Invalid('backup_schema_observation_missing')
    return operation, value, schemas


def verify_output_authority(root):
    secure_path(root, directory=True, owner=os.geteuid(), mode=0o700)
    for path in root.rglob('*'):
        directory = path.is_dir()
        secure_path(path, directory=directory, owner=os.geteuid(), mode=0o700 if directory else 0o600)


def assemble(*, files, args, roots, identity, owner, schemas, source, fence, assert_stopped,
             receipts, timeout, expected_endpoint):
    """Existing adapters run under one real hold; only HTTP is doubled in tests."""
    if type(timeout) not in (int, float) or not 0 < timeout <= 3600:
        raise Invalid('backup_timeout')
    binding = sql.bindings(args)
    if (binding['installation_id'] != identity['installation_id'] or
            binding['release_digest'] != 'sha256:' + identity['release_sha256'] or
            binding['configuration_digest'] != 'sha256:' + identity['config_sha256']):
        raise Invalid('backup_identity')
    if (not callable(assert_stopped) or not isinstance(schemas, dict) or not schemas
            or not isinstance(expected_endpoint, dict)):
        raise Invalid('backup_stopped_evidence_required')
    directory = sql.private_directory(args.state_root)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if os.listdir(directory):
            raise Invalid('backup_set_requires_new_scope')
        fence.check()
        assert_stopped()
        intent = dict(schema=SCHEMA, binding=binding, identity=identity, native_owner=owner,
                      observed_schema_versions=schemas, source=source,
                      receipts={key: digest(value) for key, value in receipts.items()})
        sql.save(directory, 'intent.json', intent)
        try:
            with files.native_hold(roots['execution'], owner['profile'], timeout=timeout) as hold:
                def current():
                    fence.check()
                    hold.check()
                    assert_stopped()
                current()
                database = Path(args.state_root) / 'database'
                database.mkdir(mode=0o700)
                provider_args = SimpleNamespace(**vars(args))  # retain exact reviewed bindings
                provider_args.state_root = str(database)
                provider_args.command = 'create'
                try:
                    managed = sql.backup(provider_args, expected_endpoint=expected_endpoint)
                except Invalid as error:
                    # Only GET reconciliation while the original hold is live.
                    if error.code not in ('backup_dispatch_uncertain', 'backup_pending',
                                          'backup_not_found_reconcile', 'cloudsql_request_failed'):
                        raise
                    current()
                    provider_args.command = 'resume'
                    managed = sql.backup(provider_args, expected_endpoint=expected_endpoint)
                current()
                persisted = private_document(database / 'receipt.json')
                if (persisted != managed or managed.get('binding') != binding or
                        managed.get('status') != 'complete' or managed.get('provider_status') != 'SUCCESSFUL' or
                        managed.get('scope') != 'cloudsql-database-only' or
                        managed.get('coherent_installation_backup') is not False):
                    raise Invalid('backup_database_receipt')
                destination = Path(args.state_root) / 'owner-files'
                snapshot = files.snapshot_files(hold, destination, roots=roots, identity=identity, owner=owner)
                current()
                checked = files.verified_manifest(destination, identity=identity, owner=owner,
                                                  roots=roots, deadline=hold.deadline)
                if checked != snapshot:
                    raise Invalid('backup_owner_manifest_changed')
                verify_output_authority(Path(args.state_root))
                current()
                complete = dict(intent, status='complete', coherent_installation_backup=True,
                    continuous_hold=dict(deployment_device=fence.identity[0], deployment_inode=fence.identity[1],
                                         native_executor=True, aiida_profile=True),
                    managed_database=dict(resource=managed['resource'], metadata=managed,
                                          metadata_sha256=digest(managed)),
                    owner_files=dict(manifest='owner-files/manifest.json', manifest_sha256=digest(snapshot)),
                    native_schema=snapshot['native_schema'])
                # No raw SQL bytes or secrets are copied; this is the sole complete marker.
                sql.save(directory, 'manifest.json', complete)
                return complete
        except BaseException:
            sql.save(directory, 'failed.json', dict(schema=SCHEMA, status='incomplete',
                     coherent_installation_backup=False, reason='continuous_backup_not_completed'))
            raise
    finally:
        os.close(directory)


def trusted_product(binding_path):
    """Consume the immutable source/native tree installed by trusted bootstrap.

    Bootstrap must already have verified/extracted the reviewed payload bytes;
    ownership and this operation's recorded hashes do not replace that proof.
    """
    specification = private_document(binding_path)
    required = {'schema', 'platform_root', 'workload', 'release', 'runtime', 'desired',
                'payload_inventory', 'control_root'}
    if set(specification) != required or specification['schema'] != 'hyprn-product-binding/v1':
        raise Invalid('backup_product_binding')
    for key in required - {'schema'}:
        secure_path(specification[key], directory=key in ('platform_root', 'control_root'), owner=0)
    if Path(specification['platform_root']) != HOST.parent:
        raise Invalid('backup_platform_source')
    documents = {key: contract.read_json(specification[key]) for key in ('release', 'runtime', 'desired', 'workload')}
    contract.check_documents(documents)
    preview = contract.render(documents['release'], documents['runtime'])
    contract.check_desired(documents['desired'], documents['release'], documents['runtime'], contract.digest(preview))
    configuration = preview['execution']['configuration']
    if Path(sys.executable).absolute() != Path(configuration['python']):
        raise Invalid('backup_native_interpreter_required')
    source = secure_path(configuration['source'], directory=True, owner=0)
    hashes = {}
    for name in ('cloud_release', 'cloud_lifecycle', 'cloud_backup'):
        path = secure_path(source / 'deployment' / (name + '.py'), owner=0)
        if path.stat().st_mode & 0o022:
            raise Invalid('backup_product_source_authority')
        hashes[name + '.py'] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Each path is a fixed module under the immutable released source prefix.
    release = load_module('cloud_release', source / 'deployment/cloud_release.py')
    lifecycle_module = load_module('cloud_lifecycle', source / 'deployment/cloud_lifecycle.py')
    files = load_module('hyprn_owner_files', source / 'deployment/cloud_backup.py')
    lifecycle = lifecycle_module.Lifecycle(specification, 3600)
    lifecycle.artifact_check()
    lifecycle.native_projection()
    return lifecycle, lifecycle_module, files, dict(source_commit=documents['release']['source_commit'],
                                                    modules=hashes, native_python=configuration['python'])


def stopped_owners(lifecycle):
    """Keep old product receipts usable while checking detached workers too."""
    lifecycle.assert_stopped()
    owner = 'hyprn-mvp-cloud-' + lifecycle.runtime['installation_id']
    result = subprocess.run(
        ['docker', 'ps', '--quiet', '--no-trunc', '--filter', 'label=org.hyprn-mvp.owner=' + owner],
        capture_output=True, text=True, timeout=lifecycle.remaining(),
        env={key: value for key, value in os.environ.items() if key in ('PATH', 'LANG', 'LC_ALL')})
    if result.returncode or result.stdout.strip():
        raise Invalid('backup_native_workers_not_stopped')


def run_child(args):
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise Invalid('backup_linux_root_required')
    lifecycle, module, files, source = trusted_product(args.binding)
    lifecycle.deadline = time.monotonic() + args.timeout
    parent = socket.socket(fileno=args.fence_channel)
    parent.settimeout(min(args.timeout, 30))
    fence = DeploymentFence(args.deployment_fd, args.deployment_path, parent)
    with module.exclusive(lifecycle.root):
        stop = receipt(lifecycle, 'stop', args.stop_operation_id)
        schema_operation, schema_observation, schemas = schema_receipt(
            lifecycle, drain_operation_id=args.drain_operation_id,
            inspect_operation_id=args.inspect_operation_id)
        if not hasattr(lifecycle, 'assert_stopped'):
            raise Invalid('backup_stopped_inspection_unavailable')
        stopped_owners(lifecycle)
        owner = private_document(lifecycle.root / 'native-owner.json')
        identity = dict(lifecycle.identity, store_ids=lifecycle.runtime['store_ids'])
        configuration = lifecycle.native_projection()
        if any(owner.get(key) != configuration[key] for key in
               ('installation_id', 'store_id', 'execution_root', 'profile', 'release_sha256', 'config_sha256')):
            raise Invalid('backup_native_owner_mismatch')
        runtime = lifecycle.runtime
        database = runtime['database']
        policy = private_document(args.backup_policy)
        fields = {'schema', 'installation_id', 'project_id', 'project_number', 'release_sha256',
                  'config_sha256', 'instance', 'private_network'}
        if (set(policy) != fields or policy['schema'] != 'hyprn-backup-policy/v1'
                or any(policy[key] != runtime[key] for key in ('installation_id', 'project_id', 'project_number'))
                or any(policy[key] != identity[key] for key in ('release_sha256', 'config_sha256'))):
            raise Invalid('backup_policy_binding')
        provider = SimpleNamespace(command='create', state_root=args.state_root, approve_resource=args.approve_resource,
            project_id=runtime['project_id'], project_number=runtime['project_number'],
            instance=policy['instance'], private_network=policy['private_network'],
            installation_id=identity['installation_id'], release_digest='sha256:' + identity['release_sha256'],
            configuration_digest='sha256:' + identity['config_sha256'], operation_id=args.operation_id,
            poll_attempts=5, poll_seconds=5)
        roots = {key: Path(runtime['mounts'][key]) for key in ('execution', 'modeling')}
        roots['artifacts'] = Path(runtime['mounts']['application']) / 'artifacts'
        return assemble(files=files, args=provider, roots=roots, identity=identity, owner=owner, schemas=schemas,
                        source=source, fence=fence,
                        assert_stopped=lambda: stopped_owners(lifecycle),
                        receipts={'stop': stop, schema_operation: schema_observation},
                        timeout=args.timeout,
                        expected_endpoint={key: database[key] for key in ('host', 'server_name')})


def create(active_binding_path, *, deployment_fd, deployment_path, operation_id, state_root,
           stop_operation_id, approve_resource, backup_policy, recheck_fence, timeout=300,
           drain_operation_id=None, inspect_operation_id=None):
    """Trusted reconciler seam. No scope approval or runtime path is invented."""
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise Invalid('backup_linux_root_required')
    if bool(drain_operation_id) == bool(inspect_operation_id):
        raise Invalid('backup_schema_receipt_selection')
    specification = private_document(active_binding_path)
    documents = {key: contract.read_json(specification[key]) for key in ('release', 'runtime', 'desired', 'workload')}
    contract.check_documents(documents)
    preview = contract.render(documents['release'], documents['runtime'])
    contract.check_desired(documents['desired'], documents['release'], documents['runtime'], contract.digest(preview))
    fence = DeploymentFence(deployment_fd, deployment_path)
    recheck_fence()
    executable = preview['execution']['configuration']['python']
    command = [executable, '-I', '-B', str(HOST / 'backup_set.py'), '--binding', str(active_binding_path),
               '--deployment-fd', str(deployment_fd), '--deployment-path', str(deployment_path),
               '--operation-id', operation_id, '--state-root', str(state_root),
               '--stop-operation-id', stop_operation_id,
               '--approve-resource', approve_resource, '--backup-policy', str(backup_policy), '--timeout', str(timeout)]
    command.extend(['--inspect-operation-id', inspect_operation_id] if inspect_operation_id else
                   ['--drain-operation-id', drain_operation_id])
    parent, child = socket.socketpair()
    command.extend(['--fence-channel', str(child.fileno())])
    deadline = time.monotonic() + timeout + 5
    process = None
    try:
        process = subprocess.Popen(command, pass_fds=(deployment_fd, child.fileno()),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL') if key in os.environ})
        child.close()
        parent.settimeout(0.2)
        while process.poll() is None:
            if time.monotonic() >= deadline:
                raise Invalid('backup_timeout')
            try:
                request = parent.recv(6)
            except socket.timeout:
                continue
            if not request:
                break
            if request != b'check\n':
                raise Invalid('backup_fence_protocol')
            fence.check()
            recheck_fence()
            parent.sendall(b'ok\n')
        stdout, _stderr = process.communicate(timeout=max(0.001, deadline - time.monotonic()))
        fence.check()
        recheck_fence()
        if process.returncode:
            raise Invalid('backup_set_incomplete')
    finally:
        parent.close()
        child.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
    manifest = private_document(Path(state_root) / 'manifest.json')
    if json.loads(stdout) != manifest:
        raise Invalid('backup_set_receipt_mismatch')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binding', 'deployment-path', 'operation-id', 'state-root', 'stop-operation-id',
                 'approve-resource', 'backup-policy'):
        parser.add_argument('--' + name, required=True)
    schema_source = parser.add_mutually_exclusive_group(required=True)
    schema_source.add_argument('--drain-operation-id')
    schema_source.add_argument('--inspect-operation-id')
    parser.add_argument('--deployment-fd', required=True, type=int)
    parser.add_argument('--fence-channel', required=True, type=int)
    parser.add_argument('--timeout', type=int, default=300)
    try:
        args = parser.parse_args(argv)
        os.umask(0o077)
        result = run_child(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Invalid as error:
        print(json.dumps({'error': error.code}), file=sys.stderr)
    except Exception:
        print(json.dumps({'error': 'backup_set_incomplete'}), file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
