"""Approved operator-only Cloud SQL bootstrap and database-secret publication.

Never run on the application host. The dedicated operator CLI supplies an OAuth
access token in memory; REST bodies carry credentials, never arguments or logs.
"""
import argparse
import base64
import fcntl
import hashlib
import hmac
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess
from urllib.parse import urlencode

from contract import Invalid, canonical, digest, read_json
import database_setup as database

SERVICE_ALIASES = ('modeling-auth', 'modeling-rails', 'cloudflare-tunnel')
ALIASES = tuple(database.ROLES) + SERVICE_ALIASES

POLICY_FIELDS = {'schema', 'database', 'database_plan_sha256', 'project_number',
                 'operator_account', 'gcloud', 'gcloud_sha256', 'gcloud_config'}


def helper():
    spec = importlib.util.spec_from_file_location('hyprn_operator_secrets',
                                                Path(__file__).with_name('secrets.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def plan(policy):
    if not isinstance(policy, dict) or set(policy) != POLICY_FIELDS:
        raise Invalid('database_operator_policy_shape')
    if policy['schema'] != 'hyprn-database-operator/v1':
        raise Invalid('database_operator_policy_schema')
    db_plan = database.plan(policy['database'])
    if digest(db_plan) != policy['database_plan_sha256']:
        raise Invalid('database_operator_role_plan_pin')
    for field, pattern in [('project_number', r'[0-9]{6,20}'),
                           ('operator_account', r'[^\s@]+@[^\s@]+'),
                           ('gcloud_sha256', r'[0-9a-f]{64}')]:
        if not isinstance(policy[field], str) or not re.fullmatch(pattern, policy[field]):
            raise Invalid('database_operator_policy_field', field)
    for field in ('gcloud', 'gcloud_config'):
        if not isinstance(policy[field], str) or not Path(policy[field]).is_absolute():
            raise Invalid('database_operator_path', field)
    return {'schema': 'hyprn-database-operator-plan/v1', 'policy': policy,
            'sources': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ('database_operator.py', 'database_setup.py',
                                     'contract.py', 'secrets.py')},
            'temporary_user': {'name': policy['database']['bootstrap_role'],
                               'create': True, 'delete_after_roles_and_secret_publication': True},
            'secret_versions': {alias: {'name': 'hyprn-staging-' + alias, 'existing_versions': [],
                                       'add': 1} for alias in ALIASES},
            'generate': ['modeling-auth', 'modeling-rails'],
            'existing_tunnel_token': 'separately reviewed read; protected file and plan-bound checksum receipt',
            'secret_iam_change': False, 'assistant_secret_change': False,
            'runtime_admin_grant': False, 'automatic_mutation_retries': False}


class Google:
    def __init__(self, policy):
        tool = Path(policy['gcloud'])
        if (not tool.is_file() or tool.stat().st_mode & 0o022 or
                hashlib.sha256(tool.read_bytes()).hexdigest() != policy['gcloud_sha256']):
            raise Invalid('database_operator_tool_pin')
        config = Path(policy['gcloud_config'])
        if (not config.is_dir() or config.is_symlink() or config.stat().st_uid != os.geteuid()
                or config.stat().st_mode & 0o022):
            raise Invalid('database_operator_identity_configuration')
        env = {key: os.environ[key] for key in ('PATH', 'HOME') if key in os.environ}
        env.update(CLOUDSDK_CONFIG=str(config), CLOUDSDK_CORE_DISABLE_FILE_LOGGING='true',
                   CLOUDSDK_CORE_LOG_HTTP='false', CLOUDSDK_CORE_DISABLE_PROMPTS='true',
                   CLOUDSDK_CORE_DISABLE_USAGE_REPORTING='true')
        def cli(arguments):
            try:
                result = subprocess.run([str(tool), '--quiet', '--verbosity=none', *arguments],
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        env=env, timeout=30, check=False)
            except (OSError, subprocess.TimeoutExpired):
                raise Invalid('database_operator_identity_unavailable') from None
            if result.returncode or len(result.stdout) > 16384:
                raise Invalid('database_operator_identity_unavailable')
            return result.stdout.strip().decode('ascii')
        if cli(['config', 'get-value', 'account']) != policy['operator_account']:
            raise Invalid('database_operator_account_mismatch')
        if cli(['projects', 'describe', policy['database']['project_id'],
                '--format=value(projectNumber)']) != policy['project_number']:
            raise Invalid('database_operator_project_number')
        self.token = cli(['auth', 'print-access-token'])
        if not re.fullmatch(r'[A-Za-z0-9._~-]{1,16384}', self.token):
            raise Invalid('database_operator_token_shape')

    def request(self, host, method, path, body=None):
        if host not in {'sqladmin.googleapis.com', 'secretmanager.googleapis.com'}:
            raise Invalid('database_operator_endpoint')
        connection = http.client.HTTPSConnection(host, timeout=30)
        try:
            connection.request(method, path, None if body is None else canonical(body),
                               {'Authorization': 'Bearer ' + self.token,
                                'Content-Type': 'application/json'})
            response = connection.getresponse()
            payload = response.read(1024 * 1024 + 1)
            if response.status not in (200, 201):
                raise Invalid('database_operator_api_http_' + str(response.status))
            if len(payload) > 1024 * 1024:
                raise Invalid('database_operator_api_size')
            result = json.loads(payload)
            if not isinstance(result, dict):
                raise Invalid('database_operator_api_shape')
            return result
        except (OSError, http.client.HTTPException, ValueError):
            raise Invalid('database_operator_api_uncertain') from None
        finally:
            connection.close()


class Operation:
    def __init__(self, policy, root, google, approved):
        self.policy, self.root, self.google = policy, Path(root), google
        self.approved = approved
        self.db = policy['database']
        self.base = '/v1/projects/' + self.db['project_id']
        self.sql = self.base + '/instances/' + self.db['instance']
        self.fd = None

    def __enter__(self):
        self.fd = helper().private_directory(str(self.root))
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        return self

    def __exit__(self, *_):
        os.close(self.fd)

    def read(self, name):
        value = json.loads(database.protected(self.root / name))
        if value.get('plan_sha256') != self.approved:
            raise Invalid('database_operator_receipt_pin')
        return value

    def write(self, name, **fields):
        database.write(self.fd, name, canonical(dict(plan_sha256=self.approved, **fields)))

    def sql_request(self, method, suffix, body=None):
        return self.google.request('sqladmin.googleapis.com', method, self.sql + suffix, body)

    def preflight(self):
        record = self.sql_request('GET', '')
        network = record.get('settings', {}).get('ipConfiguration', {})
        dns = [r.get('name', '').rstrip('.') for r in record.get('dnsNames', [])
               if r.get('connectionType') == 'PRIVATE_SERVICES_ACCESS'
               and r.get('dnsScope') == 'INSTANCE']
        ips = [r.get('ipAddress') for r in record.get('ipAddresses', []) if r.get('type') == 'PRIVATE']
        if (record.get('project') != self.db['project_id']
                or record.get('name') != self.db['instance'] or record.get('state') != 'RUNNABLE'
                or record.get('databaseVersion') != 'POSTGRES_17'
                or network.get('ipv4Enabled') is not False
                or network.get('sslMode') != 'ENCRYPTED_ONLY'
                or network.get('serverCaMode') != 'GOOGLE_MANAGED_CAS_CA'
                or self.db['server_name'] not in dns or ips != [self.db['private_ip']]):
            raise Invalid('database_operator_instance_identity')
        target = self.sql_request('GET', '/databases/' + self.db['database'])
        if any(target.get(key) != self.db[field] for key, field in
               [('name', 'database'), ('instance', 'instance'), ('project', 'project_id')]):
            raise Invalid('database_operator_database_identity')
        ca = record.get('serverCaCert', {}).get('cert', '').encode()
        if hashlib.sha256(ca).hexdigest() != self.db['ca_sha256']:
            raise Invalid('database_operator_ca_pin')

    def user(self):
        result = self.sql_request('GET', '/users')
        if result.get('nextPageToken'):
            raise Invalid('database_operator_user_listing_incomplete')
        users = [u for u in result.get('items', []) if u.get('name') == self.db['bootstrap_role']]
        # Cloud SQL omits the default BUILT_IN enum in user-list responses.
        if len(users) > 1 or users and users[0].get('type', 'BUILT_IN') != 'BUILT_IN':
            raise Invalid('database_operator_user_identity')
        return bool(users)

    def record_operation(self, stem, record):
        name = record.get('name', '')
        if (not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', name)
                or record.get('targetProject') != self.db['project_id']
                or record.get('targetId') != self.db['instance']
                or record.get('operationType') !=
                ('CREATE_USER' if stem == 'bootstrap-create' else 'DELETE_USER')):
            raise Invalid('database_operator_operation_identity')
        self.write(stem + '.operation.json', operation=name)

    def operation_done(self, stem):
        if not (self.root / (stem + '.operation.json')).exists():
            return False
        name = self.read(stem + '.operation.json')['operation']
        result = self.google.request('sqladmin.googleapis.com', 'GET',
                                     self.base + '/operations/' + name)
        if (result.get('name') != name or result.get('targetProject') != self.db['project_id']
                or result.get('targetId') != self.db['instance']
                or result.get('operationType') !=
                ('CREATE_USER' if stem == 'bootstrap-create' else 'DELETE_USER')):
            raise Invalid('database_operator_operation_identity')
        if result.get('error'):
            raise Invalid('database_operator_operation_failed')
        return result.get('status') == 'DONE'

    def create_user(self, *, reconcile=False):
        stem = 'bootstrap-create'
        if not reconcile:
            if (self.root / (stem + '.intent.json')).exists() or self.user():
                raise Invalid('database_operator_create_already_attempted')
            password = os.urandom(32).hex().encode()
            database.write(self.fd, 'bootstrap-password', password)
            self.write(stem + '.intent.json', status='attempted')
            result = self.sql_request('POST', '/users', dict(name=self.db['bootstrap_role'],
                                      type='BUILT_IN', password=password.decode()))
            self.record_operation(stem, result)
        else:
            self.read(stem + '.intent.json')
        if self.operation_done(stem) and self.user():
            if not (self.root / (stem + '.complete.json')).exists():
                self.write(stem + '.complete.json', status='created', user=self.db['bootstrap_role'])
            return {'status': 'created', 'user': self.db['bootstrap_role']}
        return {'status': 'pending_or_uncertain', 'user_present': self.user(),
                'retry': 'read-only reconciliation; never repeat create'}

    def secret_name(self, alias):
        if alias not in ALIASES:
            raise Invalid('database_operator_secret_alias')
        return 'projects/' + self.policy['project_number'] + '/secrets/hyprn-staging-' + alias

    def secret_request(self, method, name, suffix='', body=None):
        return self.google.request('secretmanager.googleapis.com', method, '/v1/' + name + suffix, body)

    def versions(self, name):
        if self.secret_request('GET', name).get('name') != name:
            raise Invalid('database_operator_secret_identity')
        result = self.secret_request('GET', name, '/versions?pageSize=1000')
        if result.get('nextPageToken'):
            raise Invalid('database_operator_versions_incomplete')
        values = result.get('versions', [])
        for value in values:
            if not re.fullmatch(re.escape(name) + r'/versions/[1-9][0-9]*', value.get('name', '')):
                raise Invalid('database_operator_version_identity')
        return values

    def payload_matches(self, name, password):
        value = self.secret_request('GET', name, ':access')
        try:
            data = base64.b64decode(value['payload']['data'], validate=True)
            correct = (value['name'] == name and hmac.compare_digest(data, password)
                       and str(helper().crc32c(data)) == str(value['payload']['dataCrc32c']))
        except (KeyError, TypeError, ValueError):
            correct = False
        if not correct:
            raise Invalid('database_operator_secret_readback')

    def prepare_secret(self, alias):
        if alias not in ('modeling-auth', 'modeling-rails'):
            raise Invalid('database_operator_generated_alias')
        if (self.root / alias).exists() or (self.root / (alias + '.prepared.json')).exists():
            raise Invalid('database_operator_generation_already_attempted')
        password = os.urandom(32).hex().encode()
        database.write(self.fd, alias, password)
        self.write(alias + '.prepared.json', schema='hyprn-prepared-secret/v1', alias=alias,
                   payload_sha256=hashlib.sha256(password).hexdigest())
        return {'status': 'prepared', 'alias': alias,
                'password_file': str(self.root / alias),
                'preparation_receipt': str(self.root / (alias + '.prepared.json'))}

    def prepared(self, preparation_receipt, alias=None):
        receipt = json.loads(database.protected(preparation_receipt))
        if alias in SERVICE_ALIASES:
            if (set(receipt) != {'plan_sha256', 'schema', 'alias', 'payload_sha256'}
                    or receipt['plan_sha256'] != self.approved
                    or receipt['schema'] != 'hyprn-prepared-secret/v1' or receipt['alias'] != alias
                    or not re.fullmatch(r'[0-9a-f]{64}', receipt['payload_sha256'])):
                raise Invalid('database_operator_preparation_receipt')
            return {'credential_sha256': {alias: receipt['payload_sha256']}}
        if (receipt.get('plan_sha256') != self.policy['database_plan_sha256']
                or receipt.get('status') != 'roles_verified' or receipt.get('roles') != database.ROLES
                or set(receipt.get('credential_sha256', {})) != set(database.ROLES)):
            raise Invalid('database_operator_preparation_receipt')
        hashes = receipt['credential_sha256']
        if (len(set(hashes.values())) != len(database.ROLES) or
                any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)
                    for value in hashes.values())):
            raise Invalid('database_operator_credential_hashes')
        return receipt

    def publish(self, alias, password_file, preparation_receipt, *, reconcile=False):
        name = self.secret_name(alias)
        password = database.protected(password_file)
        if alias != 'cloudflare-tunnel' and not re.fullmatch(rb'[0-9a-f]{64}', password):
            raise Invalid('database_operator_password_shape')
        stem = 'publish-' + alias
        hashed = hashlib.sha256(password).hexdigest()
        if self.prepared(preparation_receipt, alias)['credential_sha256'][alias] != hashed:
            raise Invalid('database_operator_role_password_mismatch')
        versions = self.versions(name)
        if reconcile:
            if self.read(stem + '.intent.json').get('payload_sha256') != hashed:
                raise Invalid('database_operator_payload_pin')
        else:
            if (self.root / (stem + '.intent.json')).exists() or versions:
                raise Invalid('database_operator_publication_already_attempted')
            if alias in database.ROLES:
                self.read('bootstrap-create.complete.json')
            self.write(stem + '.intent.json', status='attempted', payload_sha256=hashed)
            version = self.secret_request('POST', name, ':addVersion',
                {'payload': {'data': base64.b64encode(password).decode(),
                             'dataCrc32c': str(helper().crc32c(password))}})
            if not re.fullmatch(re.escape(name) + r'/versions/[1-9][0-9]*', version.get('name', '')):
                raise Invalid('database_operator_version_identity')
            versions = self.versions(name)
        if len(versions) != 1 or versions[0].get('state') != 'ENABLED':
            return {'status': 'pending_or_uncertain', 'alias': alias,
                    'retry': 'read-only reconciliation; never repeat addVersion'}
        version = versions[0]['name']
        self.payload_matches(version, password)
        if not (self.root / (stem + '.complete.json')).exists():
            self.write(stem + '.complete.json', status='published', version=version)
        elif self.read(stem + '.complete.json').get('version') != version:
            raise Invalid('database_operator_version_drift')
        return {'status': 'published', 'alias': alias, 'version': version}

    def delete_user(self, preparation_receipt, *, reconcile=False):
        stem = 'bootstrap-delete'
        if not reconcile:
            if (self.root / (stem + '.intent.json')).exists():
                raise Invalid('database_operator_delete_already_attempted')
            self.read('bootstrap-create.complete.json')
            self.prepared(preparation_receipt)
            for alias in database.ROLES:
                done = self.read('publish-' + alias + '.complete.json')
                version = done['version']
                expected = self.secret_name(alias)
                if not re.fullmatch(re.escape(expected) + r'/versions/[1-9][0-9]*', version):
                    raise Invalid('database_operator_version_identity')
                metadata = self.secret_request('GET', version)
                if metadata.get('name') != version or metadata.get('state') != 'ENABLED':
                    raise Invalid('database_operator_version_unavailable')
            if not self.user():
                raise Invalid('database_operator_user_missing')
            self.write(stem + '.intent.json', status='attempted')
            result = self.sql_request('DELETE', '/users?' + urlencode({'name': self.db['bootstrap_role']}))
            self.record_operation(stem, result)
        else:
            self.read(stem + '.intent.json')
        if self.operation_done(stem) and not self.user():
            if not (self.root / (stem + '.complete.json')).exists():
                self.write(stem + '.complete.json', status='deleted', user=self.db['bootstrap_role'])
            return {'status': 'deleted', 'database_authority_verification_required': True}
        return {'status': 'pending_or_uncertain', 'user_present': self.user(),
                'retry': 'read-only reconciliation; never repeat delete'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'prepare-secret', 'create-user', 'reconcile-user',
                        'publish-secret', 'reconcile-secret', 'delete-user', 'reconcile-delete'))
    parser.add_argument('--policy', required=True)
    parser.add_argument('--private-root')
    parser.add_argument('--approve-sha256')
    parser.add_argument('--alias', choices=ALIASES)
    parser.add_argument('--password-file')
    parser.add_argument('--preparation-receipt')
    args = parser.parse_args(argv)
    try:
        policy = read_json(args.policy)
        reviewed = plan(policy)
        if args.operation == 'plan':
            print(json.dumps({'plan': reviewed, 'sha256': digest(reviewed)}, sort_keys=True))
            return 0
        if not args.private_root or args.approve_sha256 != digest(reviewed):
            raise Invalid('database_operator_exact_approval')
        google = None if args.operation == 'prepare-secret' else Google(policy)
        with Operation(policy, args.private_root, google, args.approve_sha256) as operation:
            if google is not None:
                operation.preflight()
            if args.operation == 'prepare-secret':
                result = operation.prepare_secret(args.alias)
            elif args.operation in ('create-user', 'reconcile-user'):
                result = operation.create_user(reconcile=args.operation == 'reconcile-user')
            elif args.operation in ('publish-secret', 'reconcile-secret'):
                if not args.alias or not args.password_file or not args.preparation_receipt:
                    raise Invalid('database_operator_publication_arguments')
                result = operation.publish(args.alias, args.password_file, args.preparation_receipt,
                                           reconcile=args.operation == 'reconcile-secret')
            else:
                if args.operation == 'delete-user' and not args.preparation_receipt:
                    raise Invalid('database_operator_preparation_receipt')
                result = operation.delete_user(args.preparation_receipt,
                                               reconcile=args.operation == 'reconcile-delete')
            print(json.dumps(result, sort_keys=True))
            return 4 if result.get('status') == 'pending_or_uncertain' else 0
    except Exception as error:
        reason = error.code if isinstance(error, Invalid) else 'database_operator_uncertain'
        print(json.dumps({'reason_code': reason, 'retry': 'inspect before retrying'}))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
