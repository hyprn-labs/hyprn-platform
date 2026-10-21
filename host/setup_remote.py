"""Apply one reviewed host setup over IAP, then confirm the same VM is stopped."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tarfile
import time

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup


# Executed with OS Login sudo after the operator uploaded the approved archive.
# Hash before extraction; create a new root-owned tree, never replace an old one.
INSTALLER = r'''
import hashlib,io,json,os,pathlib,stat,subprocess,sys,tarfile
source,sha,plan_sha,expected_json=sys.argv[1:]
expected=set(json.loads(expected_json));source=pathlib.Path(source)
fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW)
with os.fdopen(fd,'rb') as f: raw=f.read(200*1024*1024+1)
assert len(raw)<=200*1024*1024 and hashlib.sha256(raw).hexdigest()==sha
base=pathlib.Path('/opt/hyprn/host-setup')
for p in (pathlib.Path('/opt'),pathlib.Path('/opt/hyprn'),base):
 if not p.exists():p.mkdir(mode=0o755)
 s=p.lstat();assert stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022
root=base/sha
existing=root.exists()
if not existing:root.mkdir(mode=0o755)
s=root.lstat();assert stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as a:
 members=a.getmembers();assert len(members)==len(expected) and {m.name for m in members}==expected
 assert sum(m.size for m in members)<=250*1024*1024
 if existing:
  entries=list(root.rglob('*'))
  assert all(not p.is_symlink() and p.lstat().st_uid==0 and not p.lstat().st_mode&0o022 for p in entries)
  assert {str(p.relative_to(root)) for p in entries if p.is_file()}==expected
 for m in members:
  p=pathlib.PurePosixPath(m.name)
  assert m.isfile() and not p.is_absolute() and '..' not in p.parts and len(p.parts)<=2
  dest=root/m.name
  if not dest.parent.exists():dest.parent.mkdir(mode=0o755)
  if existing:
   info=dest.lstat();assert stat.S_ISREG(info.st_mode) and info.st_uid==0 and info.st_nlink==1 and not info.st_mode&0o022
   assert dest.read_bytes()==a.extractfile(m).read()
   continue
  out=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o444)
  with os.fdopen(out,'wb') as f:
   payload=a.extractfile(m)
   for chunk in iter(lambda:payload.read(1024*1024),b''):f.write(chunk)
   f.flush();os.fsync(f.fileno())
result=subprocess.run(['/usr/bin/python3','-I','-B',str(root/'platform/setup.py'),
 'apply','--policy',str(root/'policy.json'),'--packages',str(root/'packages'),
 '--approve-sha256',plan_sha],env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C'},timeout=900)
sys.exit(result.returncode)
'''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def reviewed(bundle, review):
    fields = {'schema', 'plan_sha256', 'bundle_sha256', 'controller_sha256', 'source_commit'}
    if 'keep_running' in review:
        fields.add('keep_running')
    if set(review) != fields or type(review.get('keep_running', False)) is not bool:
        raise ValueError('review_fields')
    if (review['schema'] != 'hyprn-host-setup-deployment/v1'
            or review['controller_sha256'] != digest(Path(__file__).read_bytes())):
        raise ValueError('review_controller_pin')
    raw = Path(bundle).read_bytes()
    if len(raw) > 200 * 1024**2 or digest(raw) != review['bundle_sha256']:
        raise ValueError('review_bundle_pin')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        if (len(members) > 32 or any(not m.isfile() for m in members)
                or len({m.name for m in members}) != len(members)):
            raise ValueError('review_bundle_members')
        plan = json.load(archive.extractfile('plan.json'))
        policy = setup.validate(json.load(archive.extractfile('policy.json')))
        if (plan['plan_sha256'] != review['plan_sha256'] or plan['policy'] != policy
                or setup.digest(setup.canonical({k: v for k, v in plan.items() if k != 'plan_sha256'})) != review['plan_sha256']):
            raise ValueError('review_plan_pin')
        expected = {'plan.json', 'policy.json'} | {'platform/' + name for name in plan['sources']} | {
            'packages/' + row['filename'] for row in plan['packages']}
        if review.get('keep_running', False) != (plan.get('host_final_state') == 'RUNNING'):
            raise ValueError('review_host_final_state')
        sources = {'setup.py', 'reconcile.py', 'secrets.py', 'contract.py', 'host-packages.json', 'preflight.py'}
        if plan.get('schema') == 'hyprn-host-setup-repair/v1':
            sources |= {'repair_setup.py', 'base-plan.json'}
        elif plan.get('schema') == 'hyprn-host-setup-finalize/v1':
            sources |= {'finalize_setup.py', 'repair-plan.json'}
        elif plan.get('schema') != 'hyprn-host-setup-plan/v1':
            raise ValueError('review_plan_schema')
        if (set(plan['sources']) != sources
                or any(PurePosixPath(m.name).is_absolute() or '..' in PurePosixPath(m.name).parts for m in members)):
            raise ValueError('review_source_inventory')
        if {m.name for m in members} != expected:
            raise ValueError('review_bundle_inventory')
        for name, sha in plan['sources'].items():
            if digest(archive.extractfile('platform/' + name).read()) != sha:
                raise ValueError('review_source_pin')
        for row in plan['packages']:
            member = archive.getmember('packages/' + row['filename'])
            if member.size != row['size'] or digest(archive.extractfile(member).read()) != row['sha256']:
                raise ValueError('review_package_pin')
    return policy, sorted(expected)


class Operator:
    def __init__(self, config, evidence, policy):
        self.root = Path(evidence)
        self.root.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.policy = policy
        self.env = {key: value for key, value in os.environ.items() if key in ('PATH', 'HOME', 'LANG')}
        self.env.update(CLOUDSDK_CONFIG=str(Path(config).resolve()), CLOUDSDK_CORE_DISABLE_FILE_LOGGING='true',
            CLOUDSDK_CORE_LOG_HTTP='false', CLOUDSDK_CORE_DISABLE_USAGE_REPORTING='true',
            CLOUDSDK_CORE_DISABLE_PROMPTS='true')
        self.base = ['gcloud', '--quiet', '--project=' + policy['project_id'], '--verbosity=error']
        self.ssh = ['compute', 'ssh', policy['host_id'], '--zone=' + policy['zone'], '--tunnel-through-iap',
            '--ssh-key-file=' + str(self.root / 'operator-key'), '--ssh-key-expire-after=30m',
            '--ssh-flag=-oStrictHostKeyChecking=accept-new',
            '--ssh-flag=-oUserKnownHostsFile=' + str(self.root / 'known-hosts')]

    def record(self, name, value):
        (self.root / name).write_text(json.dumps(value, indent=2) + '\n')
        (self.root / name).chmod(0o600)

    def call(self, args, *, timeout=180):
        result = subprocess.run(self.base + args, env=self.env, capture_output=True, timeout=timeout)
        if result.returncode:
            (self.root / 'last-error.log').write_bytes(result.stdout[-65536:] + result.stderr[-65536:])
            (self.root / 'last-error.log').chmod(0o600)
            raise RuntimeError('operation_refused_private_log_retained')
        return result.stdout

    def observe(self, *, startup=True):
        p = self.policy
        value = json.loads(self.call(['compute', 'instances', 'describe', p['host_id'], '--zone=' + p['zone'], '--format=json']))
        link = 'https://www.googleapis.com/compute/v1/projects/' + p['project_id'] + '/zones/' + p['zone'] + '/instances/' + p['host_id']
        metadata = {x['key']: x['value'] for x in value.get('metadata', {}).get('items', [])}
        if value.get('selfLink') != link or value.get('id') != p['instance_id']:
            raise RuntimeError('unexpected_instance_identity')
        if startup and (any(n.get('accessConfigs') for n in value.get('networkInterfaces', []))
                or value.get('serviceAccounts', [{}])[0].get('email') !=
                   'hyprn-staging-runtime@' + p['project_id'] + '.iam.gserviceaccount.com'
                or metadata != {'enable-oslogin': 'TRUE', 'block-project-ssh-keys': 'TRUE'}):
            raise RuntimeError('unexpected_instance_identity_or_startup_configuration')
        return value

    def apply(self, bundle, review, expected):
        p = self.policy
        before = self.observe()
        keep_running = review.get('keep_running', False)
        if before['status'] != 'TERMINATED' and not (keep_running and before['status'] == 'RUNNING'):
            raise RuntimeError('host_not_stopped')
        self.record('intent.json', dict(review, instance_id=p['instance_id']))
        completed = False
        try:
            if before['status'] == 'TERMINATED':
                self.call(['compute', 'instances', 'start', p['host_id'], '--zone=' + p['zone']], timeout=600)
            for attempt in range(6):
                if self.observe()['status'] != 'RUNNING':
                    raise RuntimeError('host_left_running')
                try:
                    self.call(self.ssh + ['--command=/usr/bin/true'], timeout=60)
                    break
                except (RuntimeError, subprocess.TimeoutExpired):
                    if attempt == 5:
                        raise
                    time.sleep(20)
            remote = '/var/tmp/hyprn-host-setup-' + review['bundle_sha256'][:20]
            self.call(self.ssh + ['--command=umask 077 && mkdir ' + shlex.quote(remote)])
            self.call(['compute', 'scp', str(Path(bundle).resolve()), p['host_id'] + ':' + remote + '/bundle.tar.gz',
                '--zone=' + p['zone'], '--tunnel-through-iap', '--ssh-key-file=' + str(self.root / 'operator-key'),
                '--ssh-key-expire-after=30m', '--scp-flag=-oStrictHostKeyChecking=yes',
                '--scp-flag=-oUserKnownHostsFile=' + str(self.root / 'known-hosts')], timeout=600)
            entrypoint = ('finalize_setup.py' if 'platform/finalize_setup.py' in expected else
                          'repair_setup.py' if 'platform/repair_setup.py' in expected else 'setup.py')
            installer = INSTALLER.replace('platform/setup.py', 'platform/' + entrypoint)
            arguments = ['sudo', '-n', '/usr/bin/python3', '-I', '-B', '-c', installer,
                         remote + '/bundle.tar.gz', review['bundle_sha256'], review['plan_sha256'], json.dumps(expected)]
            raw = self.call(self.ssh + ['--command=' + shlex.join(arguments)], timeout=960)
            receipt = json.loads(raw)
            if (receipt.get('plan_sha256') != review['plan_sha256'] or receipt.get('admission') != 'closed'
                    or receipt.get('product_started') is not False):
                raise RuntimeError('setup_receipt_differs')
            self.record('host-result.json', receipt)
            completed = True
        finally:
            current = self.observe(startup=False)
            if not keep_running and current['status'] != 'TERMINATED':
                self.call(['compute', 'instances', 'stop', p['host_id'], '--zone=' + p['zone']], timeout=600)
            final = self.observe(startup=False)
            wanted = 'RUNNING' if keep_running else 'TERMINATED'
            if final['status'] != wanted:
                raise RuntimeError('host_final_state_not_confirmed')
            self.record('result.json', dict(setup_completed=completed, vm_status=final['status'],
                        instance_id=p['instance_id'], product_started=False))
        return dict(setup_completed=completed, vm_status=final['status'], product_started=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--review', required=True)
    p.add_argument('--bundle', required=True)
    p.add_argument('--gcloud-config', required=True)
    p.add_argument('--evidence', required=True)
    p.add_argument('--approve-plan', required=True)
    a = p.parse_args()
    os.umask(0o077)
    review = json.loads(Path(a.review).read_bytes())
    policy, expected = reviewed(a.bundle, review)
    if a.approve_plan != review['plan_sha256']:
        raise ValueError('explicit_approval_required')
    print(json.dumps(Operator(a.gcloud_config, a.evidence, policy).apply(a.bundle, review, expected)))


if __name__ == '__main__':
    main()
