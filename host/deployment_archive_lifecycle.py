"""Bound the delivery cache; durable objects and current/rollback releases are retained."""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import sys
import time

_spec = importlib.util.spec_from_file_location('deployment_cleanup',
    Path(__file__).with_name('deployment_archive_cleanup.py'))
cleanup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cleanup)
stage, Refused = cleanup.stage, cleanup.Refused
GiB = 1024 ** 3


def validate(policy):
    fields = {'schema', 'identity', 'max_cleanup_bytes', 'max_seconds',
              'max_cache_bytes', 'min_free_bytes'}
    if (not isinstance(policy, dict) or set(policy) != fields
            or policy['schema'] != 'hyprn-deployment-cache-policy/v1'):
        raise Refused('cache_policy_shape')
    for name, minimum, maximum in (
            ('max_cleanup_bytes', stage.MAX_BYTES, 4 * GiB), ('max_seconds', 30, 600),
            ('max_cache_bytes', 2 * GiB, 64 * GiB), ('min_free_bytes', GiB, 32 * GiB)):
        if type(policy[name]) is not int or not minimum <= policy[name] <= maximum:
            raise Refused('cache_policy_budget')
    stage.validate(dict(schema='hyprn-release-stage/v1', release_sha256='a' * 64,
        identity=policy['identity'], bucket=stage.BUCKET, files=[dict(
            destination=stage.PLATFORM_ROOT + '/identity-check', object='identity-check',
            sha256='b' * 64, size_bytes=1, mode=0o644)]))


def retained_releases(journal):
    identity = cleanup.read_document(cleanup.IDENTITY)
    state = journal.read() or {}
    if state.get('stage') not in ('installed_closed', 'active'):
        raise Refused('deployment_not_settled')
    values = [identity.get('release_sha256'), state.get('installed', {}).get('release_sha256'),
              state.get('backup', {}).get('identity', {}).get('release_sha256')]
    if any(not isinstance(v, str) or not cleanup.SHA.fullmatch(v) for v in values):
        raise Refused('recovery_identity_missing')
    return sorted(set(values))


def discover(policy, retained):
    """Inspect exact top-level archive names; unknown/receipt-less contents are preserved."""
    rows, total, unmanaged, protected, skipped = [], 0, 0, 0, 0
    directories = 0
    for root in (stage.DEPLOYMENT_ROOT, stage.DATA_DEPLOYMENT_ROOT):
        try:
            root_fd = stage.directory(root)
        except FileNotFoundError:
            continue
        try:
            releases = sorted(os.listdir(root_fd))
        finally:
            os.close(root_fd)
        if len(releases) > 1000:
            raise Refused('cache_inventory_limit')
        for release in releases:
            if not cleanup.SHA.fullmatch(release):
                skipped += 1
                continue
            directory = Path(root) / release
            parent = stage.directory(str(directory))
            directories += 1
            try:
                files = []
                for name in sorted(cleanup.NAMES):
                    observed = cleanup.fingerprint(parent, name)
                    if observed is None:
                        continue
                    _, _, size, _, _, mode, uid, links = observed
                    if (not stat.S_ISREG(mode) or uid != stage.OWNER or links != 1
                            or stat.S_IMODE(mode) not in (0o600, 0o644)):
                        raise Refused('cache_archive_authority')
                    total += size
                    files.append((name, size, stat.S_IMODE(mode)))
                if release in retained:
                    protected += sum(row[1] for row in files)
                    continue
                try:
                    receipt = cleanup.read_document(str(directory / stage.RECEIPT))
                except FileNotFoundError:
                    unmanaged += sum(row[1] for row in files)
                    continue
                stage.validate(receipt)
                if (receipt['identity'] != policy['identity']
                        or receipt['release_sha256'] != release):
                    raise Refused('cache_receipt_identity')
                sources = {r['destination']: r for r in receipt['files']}
                for name, size, mode in files:
                    source = sources.get(str(directory / name))
                    if source is None:
                        unmanaged += size
                        continue
                    if source['size_bytes'] != size or source['mode'] != mode:
                        raise Refused('cache_receipt_file_changed')
                    row = dict(path=str(directory / name), object=source['object'],
                        sha256=source['sha256'], size_bytes=size, mode=mode)
                    cleanup.inventory(row['path'], None, row)
                    rows.append(row)
            finally:
                os.close(parent)
    return rows, dict(cache_bytes=total, protected_bytes=protected,
        unmanaged_archive_bytes=unmanaged, release_directories=directories,
        unrecognized_entries=skipped)


def verify_remote(host, row, deadline):
    """Hash the exact durable generation without materializing another local copy."""
    if time.monotonic() >= deadline:
        raise Refused('cache_cleanup_deadline')
    metadata = host.object_version(row['object'])
    if int(metadata['size']) != row['size_bytes']:
        raise Refused('durable_archive_size')
    generation = metadata['generation']
    count, digest = 0, hashlib.sha256()
    with host.download(row['object'], generation=generation) as response:
        if response.status != 200 or response.headers.get('Content-Length') != str(row['size_bytes']):
            raise Refused('durable_archive_size')
        while True:
            if time.monotonic() >= deadline:
                raise Refused('cache_cleanup_deadline')
            block = response.read(min(1024 * 1024, row['size_bytes'] - count + 1))
            if not block:
                break
            count += len(block)
            if count > row['size_bytes']:
                raise Refused('durable_archive_size')
            digest.update(block)
    if count != row['size_bytes'] or digest.hexdigest() != row['sha256']:
        raise Refused('durable_archive_digest')
    return dict(bucket=stage.BUCKET, object=row['object'], generation=generation,
                sha256=row['sha256'], size_bytes=count)


def run(policy, approved=None, *, host=None):
    validate(policy)
    if os.geteuid() != stage.OWNER:
        raise Refused('root_required')
    if approved is not None and approved != stage.digest(policy):
        raise Refused('cache_policy_approval')
    host = host or stage.AttachedHost()
    host.verify(policy['identity'])
    stage.mounted_data()
    fd = stage.directory(cleanup.JOURNAL); os.close(fd)
    with cleanup.reconcile.Journal(cleanup.JOURNAL).lock() as journal:
        retained = retained_releases(journal)
        rows, metrics = discover(policy, retained)
        selected, size = [], 0
        for row in rows:
            if size + row['size_bytes'] <= policy['max_cleanup_bytes']:
                selected.append(row); size += row['size_bytes']
        free_before = stage.space_available(stage.DATA_ROOT)
        result = dict(policy_sha256=stage.digest(policy), retained_releases=retained,
            **metrics, eligible_bytes=sum(r['size_bytes'] for r in rows),
            selected_bytes=size, selected_files=len(selected), removed=[], durable_copies=[],
            free_bytes_before=free_before, free_bytes_after=free_before,
            root_free_bytes_before=stage.space_available('/'),
            root_free_bytes_after=stage.space_available('/'),
            cache_bytes_after=metrics['cache_bytes'], product_records_changed=False)
        if approved is not None:
            deadline = time.monotonic() + policy['max_seconds']
            verified, present, copies = {}, [], []
            for row in selected:
                if time.monotonic() >= deadline:
                    raise Refused('cache_cleanup_deadline')
                expected = cleanup.verify_file(row['path'], row, verified)
                if expected is None:
                    raise Refused('cache_archive_changed')
                present.append(expected)
                copies.append(verify_remote(host, row, deadline))
            if retained_releases(journal) != retained:
                raise Refused('cache_retention_changed')
            for row, expected, copy in zip(selected, present, copies):
                if cleanup.remove(row, expected):
                    result['removed'].append(row['path'])
                    result['durable_copies'].append(copy)
                    result['cache_bytes_after'] -= row['size_bytes']
            result['free_bytes_after'] = stage.space_available(stage.DATA_ROOT)
            result['root_free_bytes_after'] = stage.space_available('/')
        result['cleanup_pending'] = result['eligible_bytes'] > (
            metrics['cache_bytes'] - result['cache_bytes_after'])
        result['pressure'] = (result['cache_bytes_after'] > policy['max_cache_bytes']
                              or result['free_bytes_after'] < policy['min_free_bytes']
                              or result['root_free_bytes_after'] < policy['min_free_bytes'])
        return result
