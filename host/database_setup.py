"""Reviewed, single-attempt creation of ordinary application database roles.

Runs on the trusted host with the installed pg8000 driver. No Google API writes,
provider credentials, schema migration, application launch or password reset.
"""
import argparse
import base64
import fcntl
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import resource
import socket
import ssl
import stat
import sys

from contract import Invalid, canonical, cloudsql_tls_name, digest, read_json

ROLES = {
    'db-app-request': 'hyprn_request',
    'db-app-auth': 'hyprn_auth',
    'db-app-migration': 'hyprn_migration',
    'db-app-backup': 'hyprn_backup',
    'db-assistant-background': 'hyprn_assistant_background',
    'db-dispatcher-background': 'hyprn_dispatcher_background',
}
POLICY_FIELDS = {'schema', 'project_id', 'instance', 'installation_id', 'database',
                 'private_ip', 'server_name', 'ca_sha256', 'bootstrap_role'}
ROLE_SQL = """SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,
 rolcanlogin,rolreplication,rolbypassrls,shobj_description(oid,'pg_authid')
 FROM pg_roles WHERE rolname IN
 ('hyprn_request','hyprn_auth','hyprn_migration','hyprn_backup',
 'hyprn_assistant_background','hyprn_dispatcher_background') ORDER BY rolname"""
MEMBER_SQL = """SELECT r.rolname,m.rolname,a.admin_option,a.inherit_option,a.set_option FROM pg_auth_members a
 JOIN pg_roles r ON r.oid=a.roleid JOIN pg_roles m ON m.oid=a.member
 WHERE r.rolname IN ('hyprn_request','hyprn_auth','hyprn_migration','hyprn_backup',
 'hyprn_assistant_background','hyprn_dispatcher_background')
 OR m.rolname IN ('hyprn_request','hyprn_auth','hyprn_migration','hyprn_backup',
 'hyprn_assistant_background','hyprn_dispatcher_background')"""


def plan(policy):
    if not isinstance(policy, dict) or set(policy) != POLICY_FIELDS:
        raise Invalid('database_policy_shape')
    if policy['schema'] != 'hyprn-database-setup/v1':
        raise Invalid('database_policy_schema')
    patterns = {
        'project_id': r'hyprn-staging(?:-[a-z0-9-]+)?',
        'instance': r'[a-z][a-z0-9-]{0,97}',
        'installation_id': r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}',
        'database': r'[a-z][a-z0-9_]{0,62}',
        'server_name': r'[a-z0-9]+\.[a-z0-9]+\.[a-z0-9-]+\.sql-psa\.goog',
        'ca_sha256': r'[0-9a-f]{64}',
        'bootstrap_role': r'hyprn_bootstrap_[a-z0-9]{8,24}',
    }
    for name, pattern in patterns.items():
        if not isinstance(policy[name], str) or not re.fullmatch(pattern, policy[name]):
            raise Invalid('database_policy_field', name)
    try:
        ip = ipaddress.IPv4Address(policy['private_ip'])
        if not any(ip in ipaddress.ip_network(cidr) for cidr in
                   ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
            raise ValueError()
    except (ValueError, TypeError):
        raise Invalid('database_private_address') from None
    return {
        'schema': 'hyprn-database-plan/v1', 'policy': policy,
        'sources': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                    for name in ('database_setup.py', 'contract.py', 'secrets.py')},
        'driver': 'pg8000==1.31.5',
        'roles': ROLES, 'tls': 'verify-full', 'port': 5432,
        'fresh_database_required': True,
        'authority': 'LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE '
                     'NOREPLICATION NOBYPASSRLS',
        'schema_grants': {'public': {'USAGE': list(ROLES.values()),
                                    'CREATE': ['hyprn_migration']}},
        'database_grants': {'CONNECT': list(ROLES.values())},
        'public_database_privileges': [], 'public_schema_privileges': [],
        'backup_role': 'Reserved ordinary identity; no table or RLS bypass grants',
        'temporary_admin': {'create': 'separate reviewed Cloud SQL API action',
                            'remove': 'separate reviewed Cloud SQL API action; verify absence before startup',
                            'temporary_membership': 'ADMIN TRUE, INHERIT FALSE, SET FALSE only'},
        'secret_targets': {alias: 'hyprn-staging-' + alias for alias in ROLES},
        'secret_upload': 'separate reviewed operator transfer; numeric version pins',
        'product_started': False,
    }


def protected(path, limit=65536):
    """Read an owner-only regular file, rejecting symlink ancestors and hard links."""
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise Invalid('database_private_file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise Invalid('database_private_file')
        value = stream.read(limit + 1)
    if not value or len(value) > limit:
        raise Invalid('database_private_file')
    return value


def write(directory, name, value):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.fsync(directory)


def scram(password):
    """Send only a salted verifier in role DDL, never the runtime password."""
    salt = os.urandom(16)
    salted = hashlib.pbkdf2_hmac('sha256', password, salt, 4096)
    client = hmac.digest(salted, b'Client Key', 'sha256')
    stored = hashlib.sha256(client).digest()
    server = hmac.digest(salted, b'Server Key', 'sha256')
    enc = lambda value: base64.b64encode(value).decode('ascii')
    return 'SCRAM-SHA-256$4096:' + enc(salt) + '$' + enc(stored) + ':' + enc(server)


def connect(policy, ca, role, password):
    # host/secrets.py is an operator module, not Python's secrets library.
    # Keep it off dependency import paths; scramp imports the standard library.
    original = sys.path[:]
    try:
        directory = Path(__file__).parent.resolve()
        sys.path[:] = [entry for entry in sys.path if Path(entry or os.getcwd()).resolve() != directory]
        import pg8000.dbapi
    finally:
        sys.path[:] = original
    from importlib.metadata import version
    if version('pg8000') != '1.31.5':
        raise Invalid('database_driver_pin')
    # Connection host controls certificate verification; the socket controls routing.
    context = ssl.create_default_context(cadata=ca.decode('ascii'))
    if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
        raise Invalid('database_tls_required')
    sock = socket.create_connection((policy['private_ip'], 5432), timeout=15)
    try:
        return pg8000.dbapi.connect(
            host=cloudsql_tls_name(policy['server_name']), database=policy['database'], user=role,
            password=password.decode('ascii'), sock=sock, ssl_context=context, timeout=15,
        )
    except BaseException:
        sock.close()
        raise


def query(db, statement, parameters=None):
    cursor = db.cursor()
    try:
        cursor.execute(statement) if parameters is None else cursor.execute(statement, parameters)
        return cursor.fetchall() if cursor.description else []
    finally:
        cursor.close()


def verify_target(db, policy, role):
    row = query(db, 'SELECT current_database(),session_user')[0]
    if tuple(row) != (policy['database'], role):
        raise Invalid('database_target_identity')
    tls = query(db, 'SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()')
    if len(tls) != 1 or len(tls[0]) != 1 or tls[0][0] is not True:
        raise Invalid('database_tls_required')


def fresh(db):
    owner = query(db, "SELECT pg_has_role(current_user,datdba,'USAGE') FROM pg_database "
                  "WHERE datname=current_database()")[0][0]
    schema_owner = query(db, "SELECT pg_has_role(current_user,nspowner,'USAGE') "
                         "FROM pg_namespace WHERE nspname='public'")[0][0]
    if not owner or not schema_owner:
        raise Invalid('database_bootstrap_owner_grants_required')
    if query(db, ROLE_SQL):
        raise Invalid('database_roles_already_exist')
    if query(db, "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                 "WHERE n.nspname='public' LIMIT 1"):
        raise Invalid('database_not_empty')
    if query(db, "SELECT 1 FROM pg_namespace WHERE nspname NOT IN "
                 "('public','pg_catalog','information_schema') "
                 "AND nspname NOT LIKE 'pg_%' LIMIT 1"):
        raise Invalid('database_not_empty')


def authority(db, marker, temporary_admin=None):
    expected = [(role, False, False, False, False, True, False, False, marker)
                for role in sorted(ROLES.values())]
    if [tuple(row) for row in query(db, ROLE_SQL)] != expected:
        raise Invalid('database_role_authority_or_marker')
    for row in query(db, MEMBER_SQL):
        if (temporary_admin is None or tuple(row) !=
                (row[0], temporary_admin, True, False, False) or row[0] not in ROLES.values()):
            raise Invalid('database_role_membership')


def verify_credentials(policy, ca, root, marker, connector, *, temporary_admin=None):
    for alias, role in ROLES.items():
        password = protected(root / alias)
        if not re.fullmatch(rb'[0-9a-f]{64}', password):
            raise Invalid('database_credential_shape')
        connection = connector(policy, ca, role, password)
        try:
            verify_target(connection, policy, role)
            authority(connection, marker, temporary_admin)
            if temporary_admin is None and query(connection,
                    "SELECT 1 FROM pg_roles WHERE rolname='" + policy['bootstrap_role'] + "'"):
                raise Invalid('database_bootstrap_admin_still_exists')
            rights = query(connection, "SELECT has_database_privilege(current_user,current_database(),"
                           "'CONNECT'),has_database_privilege(current_user,current_database(),'CREATE'),"
                           "has_database_privilege(current_user,current_database(),'TEMP'),"
                           "has_schema_privilege(current_user,'public','USAGE'),"
                           "has_schema_privilege(current_user,'public','CREATE')")[0]
            if tuple(rights) != (True, False, False, True, role == 'hyprn_migration'):
                raise Invalid('database_role_privileges')
        finally:
            connection.close()


def execute(policy, ca_path, admin_path, root, approved, *, reconcile=False,
            connector=connect, require_memory=True, verify=False):
    # Existing audited private-directory helper also protects all parent components.
    import importlib.util
    helper_path = Path(__file__).with_name('secrets.py')
    spec = importlib.util.spec_from_file_location('hyprn_host_secrets', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    document = plan(policy)
    if approved != digest(document):
        raise Invalid('database_exact_approval_required')
    root = Path(root)
    directory = helper.private_directory(str(root))
    try:
        if require_memory:
            helper.require_tmpfs(directory)
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ca = protected(ca_path)
        if hashlib.sha256(ca).hexdigest() != policy['ca_sha256']:
            raise Invalid('database_ca_pin')
        marker = 'hyprn-database-setup:' + approved
        intent = root / 'intent.json'
        if reconcile or verify:
            if json.loads(protected(intent)) != {'plan_sha256': approved, 'status': 'attempted'}:
                raise Invalid('database_intent_mismatch')
        elif intent.exists() or any(root.glob('db-*')):
            raise Invalid('database_attempt_exists_reconcile')
        if verify:
            if not (root / 'complete.json').exists():
                raise Invalid('database_preparation_receipt_required')
            verify_credentials(policy, ca, root, marker, connector)
            result = {'schema': 'hyprn-database-authority-receipt/v1',
                      'plan_sha256': approved, 'status': 'verified',
                      'bootstrap_admin_removed': True, 'product_started': False}
            if not (root / 'verified.json').exists():
                write(directory, 'verified.json', canonical(result))
            elif json.loads(protected(root / 'verified.json')) != result:
                raise Invalid('database_receipt_mismatch')
            return result
        admin_password = protected(admin_path)
        db = connector(policy, ca, policy['bootstrap_role'], admin_password)
        try:
            verify_target(db, policy, policy['bootstrap_role'])
            query(db, "SET statement_timeout='15s'")
            query(db, 'SELECT pg_advisory_xact_lock(68272605)')
            if reconcile:
                rows = query(db, ROLE_SQL)
                if not rows:
                    return {'status': 'not_committed', 'plan_sha256': approved,
                            'retry': 'requires explicit reviewed recovery; no changes made'}
                authority(db, marker, policy['bootstrap_role'])
            else:
                fresh(db)
                # Persist every password and intent before the first role mutation.
                for alias in ROLES:
                    write(directory, alias, os.urandom(32).hex().encode('ascii'))
                write(directory, 'intent.json', canonical({'plan_sha256': approved,
                                                          'status': 'attempted'}))
                for alias, role in ROLES.items():
                    verifier = scram(protected(root / alias))
                    query(db, 'CREATE ROLE ' + role + ' LOGIN NOINHERIT NOSUPERUSER '
                          'NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '
                          "'" + verifier + "'")
                    query(db, 'COMMENT ON ROLE ' + role + " IS '" + marker + "'")
                query(db, 'REVOKE ALL ON DATABASE ' + policy['database'] + ' FROM PUBLIC')
                query(db, 'REVOKE ALL ON SCHEMA public FROM PUBLIC')
                for role in ROLES.values():
                    query(db, 'GRANT CONNECT ON DATABASE ' + policy['database'] + ' TO ' + role)
                    query(db, 'GRANT USAGE ON SCHEMA public TO ' + role)
                query(db, 'GRANT CREATE ON SCHEMA public TO hyprn_migration')
                authority(db, marker, policy['bootstrap_role'])
                db.commit()
        finally:
            db.close()
        # Read-back authenticates all six generated credentials using real verified TLS.
        verify_credentials(policy, ca, root, marker, connector,
                           temporary_admin=policy['bootstrap_role'])
        receipt = {'schema': 'hyprn-database-setup-receipt/v1', 'plan_sha256': approved,
                   'status': 'roles_verified', 'roles': ROLES,
                   'credential_sha256': {alias: hashlib.sha256(protected(root / alias)).hexdigest()
                                         for alias in ROLES},
                   'secrets_uploaded': False, 'bootstrap_admin_removed': False,
                   'product_started': False}
        if not (root / 'complete.json').exists():
            write(directory, 'complete.json', canonical(receipt))
        elif json.loads(protected(root / 'complete.json')) != receipt:
            raise Invalid('database_receipt_mismatch')
        return receipt
    finally:
        os.close(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('plan', 'apply', 'reconcile', 'verify'))
    parser.add_argument('--policy', required=True)
    parser.add_argument('--ca-file')
    parser.add_argument('--admin-password-file')
    parser.add_argument('--private-root')
    parser.add_argument('--approve-sha256')
    args = parser.parse_args(argv)
    try:
        policy = read_json(args.policy)
        if args.operation == 'plan':
            result = plan(policy)
            print(json.dumps({'plan': result, 'sha256': digest(result)}, sort_keys=True))
        else:
            if (not all((args.ca_file, args.private_root, args.approve_sha256)) or
                    args.operation != 'verify' and not args.admin_password_file):
                raise Invalid('database_apply_arguments')
            print(json.dumps(execute(policy, args.ca_file, args.admin_password_file,
                                     args.private_root, args.approve_sha256,
                                     reconcile=args.operation == 'reconcile',
                                     verify=args.operation == 'verify'), sort_keys=True))
        return 0
    except Exception as error:
        code = error.code if isinstance(error, Invalid) else 'database_operation_uncertain'
        print(json.dumps({'reason_code': code, 'retry': 'inspect and reconcile; never reset'}))
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
