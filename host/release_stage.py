"""Stage reviewed nonsecret release files; no API writes or process execution."""
import argparse
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
import time
from urllib.parse import quote
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

OWNER = 0
PROJECT = 'hyprn-staging'
BUCKET = 'hyprn-staging-artifacts'
PLATFORM_ROOT = '/opt/hyprn/platform/staging-20261021'
DEPLOYMENT_ROOT = '/opt/hyprn/staging-deployment'
MAX_BYTES = 2 * 1024 ** 3
MAX_MANIFEST = 4 * 1024 ** 2


class Refused(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def validate(value):
    if (not isinstance(value, dict) or set(value) != {'schema', 'release_sha256', 'identity', 'bucket', 'files'}
            or value['schema'] != 'hyprn-release-stage/v1' or value['bucket'] != BUCKET
            or not re.fullmatch('[a-f0-9]{64}', str(value['release_sha256']))):
        raise Refused('manifest_shape')
    identity = value['identity']
    if (not isinstance(identity, dict) or set(identity) != {'project_id', 'project_number',
            'instance_id', 'instance_name', 'zone', 'service_account'}
            or identity['project_id'] != PROJECT
            or not all(isinstance(v, str) for v in identity.values())
            or not re.fullmatch('[1-9][0-9]{5,19}', identity['project_number'])
            or not re.fullmatch('[1-9][0-9]{5,19}', identity['instance_id'])
            or identity['instance_name'] != 'hyprn-staging-host'
            or identity['zone'] != 'europe-west1-b'
            or identity['service_account'] != 'hyprn-staging-runtime@hyprn-staging.iam.gserviceaccount.com'):
        raise Refused('host_identity_shape')
    rows = value['files']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise Refused('file_count')
    destinations, objects, total = set(), set(), 0
    roots = (PLATFORM_ROOT + '/', DEPLOYMENT_ROOT + '/' + value['release_sha256'] + '/')
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'destination', 'object', 'sha256', 'size_bytes', 'mode'}
                or not isinstance(row['destination'], str) or not isinstance(row['object'], str)
                or not re.fullmatch('[a-f0-9]{64}', str(row['sha256']))
                or type(row['size_bytes']) is not int or not 0 < row['size_bytes'] <= MAX_BYTES
                or type(row['mode']) is not int or row['mode'] not in (0o600, 0o644, 0o755)):
            raise Refused('file_shape')
        destination = PurePosixPath(row['destination'])
        obj = PurePosixPath(row['object'])
        if (not row['destination'].startswith(roots) or '..' in destination.parts
                or str(destination) != row['destination'] or not destination.is_absolute()
                or destination.name.startswith('.stage-')
                or obj.is_absolute() or '..' in obj.parts or str(obj) != row['object']
                or not row['object'] or '\\' in row['object']
                or any(ord(c) < 32 for c in row['object'] + row['destination'])
                or row['destination'] in destinations or row['object'] in objects):
            raise Refused('file_location')
        destinations.add(row['destination']); objects.add(row['object'])
        total += row['size_bytes']
    if total > MAX_BYTES:
        raise Refused('download_budget')
    if any(name.startswith(other + '/') for name in destinations
           for other in destinations if name != other):
        raise Refused('file_directory_overlap')
    return value


def directory(path, create=False):
    """Traverse root-owned directories with no symlinks or writable ancestors."""
    path = PurePosixPath(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Refused('directory_path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in path.parts[1:]:
            try:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(name, 0o755, dir_fd=fd)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.fchmod(child, 0o755)
            info = os.fstat(child)
            if info.st_uid != OWNER or info.st_mode & 0o022:
                os.close(child)
                raise Refused('unprotected_directory')
            os.close(fd); fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def protected_manifest(path):
    if os.geteuid() != OWNER:
        raise Refused('root_required')
    target = PurePosixPath(path)
    parent = directory(str(target.parent))
    try:
        fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != OWNER or info.st_nlink != 1
                    or info.st_mode & 0o022 or info.st_size > MAX_MANIFEST):
                raise Refused('unprotected_manifest')
            def pairs(items):
                result = {}
                for key, val in items:
                    if key in result:
                        raise Refused('duplicate_key')
                    result[key] = val
                return result
            return validate(json.loads(stream.read(MAX_MANIFEST + 1), object_pairs_hook=pairs))
    finally:
        os.close(parent)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Refused('redirect_refused')


class AttachedHost:
    def __init__(self):
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.token = None
        self.token_expires_at = 0
        self.verified = False

    def metadata(self, suffix):
        request = Request('http://169.254.169.254/computeMetadata/v1/' + suffix,
                          headers={'Metadata-Flavor': 'Google'})
        with self.opener.open(request, timeout=10) as reply:
            if reply.headers.get('Metadata-Flavor') != 'Google':
                raise Refused('metadata_origin')
            data = reply.read(65537)
            if len(data) > 65536:
                raise Refused('metadata_size')
            return data.decode().strip()

    def verify(self, identity):
        self.verified = False
        self.token = None
        paths = {'project_id': 'project/project-id', 'project_number': 'project/numeric-project-id',
                 'instance_id': 'instance/id', 'instance_name': 'instance/name',
                 'zone': 'instance/zone', 'service_account': 'instance/service-accounts/default/email'}
        for name, suffix in paths.items():
            observed = self.metadata(suffix)
            if name == 'zone':
                observed = observed.rsplit('/', 1)[-1]
            if observed != identity[name]:
                raise Refused('attached_host_mismatch')
        self.refresh_token()
        self.verified = True

    def refresh_token(self):
        self.token = None
        started = time.monotonic()
        token = json.loads(self.metadata('instance/service-accounts/default/token'))
        if (token.get('token_type') != 'Bearer' or type(token.get('expires_in')) is not int
                or token['expires_in'] < 60 or not isinstance(token.get('access_token'), str)
                or not token['access_token'] or any(c.isspace() for c in token['access_token'])):
            raise Refused('attached_token_invalid')
        self.token = token['access_token']
        self.token_expires_at = started + token['expires_in']

    def download(self, obj):
        if not self.verified:
            raise Refused('attached_host_unverified')
        if self.token is None or self.token_expires_at - time.monotonic() < 90:
            self.refresh_token()
        request = Request('https://storage.googleapis.com/download/storage/v1/b/' + BUCKET
                          + '/o/' + quote(obj, safe='') + '?alt=media',
                          headers={'Authorization': 'Bearer ' + self.token})
        return self.opener.open(request, timeout=30)


def inspect_file(parent, name, row):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except FileNotFoundError:
        return False
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != OWNER or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) != row['mode'] or info.st_size != row['size_bytes']):
            raise Refused('existing_file_differs')
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
        if h.hexdigest() != row['sha256']:
            raise Refused('existing_file_differs')
    return True


def stage(row, host, deadline):
    target = PurePosixPath(row['destination'])
    parent = directory(str(target.parent), create=True)
    partial = '.stage-' + row['sha256'] + '.partial'
    try:
        if inspect_file(parent, target.name, row):
            return 'already_present'
        try:
            os.stat(partial, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise Refused('interrupted_download_requires_review')
        fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream, host.download(row['object']) as response:
            if response.status != 200 or response.headers.get('Content-Length') != str(row['size_bytes']):
                raise Refused('download_length')
            count, h = 0, hashlib.sha256()
            while True:
                if time.monotonic() >= deadline:
                    raise Refused('download_deadline')
                block = response.read(min(1024 * 1024, row['size_bytes'] - count + 1))
                if not block:
                    break
                count += len(block)
                if count > row['size_bytes']:
                    raise Refused('download_length')
                stream.write(block); h.update(block)
            if count != row['size_bytes'] or h.hexdigest() != row['sha256']:
                raise Refused('download_digest')
            os.fchmod(stream.fileno(), row['mode'])
            stream.flush(); os.fsync(stream.fileno())
        # Link is create-only, unlike rename/replace. An interrupted finalization
        # leaves inspectable bytes; it never silently overwrites a target.
        os.link(partial, target.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.unlink(partial, dir_fd=parent); os.fsync(parent)
        return 'staged'
    finally:
        os.close(parent)


def reconcile(value):
    """Inspect interrupted staging without creating, deleting or changing files."""
    validate(value)
    result = []
    for row in value['files']:
        target = PurePosixPath(row['destination'])
        try:
            parent = directory(str(target.parent))
        except FileNotFoundError:
            result.append({'destination': row['destination'], 'state': 'missing'})
            continue
        try:
            if inspect_file(parent, target.name, row):
                state = 'already_present'
            else:
                try:
                    info = os.stat('.stage-' + row['sha256'] + '.partial',
                                   dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    state = 'missing'
                else:
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != OWNER:
                        raise Refused('unprotected_partial')
                    state = 'interrupted_download_requires_review'
            result.append({'destination': row['destination'], 'state': state})
        finally:
            os.close(parent)
    return {'plan_sha256': digest(value), 'files': result, 'changed': False}


def apply(value, approved, host=None):
    validate(value)
    if os.geteuid() != OWNER or approved != digest(value):
        raise Refused('approval_or_privilege')
    host = host or AttachedHost()
    host.verify(value['identity'])
    deadline = time.monotonic() + 600
    return {'plan_sha256': approved, 'files': [
        {'destination': row['destination'], 'state': stage(row, host, deadline)}
        for row in value['files']], 'application_started': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'apply', 'reconcile'))
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--approve')
    args = parser.parse_args()
    try:
        value = protected_manifest(args.manifest)
        result = {'plan_sha256': digest(value), 'files': len(value['files']),
                  'size_bytes': sum(row['size_bytes'] for row in value['files'])}
        if args.operation == 'apply':
            result = apply(value, args.approve)
        elif args.operation == 'reconcile':
            result = reconcile(value)
        print(json.dumps(result, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'refused': str(error) if isinstance(error, Refused) else 'stage_failed'}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
