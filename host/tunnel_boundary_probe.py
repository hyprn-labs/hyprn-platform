"""Nonsecret connector boundary probe; executable without private deployment access."""
import json
import os
from pathlib import Path
import socket
import sys


def boundary_probe():
    # This process runs in the same IP-filtered cgroup slice and 10006 as cloudflared.
    if os.getuid() != 10006 or '/hyprn-tunnel.slice/' not in Path('/proc/self/cgroup').read_text():
        raise RuntimeError('tunnel_probe_scope')
    try:
        with socket.create_connection(('127.0.0.1', 8080), timeout=3):
            pass
    except OSError:
        raise RuntimeError('tunnel_origin_unreachable') from None
    try:
        connection = socket.create_connection(('169.254.169.254', 80), timeout=3)
    except OSError as error:
        import errno
        if error.errno not in (errno.EPERM, errno.EACCES, errno.ETIMEDOUT) and not isinstance(error, TimeoutError):
            raise RuntimeError('tunnel_metadata_denial_unproven') from None
    else:
        connection.close()
        raise RuntimeError('tunnel_metadata_reachable')
    return {'metadata': 'blocked-from-connector-slice', 'loopback_origin': 'reachable'}



if __name__ == '__main__':
    try:
        print(json.dumps(boundary_probe()))
    except RuntimeError as error:
        print(json.dumps({'status': 'refused', 'reason': str(error)}), file=sys.stderr)
        sys.exit(2)
