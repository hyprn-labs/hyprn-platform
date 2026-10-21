"""Exercise the pinned proxy with real TLS in an isolated, networkless container."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'host'))
import contract
import service_network

PROBE = r'''
import json, pathlib, socket, ssl, subprocess, threading, time
root = pathlib.Path('/probe')
config = json.loads((root / 'config.json').read_text())
listener = socket.socket()
listener.bind(('127.0.0.1', 0))
listener.listen(8)
listener.settimeout(10)
server_port = listener.getsockname()[1]
reservation = socket.socket()
reservation.bind(('127.0.0.1', 0))
proxy_port = reservation.getsockname()[1]
reservation.close()
config['static_resources']['listeners'][0]['address']['socket_address'] = {
    'address': '127.0.0.1', 'port_value': proxy_port}
for cluster in config['static_resources']['clusters']:
    endpoint = cluster['load_assignment']['endpoints'][0]['lb_endpoints'][0]['endpoint']
    endpoint['address']['socket_address'] = {'address': '127.0.0.1', 'port_value': server_port}
pathlib.Path('/tmp/config.json').write_text(json.dumps(config))
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(root / 'cert.pem', root / 'key.pem')
received = []
def server():
    try:
        conn, _ = listener.accept()
        with context.wrap_socket(conn, server_side=True) as stream:
            received.append(stream.recv(4096))
            stream.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK')
    finally:
        listener.close()
thread = threading.Thread(target=server, daemon=True)
thread.start()
process = subprocess.Popen([str(root / 'envoy'), '--config-path', '/tmp/config.json',
    '--concurrency', '1', '--log-level', 'error'], stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE)
try:
    until = time.monotonic() + 20
    while True:
        if process.poll() is not None:
            raise RuntimeError('proxy startup failed: ' + process.stderr.read().decode()[:2000])
        try:
            with socket.create_connection(('127.0.0.1', proxy_port), 1):
                break
        except OSError:
            if time.monotonic() >= until:
                raise
            time.sleep(.05)
    def request(line, host):
        conn = socket.create_connection(('127.0.0.1', proxy_port), 3)
        conn.settimeout(3)
        conn.sendall((line + '\r\nHost: ' + host + '\r\n\r\n').encode())
        header = b''
        while b'\r\n\r\n' not in header:
            part = conn.recv(1)
            if not part:
                break
            header += part
            assert len(header) < 8192
        return conn, int(header.split(b' ')[1])
    refused = []
    for target in ('example.com:443', 'api.anthropic.com:80', '169.254.169.254:443',
                   '127.0.0.1:443', 'api.anthropic.com.evil:443'):
        conn, code = request('CONNECT ' + target + ' HTTP/1.1', 'api.anthropic.com:443')
        conn.close()
        assert code in (400, 403, 404), (target, code)
        refused.append(target)
    conn, code = request('GET http://api.anthropic.com/ HTTP/1.1', 'api.anthropic.com:443')
    conn.close()
    assert code in (400, 403, 404), code
    conn, code = request('CONNECT api.anthropic.com:443 HTTP/1.1', 'api.anthropic.com:443')
    assert code == 200, code
    client = ssl.create_default_context(cafile=str(root / 'cert.pem'))
    with client.wrap_socket(conn, server_hostname='api.anthropic.com') as secure:
        secure.sendall(b'GET /probe HTTP/1.1\r\nHost: api.anthropic.com\r\n\r\n')
        assert secure.recv(4096).endswith(b'OK')
    thread.join(timeout=5)
    assert received and b'/probe' in received[0]
    print(json.dumps({'tls_verified': True, 'negative_connects': len(refused),
                      'plain_http_denied': True, 'production_network_qualified': False}))
finally:
    process.terminate()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)
'''


class ServiceNetworkLiveTests(unittest.TestCase):
    def test_real_proxy_preserves_tls_and_refuses_unapproved_connect_authorities(self):
        binary = os.environ.get('HYPRN_TEST_ENVOY_BINARY')
        image = os.environ.get('HYPRN_TEST_PROXY_IMAGE')
        self.assertTrue(binary and image, 'Explicit scratch proxy binary and local image are required')
        self.assertRegex(image, r'^sha256:[0-9a-f]{64}$')
        pins = json.loads((ROOT / 'host/egress-proxy.json').read_text())
        self.assertEqual(hashlib.sha256(Path(binary).read_bytes()).hexdigest(), pins['sha256'])
        with tempfile.TemporaryDirectory(prefix='hyprn-proxy-live-') as directory:
            scope = Path(directory)
            shutil.copyfile(binary, scope / 'envoy')
            (scope / 'envoy').chmod(0o555)
            runtime = json.loads((ROOT / 'contracts/v1/fixtures.json').read_text())['valid']['runtime']
            config = service_network.proxy_config(contract.network_policy(runtime))
            (scope / 'config.json').write_text(json.dumps(config))
            (scope / 'probe.py').write_text(PROBE)
            certificate = subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                '-nodes', '-days', '1', '-subj', '/CN=api.anthropic.com',
                '-addext', 'subjectAltName=DNS:api.anthropic.com',
                '-keyout', str(scope / 'key.pem'), '-out', str(scope / 'cert.pem')],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(certificate.returncode, 0, certificate.stderr)
            result = subprocess.run(['docker', 'run', '--rm', '--platform', 'linux/amd64',
                '--network', 'none', '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev,size=67108864',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--user', f'{os.getuid()}:{os.getgid()}', '--memory', '256m', '--cpus', '1',
                '--pids-limit', '64', '--mount', f'type=bind,src={scope},dst=/probe,readonly',
                '--entrypoint', 'python', image, '-B', '/probe/probe.py'],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report['tls_verified'])
            self.assertEqual(report['negative_connects'], 5)
            self.assertTrue(report['plain_http_denied'])
            self.assertFalse(report['production_network_qualified'])
