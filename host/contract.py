"""Closed staging contract validation and deterministic offline runtime preview.

Only the JSON Schema vocabulary used by the shipped schema is implemented here.
An unknown schema keyword fails closed. This command never extracts bundles,
fetches secrets, executes product code, starts services, or accesses cloud APIs.
"""
import argparse
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "contracts/v1/deployment.schema.json"
MAX_DOCUMENT = 2 * 1024 * 1024
MAX_BUNDLE_BYTES = 20 * 1024**3
MAX_EXPANDED_BYTES = 32 * 1024**3
MAX_MEMBERS = 200000
SECRET_CONSUMERS = {
    "app": ("modeling-auth", "assistant-provider", "db-app-request", "db-app-auth",
            "db-assistant-background"),
    "dispatcher": ("modeling-auth", "db-app-request", "db-dispatcher-background"),
    "modeling": ("modeling-auth", "modeling-rails"),
    "migration": ("db-app-migration",),
    "backup": ("db-app-backup",),
}
SCHEMA_KEYWORDS = {
    "type", "const", "enum", "properties", "required", "additionalProperties",
    "items", "minItems", "maxItems", "uniqueItems", "minimum", "maximum",
    "minLength", "maxLength", "pattern",
}


class Invalid(Exception):
    def __init__(self, code, location="input"):
        self.code = code
        self.location = location
        super().__init__(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise Invalid("duplicate_key")
        result[key] = value
    return result


def reject_constant(_value):
    raise Invalid("invalid_json")


def read_json(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_DOCUMENT + 1)
    if len(raw) > MAX_DOCUMENT:
        raise Invalid("document_size")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise Invalid("invalid_json") from None
    finite(value)
    return value


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise Invalid("invalid_json")
    if isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, list):
        for item in value:
            finite(item)


def schema_check(value, rule, location):
    if set(rule) - SCHEMA_KEYWORDS:
        raise Invalid("unsupported_schema", location)
    if "const" in rule and canonical(value) != canonical(rule["const"]):
        raise Invalid("schema_value", location)
    if "enum" in rule and value not in rule["enum"]:
        raise Invalid("schema_value", location)
    if "type" in rule:
        types = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
        kinds = {dict: "object", list: "array", str: "string", int: "integer",
                 bool: "boolean", type(None): "null"}
        if kinds.get(type(value)) not in types:
            raise Invalid("schema_type", location)
    if isinstance(value, dict) and "properties" in rule:
        properties = rule["properties"]
        if rule.get("additionalProperties") is not False:
            raise Invalid("unsupported_schema", location)
        if set(value) - set(properties):
            raise Invalid("unknown_field", location)
        if set(rule.get("required", [])) - set(value):
            raise Invalid("missing_field", location)
        for key in value:
            schema_check(value[key], properties[key], location + "." + key)
    elif isinstance(value, list) and "items" in rule:
        if not rule.get("minItems", 0) <= len(value) <= rule.get("maxItems", MAX_MEMBERS):
            raise Invalid("schema_value", location)
        if rule.get("uniqueItems") and len({canonical(item) for item in value}) != len(value):
            raise Invalid("duplicate_item", location)
        for item in value:
            schema_check(item, rule["items"], location + "[]")
    elif isinstance(value, str):
        if not rule.get("minLength", 0) <= len(value) <= rule.get("maxLength", MAX_DOCUMENT):
            raise Invalid("schema_value", location)
        if "pattern" in rule and not re.fullmatch(rule["pattern"], value):
            raise Invalid("schema_value", location)
    elif type(value) is int:
        if not rule.get("minimum", -2**53) <= value <= rule.get("maximum", 2**53):
            raise Invalid("schema_value", location)


def check_documents(documents):
    schema = read_json(SCHEMA_PATH)
    for kind, value in documents.items():
        schema_check(value, schema["$defs"][kind], kind)
    workload, release, runtime = (documents[k] for k in ("workload", "release", "runtime"))
    contract = release["platform_contract"]
    if contract["schema_sha256"] != hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest():
        raise Invalid("schema_pin", "release.platform_contract")
    if contract["renderer_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise Invalid("renderer_pin", "release.platform_contract")
    if contract["workload_sha256"] != digest(workload):
        raise Invalid("workload_pin", "release.platform_contract")
    if contract["commit"] != runtime["platform_commit"]:
        raise Invalid("identity_mismatch", "runtime.platform_commit")
    registry = runtime["registry"]
    if registry.split("/")[1] != runtime["project_id"]:
        raise Invalid("identity_mismatch", "runtime.registry")
    for image in release["images"].values():
        if not image.startswith(registry + "/"):
            raise Invalid("registry_mismatch", "release.images")
    for owner, store in release["stores"].items():
        if not store["read_min"] <= store["write_version"] <= store["read_max"]:
            raise Invalid("store_compatibility", "release.stores." + owner)
        ids = [migration["id"] for migration in store["migrations"]]
        if len(ids) != len(set(ids)):
            raise Invalid("duplicate_migration", "release.stores." + owner)
    if len(set(runtime["store_ids"].values())) != 3:
        raise Invalid("identity_mismatch", "runtime.store_ids")
    buckets = [runtime[k] for k in ("artifacts_bucket", "desired_bucket", "backup_bucket")]
    if len(set(buckets)) != 3 or any(not b.startswith("hyprn-staging-") for b in buckets):
        raise Invalid("identity_mismatch", "runtime.buckets")
    for alias, secret in runtime["secrets"].items():
        if secret["name"] != "hyprn-staging-" + alias:
            raise Invalid("secret_binding", "runtime.secrets")
    try:
        address = ipaddress.ip_address(runtime["database"]["host"])
    except ValueError:
        raise Invalid("database_address", "runtime.database.host") from None
    if address not in ipaddress.ip_network("10.0.0.0/8"):
        raise Invalid("database_address", "runtime.database.host")
    if release["execution"]["worker_sha256"] != release["images"]["worker"].split("@sha256:")[1]:
        raise Invalid("execution_pin", "release.execution.worker_sha256")
    if release["execution"]["native_sha256"] != release["native_bundle"]["sha256"]:
        raise Invalid("execution_pin", "release.execution.native_sha256")
    host = runtime["execution_host"]
    for path in (host["docker_endpoint"][7:], host["host_home"]):
        if (str(PurePosixPath(path)) != path or ".." in PurePosixPath(path).parts
                or "\\" in path):
            raise Invalid("execution_path", "runtime.execution_host")
    if not host["host_home"].startswith(runtime["mounts"]["execution"] + "/"):
        raise Invalid("execution_path", "runtime.execution_host.host_home")
    admission = runtime["admission"]
    if admission["execution"] == "qualified" and admission["attestation_sha256"] is None:
        raise Invalid("attestation_required", "runtime.admission")
    assistant = runtime["assistant"]
    if any(assistant[key] != value for key, value in release["assistant"].items()):
        raise Invalid("assistant_pin", "runtime.assistant")
    if assistant["budget"]["prior_cents"] >= assistant["budget"]["total_cents"]:
        raise Invalid("assistant_budget", "runtime.assistant.budget")
    budget = assistant["budget"]
    rate = Decimal(budget["usd_per_approved_currency"])
    converted = (Decimal(budget["approved_minor"]) * rate).to_integral_value(
        rounding=ROUND_FLOOR)
    if (rate <= 0 or converted != budget["total_cents"] or
            (budget["approved_currency"] == "USD" and rate != 1)):
        raise Invalid("assistant_conversion", "runtime.assistant.budget")
    try:
        datetime.strptime(budget["conversion_timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise Invalid("assistant_conversion", "runtime.assistant.budget") from None


def execution_configuration(release, runtime):
    """Nonsecret native inputs; live store UUIDs are recorded by explicit initialization."""
    prefix = "/srv/hyprn/staging/releases/" + release["source_commit"]
    native = prefix + "/native"
    return {
        "schema": "hyprn-cloud-execution/v1", "edition": "cloud",
        "installation_id": runtime["installation_id"],
        "store_id": runtime["store_ids"]["execution"],
        "execution_root": runtime["mounts"]["execution"],
        "host_home": runtime["execution_host"]["host_home"],
        "docker": {"endpoint": runtime["execution_host"]["docker_endpoint"]},
        "profile": "hyprn-mvp-cloud-" + runtime["installation_id"],
        "source": prefix + "/source", "native_root": native,
        "python": native + "/venv-" + release["native_environment_lock_sha256"][:16]
                  + "/bin/python",
    }


def assistant_environment(runtime):
    """Product Settings names; credentials stay in the existing private file mount."""
    binding = runtime["assistant"]
    values = {key.upper(): binding[key] for key in (
        "agent_id", "agent_version", "environment_id", "definitions_sha256",
        "configuration_sha256",
    )}
    values.update({
        "KEY_FILE": "/run/secrets/assistant-provider",
        "PLAN_FILE": "/run/hyprn-control/assistant-plan.json",
        "CONTINUITY_FILE": "/run/hyprn-control/assistant-continuity.json",
        "TOTAL_CENTS": str(binding["budget"]["total_cents"]),
        "PRIOR_CENTS": str(binding["budget"]["prior_cents"]),
        "APPROVED_MINOR": str(binding["budget"]["approved_minor"]),
        "APPROVED_CURRENCY": binding["budget"]["approved_currency"],
        "CONVERSION_DATE": binding["budget"]["conversion_timestamp"][:10],
    })
    return {"HYPRN_MVP_ASSISTANT_" + key: value for key, value in values.items()}


def cloudsql_tls_name(server_name):
    """Render the absolute DNS identity used in Cloud SQL shared-CA certificates."""
    if not isinstance(server_name, str) or not re.fullmatch(
            r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){2}'
            r'[a-z]+-[a-z]+[0-9]\.sql(?:-psa)?\.goog', server_name):
        raise Invalid("database_tls_identity")
    return server_name + "."


def application_environment(runtime):
    """Fixed product paths; host-owned identity avoids a self-referential config hash."""
    return {
        "HYPRN_MVP_DATABASE_CA_SHA256": runtime["database"]["ca_sha256"],
        "HYPRN_MVP_APPLICATION_STORE_ID": runtime["store_ids"]["application"],
        "HYPRN_MVP_HOST_IDENTITY_FILE": "/run/hyprn-control/runtime-identity.json",
        "HYPRN_MVP_ADMISSION_FILE": "/run/hyprn-control/admission.json",
        "HYPRN_MVP_ARTIFACT_ROOT": "/data/artifacts",
        "HYPRN_MVP_MODEL_URL": "http://modeling:3000/modeling/1",
        "HYPRN_MVP_MODEL_KEY_FILE": "/run/secrets/modeling-auth",
    }


def assistant_policy(runtime):
    return {
        "consumer": "app", "provider": "claude-managed-agents",
        "configuration_sha256": runtime["assistant"]["configuration_sha256"],
        "budget": runtime["assistant"]["budget"],
    }


def secret_target(component, alias):
    if component == "modeling":
        return {"modeling-auth": "/run/model.key", "modeling-rails": "/run/rails.key"}[alias]
    return "/run/secrets/" + alias


def bind(source, target, readonly=False):
    return {"type": "bind", "source": source, "target": target, "read_only": readonly,
            "bind": {"create_host_path": False}}


def container_networks():
    """Fixed non-overlapping bridge identity; host enforcement is required before start."""
    return {name: {
        "internal": name == "modeling", "enable_ipv6": False,
        "driver_opts": {"com.docker.network.bridge.name": "br-hyprn-" + name[:5]},
        "ipam": {"config": [{"subnet": f"172.29.{octet}.0/24",
                              "gateway": f"172.29.{octet}.1"}]},
    } for name, octet in (("application", 81), ("modeling", 82), ("dispatcher", 83))}


def external_networks(runtime):
    return {name: {"external": True, "name": runtime["installation_id"] + "_" + name}
            for name in container_networks()}


def service_networks(component):
    indices = {"app": "2", "modeling": "3", "dispatcher": "4"}
    value = {"modeling": {"ipv4_address": "172.29.82." + indices[component]}}
    if component == "app":
        value["application"] = {"ipv4_address": "172.29.81.2"}
    elif component == "dispatcher":
        value["dispatcher"] = {"ipv4_address": "172.29.83.2"}
    return value


def proxy_environment():
    return {"HTTPS_PROXY": "http://172.29.81.1:3128",
            "HYPRN_MVP_EGRESS_PROXY": "http://172.29.81.1:3128"}


def network_policy(runtime):
    return {"schema": "hyprn-service-network/v1", "default": "deny",
        "bridges": container_networks(),
        "database": {"address": runtime["database"]["host"], "port": 5432},
        "modeling": {"address": "172.29.82.3", "port": 3000},
        "origin": {"address": "127.0.0.1", "port": 8080, "target_port": 8000},
        "proxy": {"address": "172.29.81.1", "port": 3128,
                  "source": "172.29.81.2/32", "method": "CONNECT", "target_port": 443,
                  "hosts": ["api.anthropic.com", runtime["access"]["issuer"][8:]],
                  "deny_non_public_destinations": True},
        "metadata": "deny-all-containers", "ipv6": "disabled"}


def render(release, runtime):
    """Platform-owned topology. Product fields contain pins, never authority."""
    root = "/srv/hyprn/staging"
    limits = {
        "app": {"mem_limit": "2g", "cpus": 1.0, "pids_limit": 256},
        "modeling": {"mem_limit": "2g", "cpus": 1.0, "pids_limit": 256},
        "dispatcher": {"mem_limit": "2g", "cpus": 1.0, "pids_limit": 256},
    }
    services = {}
    for component, uid in (("app", 10002), ("dispatcher", 10002), ("modeling", 10001)):
        area = "application" if component in ("app", "dispatcher") else "modeling"
        service = {
            "image": release["images"]["app" if component == "dispatcher" else component], "user": f"{uid}:{uid}",
            "read_only": True, "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"], "restart": "no",
            "init": True, "ulimits": {"core": 0},
            "tmpfs": ["/tmp:rw,noexec,nosuid,nodev,size=134217728"],
            "networks": service_networks(component),
            "volumes": [bind(root + "/" + area + "/artifacts", "/data/artifacts")]
                if component == "dispatcher" else
                [bind(root + "/" + area, "/store" if component == "modeling" else "/data")],
            **limits[component],
        }
        environment = {}
        for alias in SECRET_CONSUMERS[component]:
            service["volumes"].append(bind(
                "/run/hyprn/secrets/" + component + "/" + alias,
                secret_target(component, alias), True,
            ))
            environment["HYPRN_SECRET_" + alias.upper().replace("-", "_") + "_FILE"] = (
                secret_target(component, alias)
            )
        if component in ("app", "dispatcher"):
            service["volumes"].append(bind(
                "/run/hyprn/control", "/run/hyprn-control", True,
            ))
            environment.update(application_environment(runtime))
            service["volumes"].append(bind(
                "/etc/hyprn/trust/cloudsql-server-ca.pem",
                "/etc/hyprn/trust/cloudsql-server-ca.pem", True,
            ))
            environment.update({
                "HYPRN_MVP_EDITION": "cloud",
                "HYPRN_MVP_DATABASE_HOST": runtime["database"]["host"],
                "HYPRN_MVP_DATABASE_PORT": "5432",
                "HYPRN_MVP_DATABASE_NAME": runtime["database"]["name"],
                "HYPRN_MVP_DATABASE_ROLE": runtime["database"]["request_role"],
                "HYPRN_MVP_DATABASE_SSLMODE": "verify-full",
                "HYPRN_MVP_DATABASE_TLS_SERVER_NAME": cloudsql_tls_name(runtime["database"]["server_name"]),
                "HYPRN_MVP_DATABASE_CA_FILE": "/etc/hyprn/trust/cloudsql-server-ca.pem",
            })
        if component == "modeling":
            environment["HYPRN_MVP_EDITION"] = "cloud"
        if component == "app":
            service["ports"] = ["127.0.0.1:8080:8000"]
            environment.update(proxy_environment())
            environment.update(assistant_environment(runtime))
            environment.update({
                "HYPRN_MVP_UI_ROOT": "/app/ui",
                "HYPRN_MVP_EXTERNAL_ORIGIN": runtime["external_origin"],
                "HYPRN_MVP_DATABASE_AUTH_ROLE": runtime["database"]["authentication_role"],
                "HYPRN_MVP_DATABASE_ASSISTANT_BACKGROUND_ROLE":
                    runtime["database"]["assistant_background_role"],
                "HYPRN_MVP_ACCESS_ISSUER": runtime["access"]["issuer"],
                "HYPRN_MVP_ACCESS_AUDIENCE": runtime["access"]["audience"],
            })
        if component == "dispatcher":
            environment.update({
                "HYPRN_MVP_DATABASE_DISPATCHER_BACKGROUND_ROLE":
                    runtime["database"]["dispatcher_background_role"],
                "HYPRN_MVP_ARTIFACT_ROOT": "/data/artifacts",
                "HYPRN_MVP_MODEL_URL": "http://modeling:3000/modeling/1",
                "HYPRN_MVP_MODEL_KEY_FILE": "/run/secrets/modeling-auth",
            })
            service.update({
                "profiles": ["host-dispatcher"],
                "entrypoint": ["python", "-B", "-m", "hyprn_mvp_app.dispatcher"],
                "command": ["--with-exports"], "stdin_open": True, "tty": False,
            })
        service["environment"] = environment
        services[component] = service
    value = {
        "schema": "hyprn-preview/v1", "environment": "staging",
        "installation": {k: runtime[k] for k in (
            "installation_id", "host_id", "disk_uuid", "store_ids", "project_number",
        )},
        "compose": {
            "services": services,
            "networks": external_networks(runtime),
        },
        "execution": {
            "kind": "host-service", "user": 10003, "root": root + "/execution",
            "native_bundle": release["native_bundle"], "application_secrets": [],
            "worker_identity": release["execution"],
            "maximum_workers": 2,
            "configuration": execution_configuration(release, runtime),
        },
        "dispatcher_bridge": {
            "owner": "execution-host", "service": "dispatcher",
            "launch": "host-owned-run-attach", "transport": "fixed-stdio",
            "lifetime": "owned-child", "public_endpoint": False,
        },
        "network_policy": network_policy(runtime),
        "dispatcher_egress": {
            "default": "deny",
            "allow": [
                {"destination": "modeling", "port": 3000, "protocol": "tcp"},
                {"destination": runtime["database"]["host"], "port": 5432, "protocol": "tcp"},
            ],
        },
        "worker": {
            "image": release["images"]["worker"], "user": "65534:65534",
            "read_only": True, "network_mode": "none", "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"], "secrets": [],
            "mem_limit": "2g", "cpus": 1.0, "pids_limit": 128,
        },
        "secret_loads": [
            {"consumer": consumer, "alias": alias,
             "resource": "projects/" + runtime["project_number"] + "/secrets/"
             + runtime["secrets"][alias]["name"] + "/versions/"
             + str(runtime["secrets"][alias]["version"]),
             "file": "/run/hyprn/secrets/" + consumer + "/" + alias}
            for consumer, aliases in SECRET_CONSUMERS.items() for alias in aliases
        ],
        "admission": runtime["admission"],
        "assistant": assistant_policy(runtime),
        "trust_files": [{
            "path": "/etc/hyprn/trust/cloudsql-server-ca.pem",
            "sha256": runtime["database"]["ca_sha256"],
        }],
        "quotas_bytes": runtime["quotas_bytes"],
        "start_requires": [
            "verified-release-bytes", "disk-and-store-identity", "writer-fencing",
            "current-host-firewall", "metadata-denied-to-containers",
            "cloudsql-tls-trust", "current-host-attestation-for-execution",
            "dispatcher-private-database-route-and-egress-policy",
            "dispatcher-host-owned-stdio-lifecycle",
            "assistant-resource-readback-and-release-definition-match",
            "assistant-shared-spending-continuity-reconciled",
        ],
    }
    check_render(value, runtime, release)
    return value


def check_render(value, runtime, release):
    """Audit the effective renderer output, not just the original descriptor."""
    services = value["compose"]["services"]
    if set(services) != {"app", "dispatcher", "modeling"}:
        raise Invalid("render_policy")
    if value.get("assistant") != assistant_policy(runtime):
        raise Invalid("render_policy")
    if not {"assistant-resource-readback-and-release-definition-match",
            "assistant-shared-spending-continuity-reconciled"}.issubset(
                value.get("start_requires", [])):
        raise Invalid("render_policy")
    for component, service in {**services, "worker": value["worker"],
                               "execution": value["execution"]}.items():
        actual = {key: setting for key, setting in service.get("environment", {}).items()
                  if key.startswith("HYPRN_MVP_ASSISTANT_")}
        if actual != (assistant_environment(runtime) if component == "app" else {}):
            raise Invalid("render_policy")
    for component, uid in (("app", 10002), ("dispatcher", 10002), ("modeling", 10001)):
        service = services[component]
        allowed_fields = {
            "image", "user", "read_only", "cap_drop", "security_opt", "restart", "init",
            "ulimits", "tmpfs", "networks", "volumes", "mem_limit", "cpus",
            "pids_limit", "environment",
        }
        if component == "app":
            allowed_fields.add("ports")
            if service.get("ports") != ["127.0.0.1:8080:8000"]:
                raise Invalid("render_policy")
            if any(service["environment"].get(k) != v for k, v in proxy_environment().items()):
                raise Invalid("render_policy")
        if component == "dispatcher":
            allowed_fields |= {"profiles", "entrypoint", "command", "stdin_open", "tty"}
            if (service.get("profiles") != ["host-dispatcher"] or
                    service.get("entrypoint") !=
                    ["python", "-B", "-m", "hyprn_mvp_app.dispatcher"] or
                    service.get("command") != ["--with-exports"] or
                    service.get("stdin_open") is not True or service.get("tty") is not False):
                raise Invalid("render_policy")
        if set(service) != allowed_fields or service["user"] != f"{uid}:{uid}":
            raise Invalid("render_policy")
        if (service["image"] != release["images"]["app" if component == "dispatcher" else component] or
                service["cap_drop"] != ["ALL"] or not service["read_only"] or
                service["security_opt"] != ["no-new-privileges:true"] or
                service["restart"] != "no"):
            raise Invalid("render_policy")
        area = "application" if component in ("app", "dispatcher") else "modeling"
        expected_mounts = (
            [bind(runtime["mounts"][area] + "/artifacts", "/data/artifacts")]
            if component == "dispatcher" else
            [bind(runtime["mounts"][area], "/store" if component == "modeling" else "/data")]
        )
        expected_mounts += [
            bind(runtime["mounts"]["secrets"] + "/" + component + "/" + alias,
                 secret_target(component, alias), True)
            for alias in SECRET_CONSUMERS[component]
        ]
        if component in ("app", "dispatcher"):
            expected_mounts.append(bind(
                "/run/hyprn/control", "/run/hyprn-control", True,
            ))
            for key, setting in application_environment(runtime).items():
                if service["environment"].get(key) != setting:
                    raise Invalid("render_policy")
            if component == "app" and service["environment"].get("HYPRN_MVP_UI_ROOT") != "/app/ui":
                raise Invalid("render_policy")
            expected_mounts.append(bind(
                "/etc/hyprn/trust/cloudsql-server-ca.pem",
                "/etc/hyprn/trust/cloudsql-server-ca.pem", True,
            ))
        if component == "modeling" and service["environment"] != {
                "HYPRN_MVP_EDITION": "cloud",
                **{"HYPRN_SECRET_" + alias.upper().replace("-", "_") + "_FILE":
                   secret_target(component, alias) for alias in SECRET_CONSUMERS[component]}}:
            raise Invalid("render_policy")
        if service["volumes"] != expected_mounts:
            raise Invalid("render_policy")
        expected_networks = service_networks(component)
        if service["networks"] != expected_networks:
            raise Invalid("render_policy")
    if value["execution"].get("configuration") != execution_configuration(release, runtime):
        raise Invalid("render_policy")
    if value["execution"]["application_secrets"]:
        raise Invalid("render_policy")
    if value["compose"]["networks"] != external_networks(runtime):
        raise Invalid("render_policy")
    if value.get("network_policy") != network_policy(runtime):
        raise Invalid("render_policy")
    expected_loads = [
        {"consumer": consumer, "alias": alias,
         "resource": "projects/" + runtime["project_number"] + "/secrets/"
         + runtime["secrets"][alias]["name"] + "/versions/"
         + str(runtime["secrets"][alias]["version"]),
         "file": "/run/hyprn/secrets/" + consumer + "/" + alias}
        for consumer, aliases in SECRET_CONSUMERS.items() for alias in aliases
    ]
    if value["secret_loads"] != expected_loads:
        raise Invalid("render_policy")
    environment = services["dispatcher"]["environment"]
    expected_environment = {
        "HYPRN_SECRET_" + alias.upper().replace("-", "_") + "_FILE":
            "/run/secrets/" + alias for alias in SECRET_CONSUMERS["dispatcher"]
    }
    expected_environment.update({
        "HYPRN_MVP_EDITION": "cloud",
        "HYPRN_MVP_DATABASE_HOST": runtime["database"]["host"],
        "HYPRN_MVP_DATABASE_PORT": "5432",
        "HYPRN_MVP_DATABASE_NAME": runtime["database"]["name"],
        "HYPRN_MVP_DATABASE_ROLE": runtime["database"]["request_role"],
        "HYPRN_MVP_DATABASE_SSLMODE": "verify-full",
        "HYPRN_MVP_DATABASE_TLS_SERVER_NAME": cloudsql_tls_name(runtime["database"]["server_name"]),
        "HYPRN_MVP_DATABASE_CA_FILE": "/etc/hyprn/trust/cloudsql-server-ca.pem",
        "HYPRN_MVP_DATABASE_DISPATCHER_BACKGROUND_ROLE":
            runtime["database"]["dispatcher_background_role"],
        "HYPRN_MVP_ARTIFACT_ROOT": "/data/artifacts",
        "HYPRN_MVP_MODEL_URL": "http://modeling:3000/modeling/1",
        "HYPRN_MVP_MODEL_KEY_FILE": "/run/secrets/modeling-auth",
    })
    expected_environment.update(application_environment(runtime))
    if environment != expected_environment:
        raise Invalid("render_policy")
    if (value["dispatcher_bridge"] != {
            "owner": "execution-host", "service": "dispatcher",
            "launch": "host-owned-run-attach", "transport": "fixed-stdio",
            "lifetime": "owned-child", "public_endpoint": False} or
            value["dispatcher_egress"] != {
                "default": "deny", "allow": [
                    {"destination": "modeling", "port": 3000, "protocol": "tcp"},
                    {"destination": runtime["database"]["host"], "port": 5432,
                     "protocol": "tcp"},
                ]}):
        raise Invalid("render_policy")
    worker = value["worker"]
    if worker["network_mode"] != "none" or worker["secrets"] or not worker["read_only"]:
        raise Invalid("render_policy")


def check_desired(desired, release, runtime, config_hash):
    if (desired["project_number"] != runtime["project_number"] or
            desired["platform_commit"] != runtime["platform_commit"]):
        raise Invalid("identity_mismatch", "desired")
    if desired["release_sha256"] != digest(release):
        raise Invalid("release_pin", "desired")
    if desired["config_sha256"] != config_hash:
        raise Invalid("config_pin", "desired")
    if desired["artifacts"] != {k: release[k] for k in (
            "images", "native_bundle", "ui_manifest_sha256")}:
        raise Invalid("artifact_mismatch", "desired")
    if desired["evidence"] != release["evidence"]:
        raise Invalid("evidence_mismatch", "desired")


def check_bundle(path, specification):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != specification["size_bytes"]:
            raise Invalid("bundle_size")
        if info.st_size > MAX_BUNDLE_BYTES:
            raise Invalid("bundle_size")
        hashed = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hashed.update(block)
        if hashed.hexdigest() != specification["sha256"]:
            raise Invalid("bundle_digest")
        stream.seek(0)
        total, count = 0, 0
        entries = {}
        parents_with_children = set()
        try:
            with tarfile.open(fileobj=stream, mode="r|*") as archive:
                for member in archive:
                    count += 1
                    if count > MAX_MEMBERS:
                        raise Invalid("unsafe_bundle")
                    path = PurePosixPath(member.name)
                    parts = member.name.rstrip("/").split("/")
                    if (not member.name or len(member.name) > 512 or
                            path.is_absolute() or "\\" in member.name or
                            any(part in ("", ".", "..") for part in parts) or
                            any(ord(c) < 32 for c in member.name) or
                            not (member.isfile() or member.isdir()) or
                            member.issparse() or member.mode & 0o7000):
                        raise Invalid("unsafe_bundle")
                    normalized = str(path)
                    if normalized in entries or any(
                            entries.get(str(parent)) == "file" for parent in path.parents):
                        raise Invalid("unsafe_bundle")
                    if member.isfile() and normalized in parents_with_children:
                        raise Invalid("unsafe_bundle")
                    entries[normalized] = "file" if member.isfile() else "directory"
                    parents_with_children.update(str(parent) for parent in path.parents)
                    total += member.size
                    if member.size < 0 or total > MAX_EXPANDED_BYTES:
                        raise Invalid("unsafe_bundle")
                    if total > max(1024 * 1024, info.st_size * 100):
                        raise Invalid("unsafe_bundle")
                if not entries:
                    raise Invalid("unsafe_bundle")
        except (tarfile.TarError, EOFError, ValueError):
            raise Invalid("unsafe_bundle") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["validate", "preview"])
    for kind in ("workload", "release", "runtime"):
        parser.add_argument("--" + kind, required=True)
    parser.add_argument("--desired")
    parser.add_argument("--bundle", help="Verify the pinned local tar bundle without extraction")
    args = parser.parse_args()
    try:
        documents = {k: read_json(getattr(args, k)) for k in ("workload", "release", "runtime")}
        if args.desired:
            documents["desired"] = read_json(args.desired)
        check_documents(documents)
        preview = render(documents["release"], documents["runtime"])
        config_hash = digest(preview)
        if args.desired:
            check_desired(documents["desired"], documents["release"],
                          documents["runtime"], config_hash)
        if args.bundle:
            check_bundle(args.bundle, documents["release"]["native_bundle"])
        result = {"valid": True, "config_sha256": config_hash,
                  "release_sha256": digest(documents["release"]),
                  "bundle_verified": bool(args.bundle),
                  "artifact_bytes_verified": False}
        if args.operation == "preview":
            result["preview"] = preview
        print(canonical(result).decode())
        return 0
    except Invalid as error:
        print(json.dumps({"error": error.code, "location": error.location}), file=sys.stderr)
    except (OSError, RecursionError):
        # No raw path, input content, secret value, or traceback enters diagnostics.
        print(json.dumps({"error": "input_unreadable", "location": "input"}), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
