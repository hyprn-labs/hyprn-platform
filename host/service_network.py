"""Render restricted host routing and CONNECT proxy from validated runtime data.

This module has no apply operation. Its files must be installed by a reviewed
host operation; rendering does not establish that packet filtering is active.
"""
import ipaddress
import json
from pathlib import Path
import re

import contract

PROXY_UID = 10005
# Public HTTPS only. Deny special-use IPv4 even if an approved hostname changes
# to such an address; DNS and response traffic have narrowly scoped exceptions.
NON_PUBLIC = ('0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8',
              '169.254.0.0/16', '172.16.0.0/12', '192.0.0.0/24',
              '192.0.2.0/24', '192.168.0.0/16', '198.18.0.0/15',
              '198.51.100.0/24', '203.0.113.0/24', '224.0.0.0/4', '240.0.0.0/4')


def checked(policy):
    """Accept only the platform's current topology and two exact public names."""
    try:
        hosts = policy['proxy']['hosts']
        database = policy['database']['address']
        if (not isinstance(hosts, list) or len(hosts) != 2
                or hosts[0] != 'api.anthropic.com'
                or not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.cloudflareaccess\.com', hosts[1])):
            raise ValueError()
        address = ipaddress.ip_address(database)
        if address.version != 4 or not any(address in ipaddress.ip_network(cidr)
                for cidr in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
            raise ValueError()
        if any(address in ipaddress.ip_network(row['ipam']['config'][0]['subnet'])
                for row in contract.container_networks().values()):
            raise ValueError()
        expected = contract.network_policy({'database': {'host': database},
                                           'access': {'issuer': 'https://' + hosts[1]}})
        if policy != expected:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ValueError('invalid_service_network_policy') from None
    return policy


def proxy_config(policy):
    """Two named static destinations; no dynamic forward proxy or admin port."""
    policy = checked(policy)
    virtual_hosts, clusters = [], []
    for index, host in enumerate(policy['proxy']['hosts']):
        name = 'allowed_' + str(index)
        virtual_hosts.append({'name': name, 'domains': [host + ':443'], 'routes': [{
            'match': {'connect_matcher': {}}, 'route': {'cluster': name,
                'timeout': '0s', 'upgrade_configs': [
                    {'upgrade_type': 'CONNECT', 'connect_config': {}}]}}]})
        clusters.append({'name': name, 'type': 'LOGICAL_DNS', 'connect_timeout': '5s',
            'dns_lookup_family': 'V4_ONLY', 'dns_refresh_rate': '60s',
            'load_assignment': {'cluster_name': name, 'endpoints': [{'lb_endpoints': [
                {'endpoint': {'address': {'socket_address': {
                    'address': host, 'port_value': 443}}}}]}]}})
    manager = {
        '@type': 'type.googleapis.com/envoy.extensions.filters.network.'
                 'http_connection_manager.v3.HttpConnectionManager',
        'stat_prefix': 'hyprn_egress', 'codec_type': 'HTTP1',
        'request_headers_timeout': '10s', 'stream_idle_timeout': '300s',
        'max_request_headers_kb': 16,
        'route_config': {'name': 'approved_connect', 'virtual_hosts': virtual_hosts},
        'http_filters': [{'name': 'envoy.filters.http.router', 'typed_config': {
            '@type': 'type.googleapis.com/envoy.extensions.filters.http.router.v3.Router'}}],
    }
    return {'static_resources': {'listeners': [{'name': 'application_only',
        'address': {'socket_address': {'address': policy['proxy']['address'], 'port_value': 3128}},
        'per_connection_buffer_limit_bytes': 65536,
        'filter_chains': [{'filters': [{'name': 'envoy.filters.network.http_connection_manager',
                                      'typed_config': manager}]}]}], 'clusters': clusters}}


def filter_rules(policy):
    """Rules for dedicated chains; never flush unrelated host tables or chains."""
    policy = checked(policy)
    bridges = {name: row['driver_opts']['com.docker.network.bridge.name']
               for name, row in policy['bridges'].items()}
    forward = [['-d', '169.254.169.254/32', '-j', 'DROP']]

    def connection(source, destination, port, incoming, outgoing=None):
        common = ['-i', incoming] + (['-o', outgoing] if outgoing else [])
        forward.append(common + ['-s', source, '-d', destination, '-p', 'tcp',
            '--dport', str(port), '-m', 'conntrack', '--ctstate', 'NEW,ESTABLISHED', '-j', 'RETURN'])
        common = (['-i', outgoing] if outgoing else []) + ['-o', incoming]
        forward.append(common + ['-s', destination, '-d', source, '-p', 'tcp',
            '--sport', str(port), '-m', 'conntrack', '--ctstate', 'ESTABLISHED', '-j', 'RETURN'])

    for source in ('172.29.82.2/32', '172.29.82.4/32'):
        connection(source, '172.29.82.3/32', 3000, bridges['modeling'], bridges['modeling'])
    # The one-off migration container is on the application bridge with a dynamic
    # address. That bridge receives only SQL forwarding; HTTPS remains app-IP only.
    connection('172.29.81.0/24', policy['database']['address'] + '/32', 5432,
               bridges['application'])
    connection('172.29.83.2/32', policy['database']['address'] + '/32', 5432,
               bridges['dispatcher'])
    forward.append(['-j', 'DROP'])
    incoming = [
        ['-i', bridges['application'], '-s', '172.29.81.2/32', '-d', '172.29.81.1/32',
         '-p', 'tcp', '--dport', '3128', '-j', 'ACCEPT'],
    ]
    for bridge, source in ((bridges['application'], '172.29.81.2/32'),
                           (bridges['modeling'], '172.29.82.2/32')):
        incoming.append(['-i', bridge, '-s', source, '-p', 'tcp', '--sport', '8000',
                         '-m', 'conntrack', '--ctstate', 'ESTABLISHED', '-j', 'ACCEPT'])
    incoming += [['-i', 'docker0', '-j', 'DROP'], ['-i', 'br+', '-j', 'DROP'], ['-j', 'RETURN']]
    proxy_output = [['-d', '172.29.81.2/32', '-p', 'tcp', '--sport', '3128',
                     '-m', 'conntrack', '--ctstate', 'ESTABLISHED', '-j', 'RETURN']]
    for protocol in ('udp', 'tcp'):
        proxy_output.append(['-d', '127.0.0.53/32', '-p', protocol, '--dport', '53', '-j', 'RETURN'])
    proxy_output += [['-d', network, '-j', 'REJECT'] for network in NON_PUBLIC]
    proxy_output += [['-p', 'tcp', '--dport', '443', '-j', 'RETURN'], ['-j', 'REJECT']]
    return {'DOCKER-USER': forward, 'HYPRN-SERVICE-IN': incoming,
            'HYPRN-PROXY-OUT': proxy_output}


def proxy_unit():
    pin = json.loads(Path(__file__).with_name('egress-proxy.json').read_text())
    binary = '/opt/hyprn/egress/' + pin['sha256'] + '/envoy'
    return f'''[Unit]
Description=HYPRN restricted application HTTPS proxy
Requires=docker.service hyprn-service-network.service
After=docker.service hyprn-service-network.service systemd-resolved.service
BindsTo=hyprn-service-network.service

[Service]
Type=simple
User={PROXY_UID}
Group={PROXY_UID}
ExecStart={binary} --config-path /etc/hyprn/egress.json --concurrency 1 --log-level error
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictAddressFamilies=AF_INET AF_UNIX
LockPersonality=true
RestrictRealtime=true
MemoryMax=256M
CPUQuota=100%
TasksMax=32
LimitCORE=0
UMask=0077
StandardOutput=journal
StandardError=journal
LogRateLimitIntervalSec=30s
LogRateLimitBurst=30

[Install]
WantedBy=multi-user.target
'''


def plan(policy):
    policy = checked(policy)
    return {'schema': 'hyprn-service-network-plan/v1', 'policy': policy,
            'proxy_uid': PROXY_UID, 'proxy': proxy_config(policy),
            'filter_chains': filter_rules(policy),
            'required_jumps': {
                'FORWARD': ['-j', 'DOCKER-USER'],
                'INPUT': ['-j', 'HYPRN-SERVICE-IN'],
                'OUTPUT': ['-m', 'owner', '--uid-owner', str(PROXY_UID),
                           '-j', 'HYPRN-PROXY-OUT']},
            'proxy_systemd_unit': proxy_unit(),
            'admission': 'closed', 'applied': False}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Preview restricted host service networking')
    parser.add_argument('--policy', required=True)
    args = parser.parse_args()
    try:
        result = plan(contract.read_json(Path(args.policy)))
    except (ValueError, OSError, contract.Invalid):
        print(json.dumps({'error': 'invalid_service_network_policy'}))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
