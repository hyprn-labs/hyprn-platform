"""Fetch exact approved product images using temporary attached-host credentials.

The trusted bootstrap has already validated local payloads. This step only fills
Docker's image store; it never starts containers or opens application admission.
"""
import base64
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace

import reconcile


def ensure_images(target, *, docker, docker_sha256, config_root):
    """Pull immutable registry references, verify them, and remove temporary auth."""
    target.protect()
    tool = reconcile.protected(docker)
    if (not re.fullmatch('[0-9a-f]{64}', docker_sha256)
            or reconcile.digest_file(tool) != docker_sha256):
        raise reconcile.Refused('docker_tool_pin')
    registry = target.runtime['registry']
    project = target.runtime['project_id']
    if (not re.fullmatch(r'[a-z0-9-]+-docker\.pkg\.dev/[a-z][a-z0-9-]+/[a-z0-9-]+', registry)
            or registry.split('/')[1] != project
            or set(target.release['images']) != {'app', 'modeling', 'worker'}):
        raise reconcile.Refused('registry_policy')
    images = dict(target.release['images'])
    for image in images.values():
        if not re.fullmatch(re.escape(registry) + r'/[a-z0-9/-]+@sha256:[0-9a-f]{64}', image):
            raise reconcile.Refused('registry_policy')
    loader = reconcile._secret_loader
    root = loader.private_directory(str(config_root))
    stage = None
    try:
        loader.require_tmpfs(root)
        stage = Path(tempfile.mkdtemp(prefix='registry-', dir=config_root))
        credentials = reconcile.AttachedServiceAccount()
        credentials.preflight(SimpleNamespace(project_id=project,
            project_number=target.runtime['project_number']))
        token = base64.b64encode(('oauth2accesstoken:' + credentials.token).encode()).decode()
        auth = {'auths': {registry.split('/')[0]: {'auth': token}}}
        fd = os.open(stage / 'config.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(auth, stream)
        # Explicit host/config and bounded()'s clean environment exclude inherited
        # contexts, credential helpers, proxy variables and alternate daemons.
        prefix = [str(tool), '--config', str(stage), '--host', 'unix:///var/run/docker.sock']
        for role, image in images.items():
            target.unchanged()
            if reconcile.digest_file(tool) != docker_sha256:
                raise reconcile.Refused('docker_tool_pin')
            reconcile.bounded(prefix + ['image', 'pull', '--platform=linux/amd64', image], timeout=300)
            observed = reconcile.decode(reconcile.bounded(
                prefix + ['image', 'inspect', image], timeout=30))
            if (not isinstance(observed, list) or len(observed) != 1
                    or not isinstance(observed[0], dict)
                    or observed[0].get('Os') != 'linux'
                    or observed[0].get('Architecture') != 'amd64'
                    or image not in (observed[0].get('RepoDigests') or [])):
                raise reconcile.Refused('installed_image_identity')
        return {'images': images, 'containers_started': False}
    finally:
        if stage is not None:
            shutil.rmtree(stage)
        os.close(root)
