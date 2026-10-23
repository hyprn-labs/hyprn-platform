"""Remove reviewed duplicate transfer archives, never installed releases or product records."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


def sibling(name):
    spec = importlib.util.spec_from_file_location(name,
                                                Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = sibling('contract')
stage = sibling('release_stage')
reconcile = sibling('reconcile')
Refused = stage.Refused
JOURNAL = '/srv/hyprn/staging/deployment-journal'
IDENTITY = '/run/hyprn/control/runtime-identity.json'
NAMES = {'app.oci.tar': 'app', 'modeling.oci.tar': 'modeling',
         'worker.oci.tar': 'worker', 'native.tar.gz': 'native_bundle'}
SHA = re.compile('[a-f0-9]{64}')


def location(path, *, source=False):
    if not isinstance(path, str):
        raise Refused('archive_location')
    value = PurePosixPath(path)
    roots = (stage.DEPLOYMENT_ROOT,) if source else (
        stage.DEPLOYMENT_ROOT, stage.DATA_DEPLOYMENT_ROOT)
    for root in roots:
        relative = value.relative_to(root) if value.is_relative_to(root) else None
        if (relative is not None and len(relative.parts) == 2
                and SHA.fullmatch(relative.parts[0]) and relative.name in NAMES
                and str(value) == path):
            return relative.parts[0], relative.name
    raise Refused('archive_location')


def validate(value):
    if (not isinstance(value, dict) or set(value) != {
            'schema', 'identity', 'retained_releases', 'archives'}
            or value['schema'] != 'hyprn-deployment-archive-cleanup/v1'):
        raise Refused('cleanup_shape')
    # Reuse the fixed host identity validator; this does not stage any file.
    stage.validate(dict(schema='hyprn-release-stage/v1', release_sha256='a' * 64,
        identity=value['identity'], bucket=stage.BUCKET, files=[dict(
            destination=stage.PLATFORM_ROOT + '/identity-check', object='identity-check',
            sha256='b' * 64, size_bytes=1, mode=0o644)]))
    retained = value['retained_releases']
    if (not isinstance(retained, list) or not 2 <= len(retained) <= 32
            or not all(isinstance(x, str) and SHA.fullmatch(x) for x in retained)
            or len(set(retained)) != len(retained)):
        raise Refused('retention_set')
    rows = value['archives']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
        raise Refused('archive_count')
    paths = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'path', 'retained_copy', 'sha256',
                'size_bytes', 'mode', 'inventory_sha256', 'retained_inventory_sha256'}
                or any(not isinstance(row[k], str) or not SHA.fullmatch(row[k])
                       for k in ('sha256', 'inventory_sha256', 'retained_inventory_sha256'))
                or type(row['size_bytes']) is not int or not 0 < row['size_bytes'] <= stage.MAX_BYTES
                or type(row['mode']) is not int or row['mode'] not in (0o600, 0o644)):
            raise Refused('archive_shape')
        release, name = location(row['path'], source=True)
        kept_release, kept_name = location(row['retained_copy'])
        if (release in retained or kept_release not in retained or name != kept_name
                or row['path'] in paths):
            raise Refused('archive_retention')
        paths.add(row['path'])
    return value


def read_document(path, expected=None):
    path = PurePosixPath(path)
    parent = stage.directory(str(path.parent))
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != stage.OWNER
                    or info.st_nlink != 1 or info.st_mode & 0o022
                    or info.st_size > stage.MAX_MANIFEST):
                raise Refused('document_authority')
            raw = stream.read(stage.MAX_MANIFEST + 1)
        if expected and hashlib.sha256(raw).hexdigest() != expected:
            raise Refused('inventory_changed')
        def pairs(items):
            result = {}
            for key, val in items:
                if key in result:
                    raise Refused('duplicate_key')
                result[key] = val
            return result
        return json.loads(raw, object_pairs_hook=pairs)
    finally:
        os.close(parent)


def inventory(path, expected, row):
    release, name = location(path)
    value = read_document(str(PurePosixPath(path).parent / 'payload.json'), expected)
    if (not isinstance(value, dict) or value.get('schema') != 'hyprn-hosted-payload/v1'
            or value.get('release_sha256') != release
            or value.get('files', {}).get(NAMES[name]) != dict(
                path=name, sha256=row['sha256'], size_bytes=row['size_bytes'])):
        raise Refused('archive_inventory_mismatch')


def guards(value, journal):
    """Current runtime, installed release and backup source all remain recoverable."""
    identity = read_document(IDENTITY)
    observed = [identity.get('release_sha256')]
    state = journal.read()
    if not state or state.get('stage') not in ('installed_closed', 'active'):
        raise Refused('deployment_not_settled')
    observed += [state.get('installed', {}).get('release_sha256'),
                 state.get('backup', {}).get('identity', {}).get('release_sha256')]
    if any(not isinstance(x, str) or not SHA.fullmatch(x)
           or x not in value['retained_releases'] for x in observed):
        raise Refused('active_or_recovery_release_not_retained')


def fingerprint(parent, name):
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_mode, info.st_uid, info.st_nlink)


def verify_file(path, row, verified):
    path = PurePosixPath(path)
    parent = stage.directory(str(path.parent))
    try:
        before = fingerprint(parent, path.name)
        key = (str(path), row['sha256'], row['size_bytes'], row['mode'])
        if key in verified:
            if before != verified[key]:
                raise Refused('verified_archive_changed')
            return before
        if not stage.inspect_file(parent, path.name, row):
            return None
        if before != fingerprint(parent, path.name):
            raise Refused('verified_archive_changed')
        verified[key] = before
        return before
    finally:
        os.close(parent)


def inspect(row, verified):
    inventory(row['path'], row['inventory_sha256'], row)
    inventory(row['retained_copy'], row['retained_inventory_sha256'], row)
    if not verify_file(row['retained_copy'], row, verified):
        raise Refused('retained_copy_missing')
    return verify_file(row['path'], row, verified)


def remove(row, expected):
    """Recheck the verified inode under the deployment lock before its single unlink."""
    path = PurePosixPath(row['path'])
    parent = stage.directory(str(path.parent))
    try:
        observed = fingerprint(parent, path.name)
        if observed != expected:
            raise Refused('verified_archive_changed')
        if observed is None:
            return False
        os.unlink(path.name, dir_fd=parent)
        os.fsync(parent)
        return True
    finally:
        os.close(parent)


def run(value, approved=None, *, host=None):
    validate(value)
    if os.geteuid() != stage.OWNER:
        raise Refused('root_required')
    if approved is not None and approved != stage.digest(value):
        raise Refused('approval_mismatch')
    host = host or stage.AttachedHost()
    host.verify(value['identity'])
    journal_fd = stage.directory(JOURNAL)
    os.close(journal_fd)
    with reconcile.Journal(JOURNAL).lock() as journal:
        guards(value, journal)
        verified = {}
        present = [inspect(row, verified) for row in value['archives']]
        removed = []
        if approved is not None:
            for row, expected in zip(value['archives'], present):
                # Same verified bytes/inode must still exist; no repeated multi-GB hashing.
                if not verify_file(row['retained_copy'], row, verified):
                    raise Refused('retained_copy_missing')
                if remove(row, expected):
                    removed.append(row['path'])
        return dict(plan_sha256=stage.digest(value),
            reclaimable_bytes=sum(row['size_bytes'] for row, exists in zip(value['archives'], present)
                                  if exists), removed=removed,
            retained_releases=value['retained_releases'], product_records_changed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'apply'))
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--approve-sha256')
    args = parser.parse_args()
    try:
        if args.operation == 'apply' and not args.approve_sha256:
            raise Refused('approval_required')
        result = run(read_document(args.manifest),
                     args.approve_sha256 if args.operation == 'apply' else None)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'refused': str(error) if isinstance(error, Refused) else 'cleanup_failed'}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
