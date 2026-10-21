"""Trusted-host standard Cloud SQL backup; database-only, never restore or retry POST.

The caller supplies reviewed bindings and a durable private directory per operation.
A successful receipt proves only the provider backup, not writer quiescence or a
coherent installation snapshot. Losing this directory loses duplicate prevention.
"""
import argparse
from datetime import datetime
import fcntl
import hashlib
import http.client
import json
import ipaddress
import os
import re
import resource
import stat
import sys
import time
from urllib.parse import urlencode

from contract import Invalid
from secrets import AttachedServiceAccount, private_directory, write_file

MAX_BODY = 1000000
MAX_PAGES = 100
MAX_SECONDS = 300
BINDING_FIELDS = ('project_id', 'project_number', 'instance', 'installation_id',
                  'release_digest', 'configuration_digest', 'operation_id', 'private_network')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Invalid('invalid_json')
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(Invalid('invalid_json')))
        if not isinstance(value, dict):
            raise Invalid('invalid_json')
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise Invalid('invalid_json') from None


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def timestamp(value):
    if not matches(value, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z'):
        raise Invalid('provider_timestamp')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise Invalid('provider_timestamp') from None


def bindings(args):
    value = {key: getattr(args, key) for key in BINDING_FIELDS}
    patterns = {
        'project_id': r'hyprn-staging(?:-[a-z0-9-]+)?',
        'project_number': r'[1-9][0-9]{5,19}',
        'instance': r'[a-z][a-z0-9-]{0,97}[a-z0-9]',
        'installation_id': r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}',
        'release_digest': r'sha256:[0-9a-f]{64}',
        'configuration_digest': r'sha256:[0-9a-f]{64}',
        'private_network': r'projects/' + re.escape(value['project_id']) + r'/global/networks/[a-z][a-z0-9-]{0,61}[a-z0-9]',
        'operation_id': r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',
    }
    if any(not matches(value[key], pattern) for key, pattern in patterns.items()):
        raise Invalid('backup_binding')
    if len(value['project_id']) > 63 or not 1 <= args.poll_attempts <= 20 or not 0 <= args.poll_seconds <= 30:
        raise Invalid('backup_limits')
    return value


class GoogleSQL:
    """Fixed TLS destination, normal certificate verification, no proxies/retries."""
    def __init__(self, args):
        principal = AttachedServiceAccount()
        principal.preflight(args)
        self.token = principal.token
        self.deadline = time.monotonic() + MAX_SECONDS
        self.base = '/v1/projects/' + args.project_id + '/instances/' + args.instance

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise Invalid('backup_deadline')
        return min(30, remaining)

    def request(self, method, path, body=None):
        connection = http.client.HTTPSConnection('sqladmin.googleapis.com', timeout=self.remaining())
        try:
            headers = {'Authorization': 'Bearer ' + self.token, 'Accept': 'application/json'}
            if body is not None:
                headers['Content-Type'] = 'application/json'
            connection.request(method, path, body=canonical(body) if body is not None else None,
                               headers=headers)
            response = connection.getresponse()
            data = response.read(MAX_BODY + 1)
            if response.status != 200 or len(data) > MAX_BODY:
                raise Invalid('cloudsql_request_failed')
            return decode(data)
        except (OSError, http.client.HTTPException, ValueError):
            raise Invalid('cloudsql_request_failed') from None
        finally:
            connection.close()

    def source(self, binding, expected_endpoint=None):
        value = self.request('GET', self.base)
        if (value.get('kind') != 'sql#instance' or value.get('project') != binding['project_id'] or
                value.get('name') != binding['instance'] or value.get('state') != 'RUNNABLE'):
            raise Invalid('source_instance_identity')
        settings = value.get('settings')
        configuration = settings.get('backupConfiguration') if isinstance(settings, dict) else None
        if (not isinstance(configuration, dict) or configuration.get('backupTier') != 'STANDARD' or
                configuration.get('enabled') is not True):
            raise Invalid('standard_backup_required')
        timestamp(value.get('createTime'))
        if value.get('databaseVersion') != 'POSTGRES_17':
            raise Invalid('source_database_version')
        network = settings.get('ipConfiguration')
        if (not isinstance(network, dict) or network.get('ipv4Enabled') is not False or
                network.get('privateNetwork') != binding['private_network'] or
                network.get('sslMode') != 'ENCRYPTED_ONLY'):
            raise Invalid('source_network_policy')
        source = {key: value[key] for key in ('project', 'name', 'createTime', 'databaseVersion')}
        source['policy'] = {'private_network': network['privateNetwork'], 'ipv4_enabled': False,
                            'ssl_mode': 'ENCRYPTED_ONLY', 'backup_tier': 'STANDARD', 'backups_enabled': True}
        if expected_endpoint is not None:
            if (not isinstance(expected_endpoint, dict) or set(expected_endpoint) != {'host', 'server_name'}
                    or not isinstance(expected_endpoint['host'], str)
                    or not matches(expected_endpoint['server_name'], r'[a-z0-9][a-z0-9.-]{1,251}[a-z0-9]')):
                raise Invalid('source_endpoint_binding')
            try:
                address = ipaddress.ip_address(expected_endpoint['host'])
                if address.version != 4 or not address.is_private or str(address) != expected_endpoint['host']:
                    raise ValueError
            except ValueError:
                raise Invalid('source_endpoint_binding') from None
            mappings = value.get('ipAddresses')
            if (not isinstance(mappings, list) or not mappings or
                    any(not isinstance(item, dict) or item.get('type') != 'PRIVATE' for item in mappings) or
                    [item.get('ipAddress') for item in mappings] != [expected_endpoint['host']]):
                raise Invalid('source_endpoint_mismatch')
            # Instance PSA names only; cluster/write endpoints cannot identify
            # the one private instance that this whole-store backup must cover.
            names = value.get('dnsNames')
            if names is None:
                names = [value.get('dnsName')]
            elif isinstance(names, list) and all(isinstance(item, dict) for item in names):
                names = [item.get('name') for item in names
                         if item.get('connectionType') == 'PRIVATE_SERVICES_ACCESS'
                         and item.get('dnsScope') == 'INSTANCE']
            else:
                raise Invalid('source_endpoint_mismatch')
            if (len(names) != 1 or not isinstance(names[0], str) or
                    names[0].removesuffix('.') != expected_endpoint['server_name']):
                raise Invalid('source_endpoint_mismatch')
            source['endpoint'] = dict(expected_endpoint)
        return source

    def dispatch(self, binding, description):
        value = self.request('POST', self.base + '/backupRuns', {'description': description})
        if (value.get('kind') != 'sql#operation' or value.get('targetProject') != binding['project_id'] or
                value.get('targetId') != binding['instance'] or value.get('operationType') != 'BACKUP_VOLUME' or
                value.get('status') not in ('PENDING', 'RUNNING', 'DONE') or value.get('error') or
                not matches(value.get('name'), r'[a-zA-Z0-9_-]{1,128}')):
            raise Invalid('provider_operation_identity')
        # Poll BackupRun via list/get instead of operations.get: DONE alone is not
        # backup success, and the exact BackupRun supplies identity and timestamps.
        return value['name']

    def locate(self, description):
        found = []
        token = None
        seen = set()
        for _ in range(MAX_PAGES):
            query = {'maxResults': 100}
            if token is not None:
                query['pageToken'] = token
            page = self.request('GET', self.base + '/backupRuns?' + urlencode(query))
            items = page.get('items', [])
            if page.get('kind') != 'sql#backupRunsList' or not isinstance(items, list) or len(items) > 100:
                raise Invalid('provider_list')
            for item in items:
                if not isinstance(item, dict):
                    raise Invalid('provider_list')
                if item.get('description') == description:
                    found.append(item)
                    if len(found) > 1:
                        raise Invalid('backup_ambiguous')
            token = page.get('nextPageToken')
            if token is None or token == '':
                if not found:
                    raise Invalid('backup_not_found_reconcile')
                return found[0]
            if not isinstance(token, str) or len(token) > 4096 or token in seen:
                raise Invalid('provider_pagination')
            seen.add(token)
        raise Invalid('provider_pagination_limit')


def verify_backup(value, binding, description, backup_id=None):
    identifier = value.get('id')
    if not matches(identifier, r'[1-9][0-9]{0,18}') or int(identifier) > 9223372036854775807:
        raise Invalid('provider_backup_identity')
    resource_name = '/projects/' + binding['project_id'] + '/instances/' + binding['instance'] + '/backupRuns/' + identifier
    # selfLink is evidence only and is never followed. Both documented API versions
    # identify the same exact resource; BackupRun has no separate project field.
    links = {host + version + resource_name
             for host in ('https://sqladmin.googleapis.com', 'https://www.googleapis.com')
             for version in ('/v1', '/sql/v1', '/sql/v1beta4')}
    if (value.get('kind') != 'sql#backupRun' or value.get('instance') != binding['instance'] or
            not isinstance(value.get('selfLink'), str) or value.get('selfLink') not in links or value.get('description') != description or
            value.get('type') != 'ON_DEMAND' or backup_id is not None and identifier != backup_id):
        raise Invalid('provider_backup_identity')
    if value.get('status') not in ('ENQUEUED', 'RUNNING', 'SUCCESSFUL', 'FAILED', 'OVERDUE',
                                   'SKIPPED', 'DELETION_PENDING', 'DELETION_FAILED', 'DELETED'):
        raise Invalid('provider_backup_status')
    return identifier


def read_private(directory, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise Invalid('private_state_file')
        data = stream.read(MAX_BODY + 1)
        if len(data) > MAX_BODY:
            raise Invalid('private_state_file')
        return decode(data)


def save(directory, name, value, replace=False):
    target = '.' + name + '.tmp' if replace else name
    write_file(directory, target, canonical(value), os.geteuid())
    if replace:
        os.replace(target, name, src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)


def backup(args, *, expected_endpoint=None):
    binding = bindings(args)
    resource_name = 'projects/' + binding['project_id'] + '/instances/' + binding['instance']
    if args.command == 'create' and args.approve_resource != resource_name:
        raise Invalid('explicit_backup_approval_required')
    directory = private_directory(args.state_root)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
        names = set(os.listdir(directory))
        if names - {'intent.json', 'status.json', 'receipt.json'}:
            raise Invalid('unexpected_state_file')
        stored = {name: read_private(directory, name) for name in names}
        intent = stored.get('intent.json')
        if intent is None and (args.command != 'create' or names):
            raise Invalid('backup_intent_missing')
        if intent is not None:
            if (set(intent) != {'schema', 'binding', 'source', 'description'} or type(intent.get('schema')) is not int or intent.get('schema') != 1 or
                    intent.get('binding') != binding or not isinstance(intent.get('source'), dict)):
                raise Invalid('backup_intent_mismatch')
            expected = 'hyprn-db-v1:' + hashlib.sha256(canonical({'binding': binding, 'source': intent['source']})).hexdigest()
            if intent['description'] != expected:
                raise Invalid('backup_intent_mismatch')
        google = GoogleSQL(args)
        source = google.source(binding, expected_endpoint=expected_endpoint)
        if intent is not None and intent['source'] != source:
            raise Invalid('source_instance_changed')
        if intent is None:
            description = 'hyprn-db-v1:' + hashlib.sha256(canonical({'binding': binding, 'source': source})).hexdigest()
            intent = {'schema': 1, 'binding': binding, 'source': source, 'description': description}
            # A crash from this point onward must always reconcile by GET, never POST.
            save(directory, 'intent.json', intent)
            save(directory, 'status.json', {'status': 'pending', 'reason': 'dispatch_not_confirmed'})
            try:
                operation = google.dispatch(binding, description)
            except Invalid:
                save(directory, 'status.json', {'status': 'closed', 'reason': 'backup_dispatch_uncertain'}, replace=True)
                raise Invalid('backup_dispatch_uncertain') from None
            save(directory, 'status.json', {'status': 'pending', 'provider_operation': operation}, replace=True)
        try:
            for attempt in range(args.poll_attempts):
                candidate = google.locate(intent['description'])
                identifier = verify_backup(candidate, binding, intent['description'])
                value = google.request('GET', google.base + '/backupRuns/' + identifier)
                verify_backup(value, binding, intent['description'], identifier)
                if value['status'] == 'SUCCESSFUL':
                    if value.get('error'):
                        raise Invalid('provider_backup_error')
                    queued, start, end = [timestamp(value.get(key)) for key in ('enqueuedTime', 'startTime', 'endTime')]
                    if not queued <= start <= end:
                        raise Invalid('provider_timestamp')
                    receipt = {'schema': 1, 'status': 'complete', 'scope': 'cloudsql-database-only',
                               'coherent_installation_backup': False, 'binding': binding, 'source': source,
                               'description': intent['description'], 'backup_id': identifier,
                               'resource': resource_name + '/backupRuns/' + identifier,
                               'provider_status': 'SUCCESSFUL', 'type': 'ON_DEMAND',
                               'enqueued_time': value['enqueuedTime'], 'start_time': value['startTime'],
                               'end_time': value['endTime']}
                    if 'receipt.json' in stored:
                        if stored['receipt.json'] != receipt:
                            raise Invalid('backup_receipt_changed')
                    else:
                        save(directory, 'receipt.json', receipt)
                    save(directory, 'status.json', {'status': 'complete', 'backup_id': identifier}, replace=True)
                    return receipt
                if value['status'] not in ('ENQUEUED', 'RUNNING'):
                    raise Invalid('backup_unavailable')
                if attempt + 1 < args.poll_attempts:
                    time.sleep(min(args.poll_seconds, google.remaining()))
            raise Invalid('backup_pending')
        except Invalid as error:
            save(directory, 'status.json', {'status': 'closed', 'reason': error.code}, replace=True)
            raise
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('create', 'resume', 'verify'))
    for key in BINDING_FIELDS:
        parser.add_argument('--' + key.replace('_', '-'), required=True)
    parser.add_argument('--state-root', required=True)
    parser.add_argument('--approve-resource')
    parser.add_argument('--poll-attempts', type=int, default=5)
    parser.add_argument('--poll-seconds', type=int, default=5)
    args = parser.parse_args()
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.umask(0o077)
        result = backup(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Invalid as error:
        print(json.dumps({'error': error.code}), file=sys.stderr)
    except (OSError, ValueError, TypeError):
        print(json.dumps({'error': 'backup_operation_failed'}), file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
