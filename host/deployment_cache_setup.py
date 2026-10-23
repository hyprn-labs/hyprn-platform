"""Install a reviewed immutable delivery-cache policy and bounded periodic maintenance."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

_spec = importlib.util.spec_from_file_location('cache_lifecycle',
    Path(__file__).with_name('deployment_archive_lifecycle.py'))
lifecycle = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(lifecycle)
cleanup, stage, Refused = lifecycle.cleanup, lifecycle.stage, lifecycle.Refused
ROOT = Path('/opt/hyprn/deployment-cache')
UNITS = Path('/etc/systemd/system')
RECORD = Path('/etc/hyprn/deployment-cache-install.json')
SOURCES = ('deployment_cache_setup.py', 'deployment_archive_lifecycle.py',
           'deployment_archive_cleanup.py', 'release_stage.py', 'contract.py',
           'reconcile.py', 'secrets.py')


def plan(policy, previous=None):
    lifecycle.validate(policy)
    if previous is not None and not cleanup.SHA.fullmatch(previous):
        raise Refused('previous_installation_hash')
    sources = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
               for name in SOURCES}
    identity = stage.digest(dict(policy=policy, sources=sources))
    path = ROOT / identity
    command = (f'/usr/bin/python3 -I -B {path}/deployment_archive_cleanup.py maintain '
               f'--policy {path}/policy.json --approve-sha256 {stage.digest(policy)}')
    units = {'hyprn-deployment-cache.service': f'''[Unit]
Description=Maintain verified HYPRN deployment transfer cache
After=network-online.target
Wants=network-online.target
RequiresMountsFor={stage.DATA_ROOT}

[Service]
Type=oneshot
ExecStart={command}
TimeoutStartSec={policy['max_seconds'] + 90}
Nice=10
IOSchedulingClass=idle
CPUQuota=25%
MemoryMax=256M
TasksMax=16
UMask=0077
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=-{stage.DEPLOYMENT_ROOT} -{stage.DATA_DEPLOYMENT_ROOT} {cleanup.JOURNAL}
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
LimitCORE=0
StandardOutput=journal
StandardError=journal
''', 'hyprn-deployment-cache.timer': '''[Unit]
Description=Bound HYPRN deployment transfer storage

[Timer]
OnBootSec=15min
OnUnitActiveSec=1h
RandomizedDelaySec=5min
Unit=hyprn-deployment-cache.service

[Install]
WantedBy=timers.target
'''}
    value = dict(schema='hyprn-deployment-cache-install/v1', policy=policy,
        policy_sha256=stage.digest(policy), source_sha256=sources, snapshot=str(path),
        previous_plan_sha256=previous, units=units,
        actions=['install-immutable-policy-and-code', 'install-owned-service-and-timer',
                 'reload-systemd', 'enable-timer'], product_records_changed=False)
    return dict(value, plan_sha256=stage.digest(value))


def read_optional(path):
    try:
        return cleanup.read_document(str(path))
    except FileNotFoundError:
        return None


def read_bytes(path):
    parent = stage.directory(str(path.parent))
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not cleanup.stat.S_ISREG(info.st_mode) or info.st_uid != stage.OWNER
                    or info.st_nlink != 1 or info.st_mode & 0o022
                    or info.st_size > stage.MAX_MANIFEST):
                raise Refused('setup_file_authority')
            return stream.read(stage.MAX_MANIFEST + 1)
    except FileNotFoundError:
        return None
    finally:
        os.close(parent)


def write(path, raw, *, replace=False):
    parent = stage.directory(str(path.parent), create=True)
    temporary = '.cache-' + hashlib.sha256(raw).hexdigest()
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); os.fchmod(stream.fileno(), 0o644)
            stream.flush(); os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        else:
            os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent,
                    follow_symlinks=False)
            os.unlink(temporary, dir_fd=parent)
        os.fsync(parent)
    finally:
        os.close(parent)


def _apply(policy, approved, previous=None, *, host=None, systemctl=None):
    value = plan(policy, previous)
    if approved != value['plan_sha256'] or os.geteuid() != stage.OWNER:
        raise Refused('setup_approval_or_privilege')
    host = host or stage.AttachedHost(); host.verify(policy['identity'])
    stage.mounted_data()
    systemctl = systemctl or (lambda args: subprocess.run(
        ['/usr/bin/systemctl', *args], check=True, timeout=45, capture_output=True))
    # A schedule replacement is restricted to the exact previously installed policy.
    previous_record = read_optional(RECORD)
    if previous_record is not None and previous_record.get('plan_sha256') not in (
            previous, value['plan_sha256']):
        raise Refused('setup_existing_policy')
    if previous_record is None and previous is not None:
        raise Refused('setup_previous_policy_missing')
    for name, text in value['units'].items():
        existing = read_bytes(UNITS / name)
        old = (previous_record or {}).get('units', {}).get(name)
        allowed = [text.encode()] + ([old.encode()] if isinstance(old, str) else [])
        if existing is not None and existing not in allowed:
            raise Refused('setup_unit_changed')
    source_bytes = {}
    for name, expected in value['source_sha256'].items():
        raw = read_bytes(Path(__file__).with_name(name))
        if raw is None or hashlib.sha256(raw).hexdigest() != expected:
            raise Refused('setup_source_changed')
        source_bytes[name] = raw
    snapshot = Path(value['snapshot'])
    fd = stage.directory(str(snapshot), create=True); os.close(fd)
    for name, raw in {**source_bytes, 'policy.json': stage.canonical(policy)}.items():
        target = snapshot / name; existing = read_bytes(target)
        if existing is not None and existing != raw:
            raise Refused('setup_snapshot_changed')
        if existing is None:
            write(target, raw)
    for name, text in value['units'].items():
        target = UNITS / name
        if read_bytes(target) != text.encode():
            write(target, text.encode(), replace=read_bytes(target) is not None)
    # Record before systemd activation so an interrupted activation is repeatable.
    if previous_record != value:
        write(RECORD, stage.canonical(value), replace=previous_record is not None)
    systemctl(['daemon-reload'])
    systemctl(['enable', '--now', 'hyprn-deployment-cache.timer'])
    systemctl(['is-active', '--quiet', 'hyprn-deployment-cache.timer'])
    return dict(plan_sha256=value['plan_sha256'], timer='active',
                cleanup_started=False, product_records_changed=False)


def apply(policy, approved, previous=None, *, host=None, systemctl=None):
    if os.geteuid() != stage.OWNER or approved != plan(policy, previous)['plan_sha256']:
        raise Refused('setup_approval_or_privilege')
    with cleanup.reconcile.Journal(cleanup.JOURNAL).lock():
        return _apply(policy, approved, previous, host=host, systemctl=systemctl)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'apply'))
    parser.add_argument('--policy', required=True)
    parser.add_argument('--approve-sha256')
    parser.add_argument('--previous-plan-sha256')
    args = parser.parse_args()
    try:
        policy = json.loads(Path(args.policy).read_bytes()) if args.operation == 'plan' else cleanup.read_document(args.policy)
        value = plan(policy, args.previous_plan_sha256) if args.operation == 'plan' else apply(
            policy, args.approve_sha256, args.previous_plan_sha256)
        print(json.dumps(value, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, cleanup.reconcile.Refused) as error:
        print(json.dumps({'refused': str(error) if isinstance(error, (Refused, cleanup.reconcile.Refused)) else 'cache_setup_failed'})); raise SystemExit(2)


if __name__ == '__main__':
    main()
