"""Install an authenticated native bundle without importing its product code.

Trusted bootstrap supplies the release and exact destination. No fetch, Docker
load, secret delivery, process start or admission change happens here. The caller
holds the deployment lock. A failed installation never replaces another release.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tarfile
import tempfile

_spec = importlib.util.spec_from_file_location('hyprn_install_contract',
                                              Path(__file__).with_name('contract.py'))
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)


def protected_directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise contract.Invalid('release_destination')
    for part in (path, *path.parents):
        info = part.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise contract.Invalid('release_destination')
        if info.st_uid not in (0, os.geteuid()):
            raise contract.Invalid('release_directory_owner')
        if info.st_mode & 0o022 and not (part != path and info.st_mode & stat.S_ISVTX):
            raise contract.Invalid('release_directory_writable')
    return path


def document(archive, name, maximum):
    member = archive.getmember(name)
    if not member.isfile() or member.size > maximum:
        raise contract.Invalid('release_document')
    with archive.extractfile(member) as stream:
        try:
            return json.loads(stream.read(), object_pairs_hook=contract.pairs,
                              parse_constant=contract.reject_constant)
        except (ValueError, UnicodeError):
            raise contract.Invalid('release_document') from None


def install_native(bundle, specification, destination, *, source_commit):
    """Verify the complete bundle, then create a fresh immutable release tree."""
    destination = Path(destination)
    parent = protected_directory(destination.parent)
    if destination.name != source_commit or len(source_commit) != 40 or any(
            c not in '0123456789abcdef' for c in source_commit):
        raise contract.Invalid('release_destination')
    if destination.exists() or destination.is_symlink():
        raise contract.Invalid('release_already_exists')
    # Authenticate before opening/extracting any member. Keep one verified inode
    # open so replacement of the supplied pathname cannot switch archive content.
    path = Path(bundle)
    if path.is_symlink():
        raise contract.Invalid('release_bundle_link')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    stage = None
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022
                or info.st_uid not in (0, os.geteuid())):
            raise contract.Invalid('release_bundle_authority')
        # The contract validates exact bytes, member kinds, paths and expansion
        # bounds. Match the opened inode again before reading through it.
        contract.check_bundle(path, specification)
        current = path.stat()
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise contract.Invalid('release_bundle_changed')
        with os.fdopen(os.dup(fd), 'rb') as raw:
            hasher = hashlib.sha256()
            for block in iter(lambda: raw.read(1024 * 1024), b''):
                hasher.update(block)
            actual = hasher.hexdigest()
        if actual != specification['sha256'] or info.st_size != specification['size_bytes']:
            raise contract.Invalid('release_bundle_changed')
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), 'rb') as raw, tarfile.open(fileobj=raw) as archive:
            build = document(archive, 'build.json', 16384)
            inventory = document(archive, 'bundle-inventory.json', 32 * 1024 * 1024)
            if (build.get('source_commit') != source_commit or build.get('prefix') != str(destination)
                    or build.get('target') != 'linux/amd64' or not isinstance(inventory, dict)):
                raise contract.Invalid('release_build_identity')
            members = {member.name: member for member in archive.getmembers()}
            if set(members) != {*inventory, 'bundle-inventory.json'}:
                raise contract.Invalid('release_inventory')
            stage = Path(tempfile.mkdtemp(prefix='.' + source_commit + '-', dir=parent))
            for name, member in members.items():
                if not member.isfile():
                    raise contract.Invalid('release_inventory')
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                hasher = hashlib.sha256()
                with archive.extractfile(member) as incoming, target.open('xb') as outgoing:
                    for block in iter(lambda: incoming.read(1024 * 1024), b''):
                        outgoing.write(block)
                        hasher.update(block)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                if name != 'bundle-inventory.json':
                    expected = inventory[name]
                    if (not isinstance(expected, dict) or set(expected) != {'sha256', 'size'}
                            or type(expected['size']) is not int or expected['size'] != target.stat().st_size
                            or expected['sha256'] != hasher.hexdigest()):
                        raise contract.Invalid('release_inventory_bytes')
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
            for directory in sorted([stage, *(p for p in stage.rglob('*') if p.is_dir())],
                                    key=lambda p: len(p.parts), reverse=True):
                directory.chmod(0o755)
                sync = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(sync)
                finally:
                    os.close(sync)
            if destination.exists() or destination.is_symlink():
                raise contract.Invalid('release_already_exists')
            # Deployment lock and protected parent exclude concurrent installers.
            stage.rename(destination)
            stage = None
            sync = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(sync)
            finally:
                os.close(sync)
        return {'source_commit': source_commit, 'bundle_sha256': actual,
                'files': len(inventory), 'product_code_executed': False}
    finally:
        os.close(fd)
        if stage is not None:
            shutil.rmtree(stage)
