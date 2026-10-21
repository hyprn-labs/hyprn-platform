"""Activate one reviewed installation behind closed admission.

Only a protected bootstrap policy grants this host entry point its exact inputs.
No descriptor supplies executable hooks, cloud mutations, publication or an
admission-opening authority. Run from the installed, reviewed platform tree.
"""
import argparse
from contextlib import contextmanager
import hashlib
import fcntl
import hmac
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
from types import SimpleNamespace
from uuid import uuid4


HOST = Path(__file__).resolve().parent


def sibling(name):
    spec = importlib.util.spec_from_file_location(name, HOST / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = sibling('contract')
reconcile = sibling('reconcile')
installer = sibling('install_release')
images = sibling('images')
backup_set = sibling('backup_set')
loader = reconcile._secret_loader
Refused = reconcile.Refused
CONSUMERS = ('app', 'dispatcher', 'modeling')
CONTROL_NAMES = {'assistant_plan', 'assistant_continuity', 'database_ca'}
POLICY_FIELDS = {'schema', 'binding', 'desired_sha256', 'initialize', 'active',
                 'journal_root', 'disk', 'images', 'secret_versions', 'controls',
                 'backup', 'minimum_free_bytes', 'preflight'}


def secure(path, *, directory=False, private=False):
    """The runtime requires root; helpers also permit isolated unprivileged tests."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Refused('bootstrap_path')
    for item in (path, *path.parents):
        info = item.lstat()
        if (stat.S_ISLNK(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or (info.st_mode & 0o022 and not (item != path and info.st_mode & stat.S_ISVTX))):
            raise Refused('bootstrap_path_authority')
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or (not directory and info.st_nlink != 1):
        raise Refused('bootstrap_path_authority')
    if private and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)):
        raise Refused('bootstrap_private_authority')
    return path


def exact_fields(value, fields):
    return isinstance(value, dict) and set(value) == set(fields)


def sha(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def absolute(value):
    return (isinstance(value, str) and Path(value).is_absolute()
            and str(Path(value)) == value and '..' not in Path(value).parts)


def validate_policy(value):
    """Closed syntax only; this function never grants host authority."""
    if not exact_fields(value, POLICY_FIELDS) or value['schema'] != 'hyprn-bootstrap/v1':
        raise Refused('bootstrap_policy')
    if (type(value['initialize']) is not bool or not sha(value['desired_sha256'])
            or not all(absolute(value[key]) for key in ('binding', 'journal_root'))
            or type(value['minimum_free_bytes']) is not int or not 1 <= value['minimum_free_bytes'] <= 2**53 - 1):
        raise Refused('bootstrap_policy')
    disk = value['disk']
    if (not exact_fields(disk, {'disk_name', 'device_name', 'retired_hosts'})
            or not isinstance(disk['retired_hosts'], list) or len(disk['retired_hosts']) > 32
            or any(not isinstance(name, str) or not re.fullmatch('[a-z][a-z0-9-]{0,61}[a-z0-9]', name)
                   for name in (disk['disk_name'], disk['device_name'], *disk['retired_hosts']))):
        raise Refused('bootstrap_disk_policy')
    if len(set(disk['retired_hosts'])) != len(disk['retired_hosts']):
        raise Refused('bootstrap_disk_policy')
    preflight = value['preflight']
    if (not exact_fields(preflight, {'policy', 'sha256'})
            or not absolute(preflight['policy']) or not sha(preflight['sha256'])):
        raise Refused('bootstrap_preflight_policy')
    image = value['images']
    if (not exact_fields(image, {'docker', 'docker_sha256', 'config_root'})
            or not absolute(image['docker']) or not absolute(image['config_root'])
            or not sha(image['docker_sha256'])):
        raise Refused('bootstrap_image_policy')
    controls = value['controls']
    if not exact_fields(controls, CONTROL_NAMES):
        raise Refused('bootstrap_control_policy')
    for item in controls.values():
        if not exact_fields(item, {'path', 'sha256'}) or not absolute(item['path']) or not sha(item['sha256']):
            raise Refused('bootstrap_control_policy')
    versions = value['secret_versions']
    if (not isinstance(versions, dict) or not versions
            or any(not isinstance(alias, str) or type(version) is not int or not 1 <= version <= 2147483647
                   for alias, version in versions.items())):
        raise Refused('bootstrap_secret_policy')
    active, backup = value['active'], value['backup']
    if value['initialize']:
        if active is not None or backup is not None:
            raise Refused('bootstrap_initialization_policy')
    else:
        if (not exact_fields(active, {'binding', 'desired_sha256'})
                or not absolute(active['binding']) or not sha(active['desired_sha256'])
                or not exact_fields(backup, {'policy', 'approve_resource', 'root'})
                or not absolute(backup['policy']) or not absolute(backup['root'])
                or not isinstance(backup['approve_resource'], str)
                or not re.fullmatch(r'projects/hyprn-staging(?:-[a-z0-9-]+)?/instances/[a-z][a-z0-9-]{0,97}[a-z0-9]',
                                    backup['approve_resource'])):
            raise Refused('bootstrap_update_policy')
    return value


def load_policy(path):
    path = secure(path, private=True)
    return validate_policy(contract.read_json(path))


def bind_policy(policy, target, active=None):
    if contract.digest(target.desired) != policy['desired_sha256'] or str(target.path) != policy['binding']:
        raise Refused('bootstrap_desired_pin')
    journal_root = Path(policy['journal_root'])
    for owner in ('application', 'modeling', 'execution'):
        store_root = Path(target.runtime['mounts'][owner])
        if journal_root == store_root or store_root in journal_root.parents:
            # Host bookkeeping cannot populate a fresh owner store before its
            # explicit initialization or enter an owner's writable namespace.
            raise Refused('bootstrap_journal_inside_owner_store')
    expected = {alias: item['version'] for alias, item in target.runtime['secrets'].items()}
    if policy['secret_versions'] != expected:
        raise Refused('bootstrap_secret_pin')
    if policy['controls']['database_ca']['sha256'] != target.runtime['database']['ca_sha256']:
        raise Refused('bootstrap_database_ca_pin')
    secrets_root = Path(target.runtime['mounts']['secrets'])
    config_root = Path(policy['images']['config_root'])
    if config_root == secrets_root or secrets_root in config_root.parents or config_root in secrets_root.parents:
        raise Refused('bootstrap_registry_secret_scope')
    for item in policy['controls'].values():
        source = Path(item['path'])
        if any(source == root or root in source.parents for root in (secrets_root, config_root)):
            raise Refused('bootstrap_control_secret_scope')
    if active is not None:
        if (policy['active'] is None or str(active.path) != policy['active']['binding']
                or contract.digest(active.desired) != policy['active']['desired_sha256']):
            raise Refused('bootstrap_active_pin')
        reconcile.stable_installation(active, target)
        if active.runtime['secrets'] != target.runtime['secrets']:
            raise Refused('secret_rotation_requires_reviewed_hook')
        if active.runtime['database'] != target.runtime['database']:
            raise Refused('database_binding_change_requires_recovery')
    elif not policy['initialize']:
        raise Refused('bootstrap_active_required')


def read_pinned(specification):
    path = secure(specification['path'])
    with path.open('rb') as stream:
        raw = stream.read(contract.MAX_DOCUMENT + 1)
    if len(raw) > contract.MAX_DOCUMENT or hashlib.sha256(raw).hexdigest() != specification['sha256']:
        raise Refused('bootstrap_control_bytes')
    return raw


def control_inputs(policy):
    result = {name: read_pinned(specification) for name, specification in policy['controls'].items()}
    for name in ('assistant_plan', 'assistant_continuity'):
        if not isinstance(reconcile.decode(result[name]), dict):
            raise Refused('bootstrap_control_document')
    return result


def write_bytes(path, raw):
    path = Path(path)
    secure(path.parent, directory=True)
    if path.exists() or path.is_symlink():
        secure(path)
    temporary = path.with_name('.' + path.name + '-' + str(uuid4()))
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o644)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def public_control_directory(path):
    """Create the fixed public-certificate directory under a protected parent."""
    path = Path(path)
    secure(path.parent, directory=True)
    if not path.exists() and not path.is_symlink():
        path.mkdir(mode=0o755)
        path.chmod(0o755)
    secure(path, directory=True)
    if stat.S_IMODE(path.stat().st_mode) != 0o755:
        raise Refused('bootstrap_public_control_directory_mode')
    return path


def application_artifacts(target):
    """Prepare only the application-owned artifact directory; never repair foreign data."""
    parent = Path(target.runtime['mounts']['application'])
    uid = target.runtime['service_users']['app']
    if not parent.is_absolute() or any(p.is_symlink() for p in (parent, *parent.parents)):
        raise Refused('bootstrap_artifact_path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = os.open(parent, flags)
    try:
        info = os.fstat(root)
        if ((info.st_uid, info.st_gid) != (uid, uid)
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise Refused('bootstrap_artifact_owner')
        created = False
        try:
            os.mkdir('artifacts', mode=0o700, dir_fd=root)
            created = True
        except FileExistsError:
            pass
        fd = os.open('artifacts', flags, dir_fd=root)
        try:
            if created:
                os.fchown(fd, uid, uid)
                os.fchmod(fd, 0o700)
            info = os.fstat(fd)
            if ((info.st_uid, info.st_gid) != (uid, uid)
                    or stat.S_IMODE(info.st_mode) != 0o700):
                raise Refused('bootstrap_artifact_owner')
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(root)
    finally:
        os.close(root)


def load_preflight():
    """Resolve reviewed siblings even when Python excludes the script directory."""
    module = sibling('preflight')
    sibling('service_network_install')
    return module


def publish_controls(target, policy):
    values = control_inputs(policy)
    continuity = reconcile.decode(values['assistant_continuity'])
    if any(continuity.get(key) != value for key, value in target.identity.items()):
        raise Refused('bootstrap_continuity_identity')
    root = Path(target.binding['control_root'])
    destinations = {'assistant_plan': root / 'assistant-plan.json',
                    'assistant_continuity': root / 'assistant-continuity.json',
                    'database_ca': Path('/etc/hyprn/trust/cloudsql-server-ca.pem')}
    public_control_directory(destinations['database_ca'].parent)
    for name, path in destinations.items():
        write_bytes(path, values[name])


def native_archive(target):
    path = secure(target.binding['payload_inventory'])
    inventory = contract.read_json(path)
    if (not exact_fields(inventory, {'schema', 'release_sha256', 'files'})
            or inventory['schema'] != 'hyprn-hosted-payload/v1'
            or inventory['release_sha256'] != target.identity['release_sha256']
            or not isinstance(inventory['files'], dict)):
        raise Refused('bootstrap_payload_inventory')
    item = inventory['files'].get('native_bundle')
    if (not exact_fields(item, {'path', 'size_bytes', 'sha256'}) or not isinstance(item['path'], str)
            or type(item['size_bytes']) is not int or item['size_bytes'] < 1 or not sha(item['sha256'])):
        raise Refused('bootstrap_native_inventory')
    relative = PurePosixPath(item['path'])
    if (relative.is_absolute() or not relative.parts or '..' in relative.parts or '\\' in item['path']
            or str(relative) != item['path']
            or {key: item[key] for key in ('sha256', 'size_bytes')} != target.release['native_bundle']):
        raise Refused('bootstrap_native_inventory')
    return secure(path.parent / relative)


def prepared_product(target, *, install):
    archive = native_archive(target)
    configuration = target.preview['execution']['configuration']
    destination = Path(configuration['source']).parent
    secure(destination.parent, directory=True)
    if not destination.exists():
        if not install:
            raise Refused('active_release_missing')
        installer.install_native(archive, target.release['native_bundle'], destination,
                                 source_commit=target.release['source_commit'])
    inventory = installer.verify_native(archive, target.release['native_bundle'], destination,
                                        source_commit=target.release['source_commit'])
    python = Path(configuration['python'])
    keys = {'script_sha256': 'source/deployment/cloud_lifecycle.py',
            'verifier_sha256': 'source/deployment/cloud_release.py',
            'python_sha256': str(python.relative_to(destination))}
    try:
        pins = {name: inventory[relative]['sha256'] for name, relative in keys.items()}
    except (KeyError, TypeError):
        raise Refused('bootstrap_product_inventory') from None
    return reconcile.Product(target, python=str(python), **pins)


def secret_arguments(target, consumer, operation):
    return SimpleNamespace(root=target.runtime['mounts']['secrets'], consumer=consumer,
        operation=operation, identity_mode='attached-service-account',
        project_id=target.runtime['project_id'], project_number=target.runtime['project_number'])


def fresh_secrets(target):
    delivered = []
    try:
        for consumer in CONSUMERS:
            loader.deliver(secret_arguments(target, consumer, 'load'), target.runtime)
            delivered.append(consumer)
    except BaseException:
        for consumer in reversed(delivered):
            loader.deliver(secret_arguments(target, consumer, 'cleanup'), target.runtime)
        raise


def verify_existing_secrets(target):
    principal = reconcile.AttachedServiceAccount()
    principal.preflight(SimpleNamespace(**target.runtime))
    root = loader.private_directory(target.runtime['mounts']['secrets'])
    try:
        loader.require_tmpfs(root)
        fcntl.flock(root, fcntl.LOCK_SH | fcntl.LOCK_NB)
        for consumer in CONSUMERS:
            folder = Path(target.runtime['mounts']['secrets']) / consumer
            secure(folder, directory=True, private=True)
            aliases = contract.SECRET_CONSUMERS[consumer]
            if set(os.listdir(folder)) != set(aliases):
                raise Refused('bootstrap_secret_inventory')
            for alias in aliases:
                path = folder / alias
                info = path.lstat()
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_uid != loader.owner(target.runtime, consumer)
                        or stat.S_IMODE(info.st_mode) != 0o600):
                    raise Refused('bootstrap_secret_file')
                with path.open('rb') as stream:
                    current = stream.read(loader.MAX_SECRET + 1)
                expected = principal.fetch(target.runtime['secrets'][alias])
                if not hmac.compare_digest(current, expected):
                    raise Refused('bootstrap_secret_version_mismatch')
    finally:
        os.close(root)


@contextmanager
def migration_scope(target, policy):
    # On replacement this context starts only after old writers stopped and the
    # coherent backup completed. Normal consumer files remain at the same pins.
    publish_controls(target, policy)
    path = Path(target.binding['control_root']) / ('migration-binding-' + str(uuid4()) + '.json')
    loaded = False
    try:
        loader.deliver(secret_arguments(target, 'migration', 'load'), target.runtime)
        loaded = True
        reconcile.atomic(path, dict(target.binding,
            migration_secret_file=target.runtime['mounts']['secrets'] + '/migration/db-app-migration'))
        yield path
    finally:
        path.unlink(missing_ok=True)
        if loaded:
            loader.deliver(secret_arguments(target, 'migration', 'cleanup'), target.runtime)


class HeldJournal:
    """Reuse a live owned deployment descriptor, never a receipt or a second lock."""
    def __init__(self, journal):
        self.journal, self.pid = journal, os.getpid()

    def __getattr__(self, key):
        return getattr(self.journal, key)

    @contextmanager
    def lock(self):
        if self.pid != os.getpid() or self.journal.fd is None:
            raise Refused('bootstrap_deployment_hold_lost')
        backup_set.DeploymentFence(self.journal.fd, self.journal.lock_path).check()
        yield self
        backup_set.DeploymentFence(self.journal.fd, self.journal.lock_path).check()


def check_attempt(journal, target, active):
    previous = journal.read()
    if previous is None:
        if active is not None:
            raise Refused('active_release_unrecorded')
        return False
    sequence, expected = target.desired['sequence'], contract.digest(target.desired)
    if sequence < previous['sequence']:
        raise Refused('stale_sequence')
    if sequence == previous['sequence'] and previous['desired_sha256'] != expected:
        raise Refused('sequence_conflict')
    if previous['stage'] != 'installed_closed':
        raise Refused('operator_recovery_required')
    observed = target if sequence == previous['sequence'] else active
    if observed is None or previous['installed'] != {**observed.identity, 'binding_sha256': observed.binding_sha256}:
        raise Refused('active_release_mismatch')
    return sequence == previous['sequence']


def coherent_backup(policy, active, journal, operations, recheck):
    setting = policy['backup']
    if setting is None:
        raise Refused('bootstrap_backup_policy_required')
    root = secure(setting['root'], directory=True, private=True)
    secure(setting['policy'], private=True)
    operation = str(uuid4())
    destination = root / operation
    recheck()
    destination.mkdir(mode=0o700)
    # Complete/incomplete records are retained for recovery; never remove a set.
    return backup_set.create(active.target.path, deployment_fd=journal.fd,
        deployment_path=journal.lock_path, operation_id=operation, state_root=str(destination),
        stop_operation_id=operations['stop']['id'], drain_operation_id=operations['drain']['id'],
        approve_resource=setting['approve_resource'], backup_policy=setting['policy'],
        recheck_fence=recheck, timeout=300)


def run(policy_path):
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise Refused('bootstrap_linux_root_required')
    os.umask(0o077)
    policy = load_policy(policy_path)
    # Exact reviewed platform modules are protected before any privileged effect.
    for name in ('bootstrap', 'contract', 'reconcile', 'install_release', 'secrets', 'images', 'backup_set', 'cloudsql_backup', 'preflight',
                 'service_network_install', 'service_network', 'setup'):
        reconcile.protected(HOST / (name + '.py'))
    for name in ('host-packages.json', 'egress-proxy.json'):
        reconcile.protected(HOST / name)
    preflight = load_preflight()
    secure(policy['binding'], private=True)
    if policy['active'] is not None:
        secure(policy['active']['binding'], private=True)
    target = reconcile.Target(policy['binding'])
    active = reconcile.Target(policy['active']['binding']) if policy['active'] is not None else None
    target.protect()
    if active is not None:
        active.protect()
    bind_policy(policy, target, active)
    control_inputs(policy)
    secure(policy['journal_root'], directory=True, private=True)
    host = reconcile.GoogleHost(target, **policy['disk'])
    journal = reconcile.Journal(policy['journal_root'])
    with journal.lock(), reconcile.failure_closes(target, host):
        fence = host.check()
        host.desired()
        if os.stat(journal.root).st_dev != os.stat(target.runtime['mounts']['execution']).st_dev:
            raise Refused('journal_not_on_installation_disk')
        if check_attempt(journal, target, active):
            control = Path(target.binding['control_root'])
            identity = contract.read_json(secure(control / 'runtime-identity.json'))
            if identity != target.identity:
                raise Refused('bootstrap_installed_identity_mismatch')
            reconcile.atomic(control / 'admission.json', dict(schema='hyprn-admission/v1',
                **identity, browser=False, scientific=False, expires_at=0), mode=0o644)
            return {'status': 'qualification_pending', 'admission': 'closed', 'sequence': target.desired['sequence']}
        def recheck():
            if load_policy(policy_path) != policy or host.check() != fence:
                raise Refused('bootstrap_authority_changed')
        recheck()
        if shutil.disk_usage(journal.root).free < policy['minimum_free_bytes']:
            raise Refused('insufficient_disk_space')
        if active is None and (Path(target.binding['control_root']) / 'runtime-identity.json').exists():
            raise Refused('unrecorded_installation_requires_recovery')
        read_pinned({'path': policy['preflight']['policy'], 'sha256': policy['preflight']['sha256']})
        observation = preflight.check(target, policy['preflight']['policy'], host=host)
        if (not isinstance(observation, dict) or observation.get('bootstrap_ready') is not True
                or observation.get('admission_ready') is not False
                or not isinstance(observation.get('docker'), dict)
                or observation['docker'].get('path') != policy['images']['docker']
                or observation['docker'].get('sha256') != policy['images']['docker_sha256']):
            raise Refused('bootstrap_preflight_mismatch')
        recheck()
        product = prepared_product(target, install=True)
        active_product = prepared_product(active, install=False) if active is not None else None
        product.preflight()
        if active_product is not None:
            active_product.preflight()
        recheck()
        images.ensure_images(target, **policy['images'])
        recheck()
        if active is None:
            fresh_secrets(target)
        else:
            verify_existing_secrets(target)
        recheck()
        application_artifacts(target)
        recheck()
        result = reconcile.reconcile(target, journal=HeldJournal(journal), host=host,
            product=product, active_product=active_product,
            backup=lambda product, held, operations, check: coherent_backup(policy, product, held, operations, check),
            migration_scope=lambda selected: migration_scope(selected, policy),
            initialize=policy['initialize'], minimum_free_bytes=policy['minimum_free_bytes'])
        if result.get('admission') != 'closed' or result.get('status') != 'qualification_pending':
            raise Refused('bootstrap_unexpected_admission')
        return result


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise Refused('bootstrap_arguments')


def main(argv=None):
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('--policy', required=True)
        arguments = parser.parse_args(argv)
        print(json.dumps(run(arguments.policy), sort_keys=True))
        return 0
    except Exception as error:
        reason = error.reason if isinstance(error, Refused) else 'bootstrap_refused'
        print(json.dumps({'status': 'refused', 'admission': 'unverified', 'reason_code': reason}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
