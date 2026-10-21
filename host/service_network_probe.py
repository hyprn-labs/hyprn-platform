"""Observe approved and forbidden paths from the installed service containers.

The probe sends no credentials and launches no model or provider conversation.
It must run after closed application startup, before opening browser admission.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activation
import service_network_install

PYTHON = r'''
import http.client,json,socket,ssl,struct,sys
role,db,server,issuer,ca=sys.argv[1:]
checks={}
def reachable(host,port):
 try:
  with socket.create_connection((host,port),timeout=3): return True
 except OSError: return False
checks['modeling_route']=reachable('172.29.82.3',3000)
with socket.create_connection((db,5432),timeout=5) as stream:
 stream.sendall(struct.pack('!II',8,80877103))
 if stream.recv(1)!=b'S': raise RuntimeError('database_requires_tls')
 with ssl.create_default_context(cafile=ca).wrap_socket(stream,server_hostname=server) as secured:
  checks['database_verified_tls']=bool(secured.getpeercert())
checks['metadata_denied']=not reachable('169.254.169.254',80)
checks['direct_public_https_denied']=not reachable('1.1.1.1',443)
if role=='app':
 for name,path,expected in ((issuer,'/cdn-cgi/access/certs',200),('api.anthropic.com','/v1/sessions',401)):
  c=http.client.HTTPSConnection('172.29.81.1',3128,context=ssl.create_default_context(),timeout=15)
  c.set_tunnel(name,443)
  try:
   c.request('GET',path,headers={'anthropic-version':'2023-06-01','anthropic-beta':'managed-agents-2026-04-01'})
   r=c.getresponse();r.read(65537)
   checks['tls_proxy_'+name]=r.status==expected
  finally:c.close()
 for host,port in (('example.com',443),('169.254.169.254',80),(issuer,8443)):
  c=http.client.HTTPConnection('172.29.81.1',3128,timeout=5)
  try:
   c.request('CONNECT',host+':'+str(port));r=c.getresponse();r.read(65537)
   checks['proxy_denied_'+host+'_'+str(port)]=r.status in (400,403,404)
  finally:c.close()
else:
 checks['proxy_denied']=not reachable('172.29.81.1',3128)
print(json.dumps(checks,sort_keys=True))
'''
RUBY = r'''
require 'socket'; require 'json'
checks={}
[['metadata','169.254.169.254',80],['database',ARGV[0],5432],['app','172.29.82.2',8000],['public_https','1.1.1.1',443],['proxy','172.29.81.1',3128]].each do |name,host,port|
 begin
  Socket.tcp(host,port,connect_timeout:3) {|s| s.close}; checks[name+'_denied']=false
 rescue SystemCallError, IOError
  checks[name+'_denied']=true
 end
end
puts JSON.generate(checks)
'''


def verify(binding, network_policy):
    service_network_install.require_root()
    target = activation.reconcile.Target(binding)
    target.protect()
    policy = activation.contract.read_json(activation.reconcile.protected(network_policy))
    if (policy['installation_id'] != target.runtime['installation_id']
            or policy['network'] != target.preview['network_policy']):
        raise activation.Refused('network_probe_target_changed')
    before = service_network_install.verify_live(policy)
    containers = activation.containers(target)
    result = {}
    db = target.runtime['database']
    for role in ('app', 'dispatcher'):
        command = ['/usr/bin/docker', '--host', 'unix:///run/docker.sock', 'exec',
            containers[role], 'python', '-I', '-B', '-c', PYTHON, role, db['host'],
            target.preview['compose']['services'][role]['environment']['HYPRN_MVP_DATABASE_TLS_SERVER_NAME'],
            target.runtime['access']['issuer'].removeprefix('https://'),
            '/run/hyprn/control/database-ca.pem']
        # Take the actual rendered CA path, rather than assuming a product mount.
        command[-1] = target.preview['compose']['services'][role]['environment']['HYPRN_MVP_DATABASE_CA_FILE']
        result[role] = activation.reconcile.decode(activation.command(command, timeout=75))
    result['modeling'] = activation.reconcile.decode(activation.command([
        '/usr/bin/docker', '--host', 'unix:///run/docker.sock', 'exec',
        containers['modeling'], 'ruby', '-e', RUBY, db['host']], timeout=30))
    expected = {
        'app': {'modeling_route', 'database_verified_tls', 'metadata_denied',
                'direct_public_https_denied', 'tls_proxy_'+target.runtime['access']['issuer'].removeprefix('https://'),
                'tls_proxy_api.anthropic.com', 'proxy_denied_example.com_443',
                'proxy_denied_169.254.169.254_80',
                'proxy_denied_'+target.runtime['access']['issuer'].removeprefix('https://')+'_8443'},
        'dispatcher': {'modeling_route','database_verified_tls','metadata_denied',
                       'direct_public_https_denied','proxy_denied'},
        'modeling': {'metadata_denied','database_denied','app_denied','public_https_denied','proxy_denied'}}
    if any(set(result[role]) != keys or any(v is not True for v in result[role].values())
           for role,keys in expected.items()):
        raise activation.Refused('network_probe_path_failed')
    after = service_network_install.verify_live(policy)
    target.unchanged()
    if before != after or containers != activation.containers(target):
        raise activation.Refused('network_probe_state_changed')
    return {'schema':'hyprn-service-network-probe/v1','identity':target.identity,
            'observations':result,'model_executions':0,'provider_messages':0}


def main():
    p=argparse.ArgumentParser();p.add_argument('--binding',required=True);p.add_argument('--network-policy',required=True)
    a=p.parse_args()
    try:
        print(json.dumps(verify(a.binding,a.network_policy),sort_keys=True));return 0
    except (activation.Refused,ValueError,OSError,KeyError):
        print(json.dumps({'error':'network_probe_refused'}));return 2

if __name__=='__main__':
    raise SystemExit(main())
