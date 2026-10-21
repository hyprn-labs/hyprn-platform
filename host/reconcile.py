"""Trusted-host reconciliation primitives; no authority is accepted from a receipt.

Call reconcile() from reviewed bootstrap code with GoogleHost and Product adapters.
This module does not install itself, fetch executable code, grant cloud authority,
open admission or claim a completed deployment. Whole-host qualification remains
an explicit prerequisite. Journal state belongs on the installation disk, never
on /run. The Python interfaces are host-only, not product or agent APIs.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import selectors
import time
import signal
import stat
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import quote
from uuid import uuid4

import contract
# The standard library's secrets module may already be loaded by bootstrap or
# native dependencies. Load this fixed trusted sibling under its own name.
_secret_spec = importlib.util.spec_from_file_location(
    'hyprn_reconcile_secret_loader', Path(__file__).with_name('secrets.py'))
_secret_loader = importlib.util.module_from_spec(_secret_spec)
_secret_spec.loader.exec_module(_secret_loader)
AttachedServiceAccount = _secret_loader.AttachedServiceAccount
request_google = _secret_loader.request_google

MAX_OUTPUT = 2 * 1024 * 1024
RESULT_FIELDS = {'operation_id', 'operation', 'installation_id', 'status',
                 'reason_code', 'observed_schema_versions', 'evidence_refs'}
OPERATIONS = {'initialize', 'inspect', 'check', 'admission', 'drain', 'migrate',
              'start', 'stop', 'qualify'}


class Refused(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def decode(raw):
    if len(raw) > MAX_OUTPUT:
        raise Refused('document_size')
    try:
        return json.loads(raw, object_pairs_hook=contract.pairs,
                          parse_constant=contract.reject_constant)
    except (ValueError, UnicodeError, contract.Invalid):
        raise Refused('invalid_json') from None


def digest_file(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def protected(path, *, directory=False):
    """Only bootstrap-owned paths can confer authority on the privileged host."""
    path = Path(path)
    if not path.is_absolute():
        raise Refused('host_path_authority')
    for parent in (path, *path.parents):
        info = parent.lstat()
        if (stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022):
            raise Refused('host_path_authority')
    mode = path.stat().st_mode
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        raise Refused('host_path_authority')
    return path


def atomic(path, value, *, mode=0o600):
    """Persist both file bytes and rename before any dependent external effect."""
    path = Path(path)
    temporary = path.parent / ('.' + path.name + '-' + str(uuid4()))
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contract.canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


class Journal:
    """One deployment/backup lock and monotonic journal, retained across reboot."""
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / 'reconcile.json'
        self.lock_path = self.root / 'deployment.lock'
        self.fd = None

    @contextmanager
    def lock(self):
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        info = os.fstat(fd)
        try:
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                    or info.st_uid != os.geteuid() or info.st_mode & 0o077):
                raise Refused('deployment_lock_authority')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refused('deployment_conflict') from None
            self.fd = fd
            yield self
        finally:
            self.fd = None
            os.close(fd)

    def read(self):
        if self.fd is None:
            raise Refused('deployment_lock_required')
        if not self.path.exists():
            return None
        info = self.path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.geteuid() or info.st_mode & 0o077):
            raise Refused('journal_authority')
        value = contract.read_json(self.path)
        fields = {'schema', 'sequence', 'desired_sha256', 'stage', 'mutation',
                  'operations', 'migration', 'failure', 'backup', 'installed', 'fence', 'desired_generation'}
        if (not isinstance(value, dict) or set(value) != fields
                or value['schema'] != 'hyprn-reconcile/v1'
                or type(value['sequence']) is not int or not 1 <= value['sequence'] <= 2147483647
                or not isinstance(value['desired_sha256'], str)
                or not re.fullmatch('[a-f0-9]{64}', value['desired_sha256'])
                or type(value['mutation']) is not bool
                or value['stage'] not in {'verified', 'prestaged', 'draining', 'quiesced',
                    'backed_up', 'migrating', 'qualifying', 'starting', 'installed_closed'}
                or not isinstance(value['operations'], dict)):
            raise Refused('journal_corrupt')
        return value

    def write(self, value):
        if self.fd is None:
            raise Refused('deployment_lock_required')
        atomic(self.path, value)

    def accept(self, sequence, desired_sha256):
        previous = self.read()
        if type(sequence) is not int or not 1 <= sequence <= 2147483647:
            raise Refused('invalid_sequence')
        if not isinstance(desired_sha256, str) or not re.fullmatch('[a-f0-9]{64}', desired_sha256):
            raise Refused('invalid_desired_digest')
        if previous:
            if sequence < previous['sequence']:
                raise Refused('stale_sequence')
            if sequence == previous['sequence']:
                if desired_sha256 != previous['desired_sha256']:
                    raise Refused('sequence_conflict')
                if previous['stage'] == 'installed_closed':
                    return previous
                # No mutation, drain or prior command is silently repeated. Even
                # pre-mutation retries require an explicit new desired sequence.
                raise Refused('operator_recovery_required')
            if previous['stage'] != 'installed_closed' and (
                    previous['mutation'] or previous['operations']):
                raise Refused('operator_recovery_required')
        value = dict(schema='hyprn-reconcile/v1', sequence=sequence,
                     desired_sha256=desired_sha256, stage='verified', mutation=False,
                     operations={}, migration=None, failure=None, backup=None,
                     installed=previous['installed'] if previous else None,
                     fence=previous['fence'] if previous else None, desired_generation=None)
        self.write(value)
        return value


class Target:
    """Closed descriptor validation; no executable import or owner effect."""
    def __init__(self, binding_path):
        self.path = Path(binding_path)
        self.binding = contract.read_json(self.path)
        required = {'schema', 'platform_root', 'workload', 'release', 'runtime', 'desired',
                    'payload_inventory', 'control_root'}
        if (set(self.binding) != required or self.binding['schema'] != 'hyprn-product-binding/v1'):
            raise Refused('invalid_binding')
        if Path(self.binding['platform_root']).resolve() != Path(__file__).resolve().parents[1]:
            raise Refused('platform_root_mismatch')
        self.documents = {key: contract.read_json(self.binding[key]) for key in
                          ('workload', 'release', 'runtime', 'desired')}
        contract.check_documents(self.documents)
        self.release, self.runtime, self.desired = (self.documents[key] for key in
                                                   ('release', 'runtime', 'desired'))
        self.preview = contract.render(self.release, self.runtime)
        contract.check_desired(self.desired, self.release, self.runtime, contract.digest(self.preview))
        self.identity = dict(installation_id=self.runtime['installation_id'],
                             release_sha256=contract.digest(self.release),
                             config_sha256=contract.digest(self.preview))
        self.binding_sha256 = contract.digest(self.binding)

    def unchanged(self):
        current = Target(self.path)
        if (current.documents != self.documents or current.binding != self.binding):
            raise Refused('staged_documents_changed')

    def protect(self):
        protected(self.path)
        for key in ('workload', 'release', 'runtime', 'desired', 'payload_inventory'):
            protected(self.binding[key])
        control = next(volume['source'] for volume in self.preview['compose']['services']['app']['volumes']
                       if volume['target'] == '/run/hyprn-control')
        if self.binding['control_root'] != control:
            raise Refused('host_control_mount_mismatch')
        protected(control, directory=True)
        self.unchanged()


def disk_attachment(runtime, *, disk_name, device_name, instance, disk):
    """Check live Compute observations; the returned device still needs kernel proof.

    The supported zonal pd-balanced type cannot be multi-writer. Its API response
    may omit accessMode, unlike Hyperdisk. Never extend that inference to another
    disk type, a foreign type URL, or explicit conflicting mode/multiWriter data.
    """
    for name in (disk_name, device_name):
        if not isinstance(name, str) or not re.fullmatch('[a-z][a-z0-9-]{0,61}[a-z0-9]', name):
            raise Refused('host_policy_invalid')
    base = ('https://www.googleapis.com/compute/v1/projects/' + runtime['project_id']
            + '/zones/' + runtime['zone'])
    instance_link = base + '/instances/' + runtime['host_id']
    disk_link = base + '/disks/' + disk_name
    if (not isinstance(instance, dict) or not isinstance(disk, dict)
            or instance.get('selfLink') != instance_link or instance.get('status') != 'RUNNING'
            or disk.get('selfLink') != disk_link or disk.get('users') != [instance_link]
            or disk.get('type') != base + '/diskTypes/pd-balanced'
            or ('accessMode' in disk and disk['accessMode'] != 'READ_WRITE_SINGLE')
            or disk.get('multiWriter', False) is not False or disk.get('status') != 'READY'):
        raise Refused('exclusive_disk_ownership_unproven')
    observed = instance.get('disks')
    if not isinstance(observed, list) or any(not isinstance(item, dict) for item in observed):
        raise Refused('disk_attachment_mismatch')
    attachments = [item for item in observed if item.get('source') == disk_link]
    if (len(attachments) != 1 or attachments[0].get('mode') != 'READ_WRITE'
            or attachments[0].get('type') != 'PERSISTENT'
            or attachments[0].get('boot') is not False
            or attachments[0].get('deviceName') != device_name):
        raise Refused('disk_attachment_mismatch')
    return Path('/dev/disk/by-id/google-' + device_name)


class GoogleHost:
    """Read live metadata, Compute ownership, kernel mounts and GCS generation.

Disk resource, attachment device and retired instance names come from bootstrap policy,
never from product receipts. IAM authorizes only reads here. Runtime must have
compute.instances.get / compute.disks.get to establish exclusive ownership.
"""
    def __init__(self, target, *, disk_name, device_name, retired_hosts=()):
        self.target = target
        self.runtime = target.runtime
        self.disk_name = disk_name
        self.device_name = device_name
        self.retired_hosts = tuple(retired_hosts)
        for name in (disk_name, device_name, *self.retired_hosts):
            if not isinstance(name, str) or not re.fullmatch('[a-z][a-z0-9-]{0,61}[a-z0-9]', name):
                raise Refused('host_policy_invalid')
        if self.runtime['host_id'] in self.retired_hosts:
            raise Refused('host_policy_invalid')
        self.principal = AttachedServiceAccount()

    def request(self, service, path, *, raw=False):
        if service not in ('compute.googleapis.com', 'storage.googleapis.com'):
            raise Refused('host_service_invalid')
        connection = http.client.HTTPSConnection(service, timeout=20)
        try:
            connection.request('GET', path, headers={
                'Authorization': 'Bearer ' + self.principal.token})
            response = connection.getresponse()
            body = response.read(MAX_OUTPUT + 1)
            if response.status != 200 or len(body) > MAX_OUTPUT:
                raise Refused('host_observation_unavailable')
            return body if raw else decode(body)
        except (OSError, http.client.HTTPException):
            raise Refused('host_observation_unavailable') from None
        finally:
            connection.close()

    def check(self):
        if sys.platform != 'linux' or os.geteuid() != 0:
            raise Refused('linux_root_required')
        runtime = self.runtime
        self.target.protect()
        self.principal.preflight(SimpleNamespace(**runtime))
        for key, value in (('instance/name', runtime['host_id']),
                           ('instance/zone', 'projects/' + runtime['project_number'] + '/zones/' + runtime['zone'])):
            if request_google(True, '/computeMetadata/v1/' + key).decode().strip() != value:
                raise Refused('host_identity_mismatch')
        base = '/compute/v1/projects/' + runtime['project_id'] + '/zones/' + runtime['zone']
        instance = self.request('compute.googleapis.com', base + '/instances/' + runtime['host_id'])
        disk = self.request('compute.googleapis.com', base + '/disks/' + self.disk_name)
        device = disk_attachment(runtime, disk_name=self.disk_name, device_name=self.device_name,
                                 instance=instance, disk=disk)
        for previous in self.retired_hosts:
            item = self.request('compute.googleapis.com', base + '/instances/' + previous)
            if (item.get('selfLink') != 'https://www.googleapis.com' + base + '/instances/' + previous
                    or item.get('status') != 'TERMINATED'):
                raise Refused('previous_host_not_fenced')
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if not re.fullmatch('[0-9a-f-]{36}', boot):
            raise Refused('boot_identity_unavailable')
        device = device.resolve(strict=True)
        expected_device = os.stat(device).st_rdev
        if not stat.S_ISBLK(os.stat(device).st_mode):
            raise Refused('disk_device_unproven')
        for owner in ('application', 'modeling', 'execution'):
            mount = Path(runtime['mounts'][owner])
            if not mount.is_absolute() or any(path.is_symlink() for path in (mount, *mount.parents)):
                raise Refused('store_mount_invalid')
            result = bounded(['/usr/bin/findmnt', '--json', '--target', str(mount),
                              '--output', 'UUID,SOURCE,OPTIONS'], timeout=15)
            entries = decode(result)['filesystems']
            if len(entries) != 1:
                raise Refused('store_mount_invalid')
            entry = entries[0]
            source = Path(entry['source']).resolve(strict=True)
            if (entry.get('uuid') != runtime['disk_uuid'] or 'rw' not in entry['options'].split(',')
                    or os.stat(source).st_rdev != expected_device or os.stat(mount).st_dev != expected_device):
                raise Refused('store_mount_identity_mismatch')
        instance_id = request_google(True, '/computeMetadata/v1/instance/id').decode().strip()
        if instance.get('id') != instance_id or not re.fullmatch('[1-9][0-9]{0,30}', instance_id):
            raise Refused('host_identity_mismatch')
        return dict(host_id=runtime['host_id'], instance_id=instance_id, boot_id=boot, disk_uuid=runtime['disk_uuid'])

    def desired(self):
        bucket = self.runtime['desired_bucket']
        base = '/storage/v1/b/' + quote(bucket, safe='') + '/o/current.json'
        metadata = self.request('storage.googleapis.com', base)
        generation = metadata.get('generation')
        if (metadata.get('bucket') != bucket or metadata.get('name') != 'current.json'
                or not isinstance(generation, str) or not re.fullmatch('[1-9][0-9]{0,30}', generation)):
            raise Refused('desired_generation_invalid')
        body = self.request('storage.googleapis.com', base + '?alt=media&generation=' + generation, raw=True)
        if decode(body) != self.target.desired:
            raise Refused('desired_generation_mismatch')
        return generation


def bounded(command, *, timeout):
    """No shell, ambient credentials or unbounded captured output."""
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, start_new_session=True,
                             env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C.UTF-8'})
    deadline, data = time.monotonic() + timeout, bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise Refused('operation_outcome_uncertain')
                block = os.read(child.stdout.fileno(), 65536)
                if not block:
                    break
                data.extend(block)
                if len(data) > MAX_OUTPUT:
                    raise Refused('operation_output_invalid')
        try:
            child.wait(timeout=max(0.01, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise Refused('operation_outcome_uncertain') from None
        if child.returncode:
            raise Refused('operation_refused')
        return bytes(data)
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        child.stdout.close()


class Product:
    """Fixed real product commands from bootstrap-approved, protected source.

The trusted bootstrap supplies SHA-256 for both scripts and the interpreter.
No descriptor field can supply an executable or command. Prepared release trees
and dependencies must be root-owned; provisioning/import remain separate steps.
"""
    def __init__(self, target, *, python, script_sha256, verifier_sha256, python_sha256):
        self.target = target
        self.python = str(python)
        source = Path(target.preview['execution']['configuration']['source'])
        self.script = source / 'deployment/cloud_lifecycle.py'
        self.verifier = source / 'deployment/cloud_release.py'
        self.pins = {self.script: script_sha256, self.verifier: verifier_sha256,
                     Path(self.python): python_sha256}

    def preflight(self):
        self.target.protect()
        for path, expected in self.pins.items():
            protected(path)
            if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected) or digest_file(path) != expected:
                raise Refused('product_code_pin')
        args = [self.python, '-B', str(self.verifier), '--platform-root', self.target.binding['platform_root']]
        for key in ('workload', 'release', 'runtime', 'desired'):
            args += ['--' + key, self.target.binding[key]]
        args += ['--payload', self.target.binding['payload_inventory']]
        result = decode(bounded(args, timeout=300))
        if (set(result) != {'verified', 'inventory_sha256'} or result['verified'] is not True
                or result['inventory_sha256'] != contract.digest(contract.read_json(self.target.binding['payload_inventory']))):
            raise Refused('product_payload_unverified')

    def compatibility(self, target):
        result = self.call('inspect', str(uuid4()))
        observed = result['observed_schema_versions']
        # The current product returns the application SQL migration ledger only.
        # It cannot be converted to all-owner compatibility by trusting a release
        # declaration, so the real second activation refuses until the owner
        # observation contract is extended and its adapter reviewed.
        if not isinstance(observed, dict) or set(observed) != set(target.release['stores']):
            raise Refused('owner_schema_observation_unavailable')
        raise Refused('owner_schema_mapping_unimplemented')

    def call(self, operation, operation_id, *, migration_binding=None):
        if operation not in OPERATIONS:
            raise Refused('unsupported_operation')
        self.target.unchanged()
        for path, expected in self.pins.items():
            protected(path)
            if digest_file(path) != expected:
                raise Refused('product_code_pin')
        binding = self.target.path
        if operation in ('initialize', 'migrate'):
            if migration_binding is None:
                raise Refused('migration_credential_scope_required')
            protected(migration_binding)
            supplied = contract.read_json(migration_binding)
            expected = dict(self.target.binding, migration_secret_file='/run/hyprn/secrets/migration/db-app-migration')
            if supplied != expected:
                raise Refused('migration_binding_mismatch')
            binding = migration_binding
        args = [self.python, '-B', str(self.script), operation, '--binding', str(binding),
                '--operation-id', operation_id, '--timeout', '300']
        if operation == 'admission':
            args += ['--surface', 'browser', '--state', 'closed']
        result = decode(bounded(args, timeout=310))
        if (not isinstance(result, dict) or set(result) != RESULT_FIELDS
                or result['operation_id'] != operation_id or result['operation'] != operation
                or result['installation_id'] != self.target.runtime['installation_id']
                or result['status'] not in ('success', 'noop')
                or result['reason_code'] != 'completed'
                or not isinstance(result['evidence_refs'], list)
                or len(result['evidence_refs']) > 64
                or any(not isinstance(item, str) or not re.fullmatch('operation-[0-9a-f-]{36}\\.json', item)
                       for item in result['evidence_refs'])):
            raise Refused('product_result_invalid')
        return result


def stable_installation(old, new):
    keys = ('installation_id', 'project_id', 'project_number', 'disk_uuid', 'store_ids', 'mounts')
    if any(old.runtime[key] != new.runtime[key] for key in keys):
        raise Refused('installation_identity_changed')
    # Until inspect reports all three live owner schemas, a changed migration
    # contract cannot establish compatibility merely from release declarations.
    if old.release['stores'] != new.release['stores']:
        raise Refused('owner_schema_compatibility_unproven')


@contextmanager
def failure_closes(target, host):
    try:
        yield
    except BaseException:
        # Closing access to an already bound local installation is safe even when
        # the data mount/cloud reads are unavailable. Never use foreign receipts
        # or write a data store to achieve this closure.
        if isinstance(host, GoogleHost):
            try:
                target.protect()
                control = Path(target.binding['control_root'])
                path = protected(control / 'runtime-identity.json')
                identity = contract.read_json(path)
                if (set(identity) == {'installation_id', 'release_sha256', 'config_sha256'}
                        and identity['installation_id'] == target.runtime['installation_id']):
                    atomic(control / 'admission.json', dict(schema='hyprn-admission/v1',
                           **identity, browser=False, scientific=False, expires_at=0), mode=0o644)
            except Exception:
                pass  # Missing/unreadable/expired controls are closed in consumers.
        raise


def reconcile(target, *, journal, host, product, active_product=None, backup=None,
              migration_scope=None, initialize=False, minimum_free_bytes=1024**3):
    """Perform one bounded activation with admission closed, under host authority.

backup(active_product, journal, operations, recheck_fence) must create a complete
coherent set via backup_set.create; no caller receipt substitutes for that action.
migration_scope(target) is a context manager delivering an operation-only binding
and deleting its migration credential on exit. Both are trusted bootstrap code.
No retry/restore/open-admission operation exists on this interface.
"""
    with journal.lock(), failure_closes(target, host):
        if product.target is not target or (isinstance(host, GoogleHost) and host.target is not target):
            raise Refused('adapter_target_mismatch')
        target.unchanged()
        fence = host.check()
        generation = host.desired()
        if not isinstance(generation, str) or not re.fullmatch('[1-9][0-9]{0,30}', generation):
            raise Refused('desired_generation_invalid')
        product.preflight()
        # The actual host adapter additionally proves journal persistence on disk.
        if isinstance(host, GoogleHost):
            protected(journal.root, directory=True)
            if os.stat(journal.root).st_dev != os.stat(target.runtime['mounts']['execution']).st_dev:
                raise Refused('journal_not_on_installation_disk')
        if type(minimum_free_bytes) is not int or minimum_free_bytes < 1:
            raise Refused('free_space_policy_invalid')
        if shutil.disk_usage(journal.root).free < minimum_free_bytes:
            raise Refused('insufficient_disk_space')
        if active_product is not None:
            stable_installation(active_product.target, target)
            active_product.preflight()
            active_product.compatibility(target)
        elif not initialize:
            raise Refused('explicit_initialization_required')
        elif initialize is not True:
            raise Refused('explicit_initialization_required')
        if migration_scope is None:
            raise Refused('migration_credential_scope_required')
        record = journal.accept(target.desired['sequence'], contract.digest(target.desired))
        previous_fence = record['fence']
        if previous_fence is not None and previous_fence != fence:
            if (previous_fence.get('host_id') == fence.get('host_id')
                    and previous_fence.get('instance_id') != fence.get('instance_id')):
                raise Refused('replaced_host_requires_recovery')
            if previous_fence.get('host_id') != fence.get('host_id') and (
                    not isinstance(host, GoogleHost) or previous_fence.get('host_id') not in host.retired_hosts):
                raise Refused('previous_host_not_fenced')
        record['fence'] = fence
        record['desired_generation'] = generation
        journal.write(record)
        if record['stage'] == 'installed_closed':
            return dict(status='qualification_pending', admission='closed', sequence=record['sequence'])
        if record['installed'] is not None:
            if active_product is None or record['installed'] != {
                    **active_product.target.identity,
                    'binding_sha256': active_product.target.binding_sha256}:
                raise Refused('active_release_mismatch')
        elif active_product is not None:
            raise Refused('active_release_unrecorded')

        def checkpoint(stage):
            record['stage'] = stage
            journal.write(record)

        def recheck():
            target.unchanged()
            if host.check() != fence:
                raise Refused('host_fence_changed')

        def call(adapter, operation, **kwargs):
            recheck()
            operation_id = str(uuid4())
            record['operations'][operation] = dict(id=operation_id, state='intent', identity=adapter.target.identity)
            journal.write(record)
            result = adapter.call(operation, operation_id, **kwargs)
            record['operations'][operation]['state'] = 'complete'
            journal.write(record)
            return result

        try:
            checkpoint('prestaged')
            if active_product is not None:
                call(active_product, 'admission')
                checkpoint('draining')
                call(active_product, 'drain')
                call(active_product, 'stop')
                checkpoint('quiesced')
                if backup is None:
                    raise Refused('coherent_backup_adapter_required')
                record['backup'] = backup(active_product, journal, record['operations'], recheck)
                if not isinstance(record['backup'], dict) or not record['backup']:
                    raise Refused('coherent_backup_incomplete')
                checkpoint('backed_up')
            # Preserve the previous installed binding until migration completes.
            # An intent before identity switch makes a crash operator-recoverable.
            record['mutation'] = True
            record['migration'] = dict(state='intent', release_sha256=target.identity['release_sha256'],
                                       checksum=contract.digest(target.release['stores']))
            checkpoint('migrating')
            recheck()
            control = Path(target.binding['control_root'])
            atomic(control / 'runtime-identity.json', target.identity, mode=0o644)
            # Closed admission is written directly before the first lifecycle
            # operation because initialize has no previous product identity.
            atomic(control / 'admission.json', dict(schema='hyprn-admission/v1', **target.identity,
                                                   browser=False, scientific=False, expires_at=0), mode=0o644)
            with migration_scope(target) as binding:
                call(product, 'initialize' if active_product is None else 'migrate', migration_binding=binding)
            record['migration']['state'] = 'complete'
            record['installed'] = {**target.identity, 'binding_sha256': target.binding_sha256}
            journal.write(record)
            # Native attestation requires a stopped native owner in current CLI.
            checkpoint('qualifying')
            call(product, 'qualify')
            checkpoint('starting')
            call(product, 'start')
            call(product, 'inspect')
            checkpoint('installed_closed')
            return dict(status='qualification_pending', admission='closed', sequence=record['sequence'])
        except BaseException as error:
            # Identity-bound admission is closed above; expired or missing records
            # are closed in consumers. Never switch back to old stores or retry an
            # uncertain operation. Best effort reclose uses current host identity.
            try:
                adapter = product if record['mutation'] else active_product
                if adapter is not None:
                    recheck()
                    adapter.call('admission', str(uuid4()))
            except Exception:
                pass
            record['failure'] = error.reason if isinstance(error, Refused) else 'operation_outcome_uncertain'
            journal.write(record)
            raise
