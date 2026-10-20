"""Pinned secret delivery and explicitly approved, single-attempt provider transfer.

Only metadata reaches stdout/stderr. The privileged caller owns the runtime,
tool/configuration and private roots; product descriptors cannot choose paths.
"""
import argparse
import base64
import ctypes
import fcntl
import http.client
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys

from contract import Invalid, SCHEMA_PATH, SECRET_CONSUMERS, read_json, schema_check

MAX_SECRET = 65536
DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def private_directory(path):
    """Walk without following any symlink, then retain the directory capability."""
    if not path.startswith("/") or any(p in (".", "..", "") for p in path[1:].split("/")):
        raise Invalid("private_path")
    fd = os.open("/", DIRECTORY)
    try:
        for part in path[1:].split("/"):
            child = os.open(part, DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            if info.st_uid not in (0, os.geteuid()):
                raise Invalid("private_owner")
            if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
                raise Invalid("private_parent")
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise Invalid("private_mode")
        return fd
    except BaseException:
        os.close(fd)
        raise


def require_tmpfs(fd):
    if sys.platform != "linux" or os.geteuid() != 0:
        raise Invalid("linux_root_required")
    # fstatfs writes a platform struct; only its first native long is inspected.
    buffer = ctypes.create_string_buffer(512)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.fstatfs(fd, ctypes.byref(buffer)) != 0:
        raise Invalid("tmpfs_check")
    if ctypes.c_long.from_buffer(buffer).value != 0x01021994:
        raise Invalid("tmpfs_required")
    if len(Path("/proc/swaps").read_text().splitlines()) != 1:
        raise Invalid("swap_must_be_disabled")


def runtime_binding(args):
    runtime = read_json(args.runtime)
    schema_check(runtime, read_json(SCHEMA_PATH)["$defs"]["runtime"], "runtime")
    if (runtime["project_id"] != args.project_id or
            runtime["project_number"] != args.project_number):
        raise Invalid("project_mismatch")
    for alias, binding in runtime["secrets"].items():
        if binding["name"] != "hyprn-staging-" + alias:
            raise Invalid("secret_binding")
    return runtime


def request_google(metadata, path, token=None):
    """Fixed destinations, no proxy environment, redirects, logging or retries."""
    connection = (http.client.HTTPConnection("169.254.169.254", timeout=10) if metadata
                  else http.client.HTTPSConnection("secretmanager.googleapis.com", timeout=30))
    headers = {"Metadata-Flavor": "Google"} if metadata else {"Authorization": "Bearer " + token}
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        data = response.read(100001)
        if (response.status != 200 or len(data) > 100000 or
                metadata and response.getheader("Metadata-Flavor") != "Google"):
            raise Invalid("google_operation_failed")
        return data
    except (OSError, http.client.HTTPException, ValueError):
        raise Invalid("google_operation_failed") from None
    finally:
        connection.close()


def crc32c(data):
    value = 0xffffffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0x82f63b78 if value & 1 else 0)
    return value ^ 0xffffffff


class AttachedServiceAccount:
    """Trusted host only: metadata principal, with no ADC or CLI fallback."""
    def preflight(self, args):
        prefix = "/computeMetadata/v1/"
        expected = "hyprn-staging-runtime@" + args.project_id + ".iam.gserviceaccount.com"
        for path, value in (("project/project-id", args.project_id),
                            ("project/numeric-project-id", args.project_number),
                            ("instance/service-accounts/default/email", expected)):
            if request_google(True, prefix + path).strip() != value.encode():
                raise Invalid("attached_identity_mismatch")
        try:
            result = json.loads(request_google(True, prefix + "instance/service-accounts/default/token"))
            token = result["access_token"]
            if (result["token_type"] != "Bearer" or not isinstance(token, str) or
                    not re.fullmatch(r"[A-Za-z0-9._~-]{1,8192}", token) or
                    type(result["expires_in"]) is not int or result["expires_in"] < 120):
                raise Invalid("metadata_token")
        except (KeyError, TypeError, ValueError):
            raise Invalid("metadata_token") from None
        self.token = token
        self.project_number = args.project_number

    def fetch(self, binding):
        name = ("projects/" + self.project_number + "/secrets/" + binding["name"]
                + "/versions/" + str(binding["version"]))
        try:
            response = json.loads(request_google(False, "/v1/" + name + ":access", self.token))
            if response["name"] != name:
                raise Invalid("secret_identity")
            data = base64.b64decode(response["payload"]["data"], validate=True)
            if (not 0 < len(data) <= MAX_SECRET or
                    str(crc32c(data)) != response["payload"]["dataCrc32c"]):
                raise Invalid("secret_payload")
            return data
        except (KeyError, TypeError, ValueError):
            raise Invalid("secret_payload") from None


class Google:
    def __init__(self, args):
        if not args.gcloud:
            raise Invalid("reviewed_tool_required")
        tool = Path(args.gcloud)
        if not tool.is_absolute() or not tool.is_file() or tool.stat().st_mode & 0o022:
            raise Invalid("reviewed_tool_required")
        # No inherited CLOUDSDK debug/endpoint/credential overrides or token env.
        self.env = {k: os.environ[k] for k in ("PATH", "HOME") if k in os.environ}
        for key in ("CLOUDSDK_CONFIG", "GOOGLE_APPLICATION_CREDENTIALS"):
            value = os.environ.get(key)
            if not value or not os.path.isabs(value):
                raise Invalid("dedicated_identity_required")
            self.env[key] = value
        self.env.update(CLOUDSDK_CORE_DISABLE_FILE_LOGGING="true",
                        CLOUDSDK_CORE_LOG_HTTP="false",
                        CLOUDSDK_CORE_DISABLE_PROMPTS="true",
                        CLOUDSDK_CORE_DISABLE_USAGE_REPORTING="true")
        self.prefix = [str(tool), "--quiet", "--verbosity=none", "--project=" + args.project_id]

    def call(self, *args, data=None):
        try:
            result = subprocess.run(self.prefix + list(args), input=data,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    env=self.env, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise Invalid("google_operation_failed") from None
        if result.returncode or len(result.stdout) > 100000:
            raise Invalid("google_operation_failed")
        return result.stdout.strip()

    def preflight(self, args):
        number = self.call("projects", "describe", args.project_id, "--format=value(projectNumber)")
        if number != args.project_number.encode():
            raise Invalid("project_mismatch")

    def fetch(self, binding):
        value = self.call("secrets", "versions", "access", str(binding["version"]),
                          "--secret=" + binding["name"], "--format=get(payload.data)")
        try:
            value = base64.b64decode(value, altchars=b"-_", validate=True)
        except ValueError:
            raise Invalid("secret_payload") from None
        if not 0 < len(value) <= MAX_SECRET:
            raise Invalid("secret_payload")
        return value


def owner(runtime, consumer):
    return runtime["service_users"]["modeling" if consumer == "modeling" else "app"]


def write_file(directory, name, data, uid):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                 dir_fd=directory)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            if uid != os.geteuid():
                os.fchown(fd, uid, uid)
            os.fchmod(fd, 0o600)
            os.fsync(fd)
    finally:
        os.close(fd)


def remove_consumer(root, name, aliases, uid):
    """Check the complete owned inventory before deleting any one file."""
    fd = os.open(name, DIRECTORY, dir_fd=root)
    try:
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise Invalid("consumer_directory")
        names = os.listdir(fd)
        if set(names) - set(aliases):
            raise Invalid("unexpected_secret_file")
        for filename in names:
            info = os.stat(filename, dir_fd=fd, follow_symlinks=False)
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                    info.st_uid != uid or stat.S_IMODE(info.st_mode) != 0o600):
                raise Invalid("unsafe_secret_file")
        for filename in names:
            os.unlink(filename, dir_fd=fd)
    finally:
        os.close(fd)
    os.rmdir(name, dir_fd=root)


def deliver(args, runtime):
    root = private_directory(args.root)
    try:
        require_tmpfs(root)
        fcntl.flock(root, fcntl.LOCK_EX | fcntl.LOCK_NB)
        consumer = args.consumer
        aliases = SECRET_CONSUMERS[consumer]
        staging = ".loading-" + consumer
        if set(os.listdir(root)) - set(SECRET_CONSUMERS) - {
                ".loading-" + c for c in SECRET_CONSUMERS}:
            raise Invalid("unexpected_root_entry")
        if args.operation == "cleanup":
            for name in (consumer, staging):
                if name in os.listdir(root):
                    remove_consumer(root, name, aliases, owner(runtime, consumer))
            return {"status": "removed", "consumer": consumer}
        if consumer in os.listdir(root) or staging in os.listdir(root):
            raise Invalid("consumer_exists_cleanup_required")
        google = AttachedServiceAccount() if args.identity_mode == "attached-service-account" else Google(args)
        google.preflight(args)
        os.mkdir(staging, 0o700, dir_fd=root)
        directory = os.open(staging, DIRECTORY, dir_fd=root)
        try:
            for alias in aliases:
                data = google.fetch(runtime["secrets"][alias])
                write_file(directory, alias, data, owner(runtime, consumer))
            os.fsync(directory)
            os.rename(staging, consumer, src_dir_fd=root, dst_dir_fd=root)
            os.fsync(root)
        except BaseException:
            # A partial write owned by root can occur before fchown; remove only
            # files created by this invocation through the still-private fd.
            for name in os.listdir(directory):
                os.unlink(name, dir_fd=directory)
            if staging in os.listdir(root):
                os.rmdir(staging, dir_fd=root)
            raise
        finally:
            os.close(directory)
        return {"status": "delivered", "consumer": consumer, "files": len(aliases)}
    finally:
        os.close(root)


def transfer(args):
    # Bootstrap precedes complete runtime/agent bindings and the first version.
    properties = read_json(SCHEMA_PATH)["$defs"]["runtime"]["properties"]
    schema_check(args.project_id, properties["project_id"], "project_id")
    schema_check(args.project_number, properties["project_number"], "project_number")
    if not re.fullmatch(r"hyprn-staging(?:-[a-z0-9-]+)?", args.project_id):
        raise Invalid("staging_project_required")
    secret = "projects/" + args.project_number + "/secrets/hyprn-staging-assistant-provider"
    if args.approve_resource != secret:
        raise Invalid("explicit_transfer_approval_required")
    directory = private_directory(args.receipt_root)
    try:
        fcntl.flock(directory, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = "assistant-provider-transfer.json"
        if receipt in os.listdir(directory):
            raise Invalid("transfer_already_attempted_reconcile_receipt")
        google = Google(args)
        google.preflight(args)
        if google.call("secrets", "describe", secret, "--format=value(name)") != secret.encode():
            raise Invalid("secret_identity")
        parent = private_directory(str(Path(args.key_file).parent))
        try:
            fd = os.open(Path(args.key_file).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                        info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
                    raise Invalid("private_key_file")
                data = stream.read(MAX_SECRET + 1)
                if not 0 < len(data) <= MAX_SECRET:
                    raise Invalid("secret_payload")
        finally:
            os.close(parent)
        # Durable before the side effect: ambiguous failure must never redispatch.
        pending = json.dumps({"resource": secret, "status": "attempted-reconcile-before-retry"}).encode()
        write_file(directory, receipt, pending, os.geteuid())
        os.fsync(directory)
        try:
            version = google.call("secrets", "versions", "add", secret,
                                  "--data-file=-", "--format=value(name)", data=data)
            text = version.decode("ascii")
            if not re.fullmatch(re.escape(secret) + r"/versions/[1-9][0-9]*", text):
                raise Invalid("transfer_uncertain_reconcile_receipt")
            output = {"status": "created", "version": text}
            write_file(directory, receipt + ".complete", json.dumps(output).encode(), os.geteuid())
            os.replace(receipt + ".complete", receipt, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
            return output
        except (Invalid, OSError, UnicodeError):
            raise Invalid("transfer_uncertain_reconcile_receipt") from None
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("deliver", "cleanup", "transfer-provider"):
        command = commands.add_parser(name)
        for flag in ("project-id", "project-number"):
            command.add_argument("--" + flag, required=True)
        if name != "transfer-provider":
            command.add_argument("--runtime", required=True)
        if name != "cleanup":
            command.add_argument("--gcloud")
        if name == "deliver":
            command.add_argument("--identity-mode", required=True,
                                 choices=("attached-service-account", "dedicated-operator"))
        if name == "transfer-provider":
            for flag in ("key-file", "receipt-root", "approve-resource"):
                command.add_argument("--" + flag, required=True)
        else:
            command.add_argument("--root", required=True)
            command.add_argument("--consumer", required=True, choices=tuple(SECRET_CONSUMERS))
    args = parser.parse_args()
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.umask(0o077)
        result = transfer(args) if args.operation == "transfer-provider" else deliver(args, runtime_binding(args))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Invalid as error:
        print(json.dumps({"error": error.code}), file=sys.stderr)
    except (OSError, ValueError):
        print(json.dumps({"error": "secret_operation_failed"}), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
