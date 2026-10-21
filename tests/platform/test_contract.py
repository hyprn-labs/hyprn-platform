"""Exercise the public contract CLI against isolated, non-secret inputs."""
import copy
import hashlib
import io
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "host/contract.py"


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(prefix="hyprn-contract-")
        self.addCleanup(self.scope.cleanup)
        self.directory = Path(self.scope.name)
        self.fixtures = json.loads((ROOT / "contracts/v1/fixtures.json").read_text())
        self.documents = copy.deepcopy(self.fixtures["valid"])

    def command(self, operation="preview", desired=False, bundle=None, raw=None):
        args = [sys.executable, "-B", str(CLI), operation]
        for kind in ("workload", "release", "runtime", "desired"):
            if kind == "desired" and not desired:
                continue
            path = self.directory / (kind + ".yaml")
            path.write_text(raw[kind] if raw and kind in raw else json.dumps(self.documents[kind]))
            args += ["--" + kind, str(path)]
        if bundle:
            args += ["--bundle", str(bundle)]
        return subprocess.run(args, capture_output=True, text=True, cwd=ROOT)

    def success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def rejected(self, result, code):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["error"], code)

    def test_valid_preview_is_deterministic_and_separates_secret_authority(self):
        first = self.success(self.command())
        self.assertEqual(first, self.success(self.command()))
        rendered = first["preview"]
        app = rendered["compose"]["services"]["app"]
        modeling = rendered["compose"]["services"]["modeling"]
        self.assertEqual(app["user"], "10002:10002")
        self.assertEqual(modeling["user"], "10001:10001")
        self.assertEqual(app["cap_drop"], ["ALL"])
        self.assertTrue(app["read_only"])
        self.assertEqual(app["ports"], ["127.0.0.1:8080:8000"])
        self.assertNotIn("privileged", app)
        self.assertEqual(rendered["worker"]["network_mode"], "none")
        self.assertEqual(rendered["worker"]["secrets"], [])
        app_secrets = [m["target"] for m in app["volumes"] if "/secrets/" in m["target"]]
        self.assertIn("/run/secrets/assistant-provider", app_secrets)
        self.assertIn("/run/secrets/db-app-auth", app_secrets)
        self.assertEqual(app["environment"]["HYPRN_MVP_DATABASE_AUTH_ROLE"], "hyprn_auth")
        self.assertNotIn("/run/secrets/db-app-migration", app_secrets)
        self.assertNotIn("/run/secrets/db-app-backup", app_secrets)
        self.assertNotIn("assistant-provider", json.dumps(modeling))
        self.assertEqual(rendered["execution"]["application_secrets"], [])
        self.assertEqual(app["environment"]["HYPRN_MVP_DATABASE_SSLMODE"], "verify-full")
        self.assertEqual(app["environment"]["HYPRN_MVP_DATABASE_TLS_SERVER_NAME"],
                         self.documents["runtime"]["database"]["server_name"] + ".")
        self.assertTrue(any(m["read_only"] and m["target"].endswith("server-ca.pem")
                            for m in app["volumes"]))
        encoded = json.dumps(rendered, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(first["config_sha256"], hashlib.sha256(encoded).hexdigest())

    def test_private_routes_and_proxy_are_bound_to_the_exact_runtime(self):
        rendered = self.success(self.command())["preview"]
        services = rendered["compose"]["services"]
        self.assertFalse(rendered['network_policy']['bridges']['dispatcher']['internal'])
        self.assertTrue(rendered['network_policy']['bridges']['modeling']['internal'])
        for network in rendered['network_policy']['bridges'].values():
            bridge = network['driver_opts']['com.docker.network.bridge.name']
            self.assertTrue(bridge.startswith('br-'))
            self.assertLessEqual(len(bridge), 15)
        policy = rendered["network_policy"]
        self.assertEqual(policy["database"]["address"], self.documents["runtime"]["database"]["host"])
        self.assertEqual(policy["proxy"]["hosts"], ["api.anthropic.com", "fixture.cloudflareaccess.com"])
        self.assertEqual(services["app"]["environment"]["HYPRN_MVP_EGRESS_PROXY"],
                         "http://172.29.81.1:3128")
        for name in ("dispatcher", "modeling"):
            self.assertNotIn("HTTPS_PROXY", services[name]["environment"])
            self.assertNotIn("ports", services[name])
        self.assertEqual(services["modeling"]["networks"],
                         {"modeling": {"ipv4_address": "172.29.82.3"}})

    def test_runtime_controls_are_read_only_and_not_given_to_modeling(self):
        services = self.success(self.command())["preview"]["compose"]["services"]
        for name in ("app", "dispatcher"):
            service = services[name]
            controls = [m for m in service["volumes"] if m["target"] == "/run/hyprn-control"]
            self.assertEqual(len(controls), 1)
            self.assertTrue(controls[0]["read_only"])
            self.assertFalse(controls[0]["bind"]["create_host_path"])
            self.assertEqual(service["environment"]["HYPRN_MVP_DATABASE_CA_SHA256"],
                             self.documents["runtime"]["database"]["ca_sha256"])
            self.assertEqual(service["environment"]["HYPRN_MVP_APPLICATION_STORE_ID"],
                             self.documents["runtime"]["store_ids"]["application"])
            self.assertEqual(service["environment"]["HYPRN_MVP_HOST_IDENTITY_FILE"],
                             "/run/hyprn-control/runtime-identity.json")
        modeling = services["modeling"]
        self.assertEqual({m["target"] for m in modeling["volumes"]},
                         {"/store", "/run/model.key", "/run/rails.key"})
        self.assertEqual(modeling["environment"]["HYPRN_MVP_EDITION"], "cloud")
        self.assertNotIn("hyprn-control", json.dumps(modeling))
        self.assertNotIn("HYPRN_MVP_ASSISTANT_PLAN_FILE", services["dispatcher"]["environment"])
        self.assertEqual(services["app"]["environment"]["HYPRN_MVP_UI_ROOT"], "/app/ui")

    def test_execution_projection_is_release_pinned_without_application_credentials(self):
        preview = self.success(self.command())["preview"]
        config = preview["execution"]["configuration"]
        prefix = "/srv/hyprn/staging/releases/" + self.documents["release"]["source_commit"]
        self.assertEqual(config["source"], prefix + "/source")
        self.assertEqual(config["native_root"], prefix + "/native")
        self.assertEqual(config["python"], prefix + "/native/venv-" +
                         self.documents["release"]["native_environment_lock_sha256"][:16] +
                         "/bin/python")
        self.assertEqual(config["store_id"], self.documents["runtime"]["store_ids"]["execution"])
        self.assertEqual(config["docker"], {"endpoint": "unix:///var/run/docker.sock"})
        self.assertNotIn("secrets", config)
        self.assertNotIn("database", config)
        self.assertNotIn("config_sha256", config)

    def test_execution_host_refuses_network_engine_and_noncanonical_paths(self):
        for field, value, code in (
            ("docker_endpoint", "tcp://127.0.0.1:2375", "schema_value"),
            ("docker_endpoint", "unix:///run/../docker.sock", "execution_path"),
            ("host_home", "/srv/hyprn/staging/execution/../other", "execution_path"),
            ("host_home", "/outside", "execution_path"),
        ):
            with self.subTest(field=field, value=value):
                self.documents = copy.deepcopy(self.fixtures["valid"])
                self.documents["runtime"]["execution_host"][field] = value
                self.rejected(self.command(), code)

    def test_dispatcher_has_only_scoped_credentials_and_host_owned_bridge(self):
        preview = self.success(self.command())["preview"]
        services = preview["compose"]["services"]
        self.assertIn("dispatcher", services)
        dispatcher = services["dispatcher"]
        self.assertEqual(dispatcher["image"], services["app"]["image"])
        self.assertEqual(dispatcher["user"], "10002:10002")
        aliases = {
            row["consumer"]: {entry["alias"] for entry in preview["secret_loads"]
                              if entry["consumer"] == row["consumer"]}
            for row in preview["secret_loads"]
        }
        self.assertEqual(aliases["dispatcher"],
                         {"db-app-request", "db-dispatcher-background", "modeling-auth"})
        self.assertIn("db-assistant-background", aliases["app"])
        self.assertNotIn("db-dispatcher-background", aliases["app"])
        environment = dispatcher["environment"]
        self.assertEqual(environment["HYPRN_MVP_DATABASE_DISPATCHER_BACKGROUND_ROLE"],
                         "hyprn_dispatcher_background")
        self.assertNotIn("HYPRN_MVP_DATABASE_AUTH_ROLE", environment)
        self.assertEqual(services["app"]["environment"]["HYPRN_MVP_DATABASE_ASSISTANT_BACKGROUND_ROLE"],
                         "hyprn_assistant_background")
        self.assertEqual(dispatcher["networks"], {"modeling": {"ipv4_address": "172.29.82.4"},
                                               "dispatcher": {"ipv4_address": "172.29.83.2"}})
        self.assertFalse(preview['network_policy']['bridges']['dispatcher']['internal'])
        self.assertEqual(dispatcher["profiles"], ["host-dispatcher"])
        self.assertEqual(dispatcher["entrypoint"],
                         ["python", "-B", "-m", "hyprn_mvp_app.dispatcher"])
        self.assertEqual(dispatcher["command"], ["--with-exports"])
        self.assertTrue(dispatcher["stdin_open"])
        self.assertFalse(dispatcher["tty"])
        self.assertEqual(preview["dispatcher_bridge"], {
            "owner": "execution-host", "service": "dispatcher",
            "launch": "host-owned-run-attach", "transport": "fixed-stdio",
            "lifetime": "owned-child", "public_endpoint": False,
        })
        self.assertEqual(preview["dispatcher_egress"], {
            "default": "deny", "allow": [
                {"destination": "modeling", "port": 3000, "protocol": "tcp"},
                {"destination": self.documents["runtime"]["database"]["host"],
                 "port": 5432, "protocol": "tcp"},
            ],
        })
        self.assertIn("dispatcher-private-database-route-and-egress-policy",
                      preview["start_requires"])
        writable = [m for m in dispatcher["volumes"] if not m["read_only"]]
        self.assertEqual([(m["source"], m["target"]) for m in writable],
                         [("/srv/hyprn/staging/application/artifacts", "/data/artifacts")])
        self.assertNotIn("ports", dispatcher)
        self.assertNotIn("assistant-provider", json.dumps(dispatcher))
        self.assertNotIn("docker.sock", json.dumps(services))
        self.assertEqual(preview["execution"]["application_secrets"], [])
        self.assertEqual(preview["worker"]["secrets"], [])

    def test_assistant_has_exact_release_bound_settings_and_shared_accounting(self):
        preview = self.success(self.command())["preview"]
        environment = preview["compose"]["services"]["app"]["environment"]
        self.assertIn("HYPRN_MVP_ASSISTANT_KEY_FILE", environment)
        binding = self.documents["runtime"]["assistant"]
        expected = {
            "KEY_FILE": "/run/secrets/assistant-provider",
            "PLAN_FILE": "/run/hyprn-control/assistant-plan.json",
            "CONTINUITY_FILE": "/run/hyprn-control/assistant-continuity.json",
            "AGENT_ID": binding["agent_id"],
            "AGENT_VERSION": binding["agent_version"],
            "ENVIRONMENT_ID": binding["environment_id"],
            "DEFINITIONS_SHA256": binding["definitions_sha256"],
            "CONFIGURATION_SHA256": binding["configuration_sha256"],
            "TOTAL_CENTS": str(binding["budget"]["total_cents"]),
            "PRIOR_CENTS": str(binding["budget"]["prior_cents"]),
            "APPROVED_MINOR": str(binding["budget"]["approved_minor"]),
            "APPROVED_CURRENCY": binding["budget"]["approved_currency"],
            "CONVERSION_DATE": binding["budget"]["conversion_timestamp"][:10],
        }
        self.assertEqual({k.removeprefix("HYPRN_MVP_ASSISTANT_"): v
                          for k, v in environment.items()
                          if k.startswith("HYPRN_MVP_ASSISTANT_")}, expected)
        self.assertEqual(preview["assistant"], {
            "consumer": "app", "provider": "claude-managed-agents",
            "configuration_sha256": binding["configuration_sha256"],
            "budget": binding["budget"],
        })
        self.assertIn("assistant-resource-readback-and-release-definition-match",
                      preview["start_requires"])
        self.assertIn("assistant-shared-spending-continuity-reconciled",
                      preview["start_requires"])
        for component in ("dispatcher", "modeling"):
            self.assertNotIn("HYPRN_MVP_ASSISTANT_",
                             json.dumps(preview["compose"]["services"][component]))
        for component in ("execution", "worker"):
            self.assertNotIn("HYPRN_MVP_ASSISTANT_", json.dumps(preview[component]))

    def test_background_roles_and_aliases_are_required_and_closed(self):
        for parent, key in (("database", "assistant_background_role"),
                            ("database", "dispatcher_background_role"),
                            ("secrets", "db-assistant-background"),
                            ("secrets", "db-dispatcher-background")):
            with self.subTest(parent=parent, key=key):
                self.documents = copy.deepcopy(self.fixtures["valid"])
                del self.documents["runtime"][parent][key]
                self.rejected(self.command(), "missing_field")
        self.documents = copy.deepcopy(self.fixtures["valid"])
        self.documents["runtime"]["secrets"]["dispatcher-provider"] = {
            "name": "hyprn-staging-dispatcher-provider", "version": 1,
        }
        self.rejected(self.command(), "unknown_field")

    def test_assistant_binding_and_accounting_have_no_implicit_defaults(self):
        for document, path in (
            ("runtime", ["assistant"]), ("release", ["assistant"]),
            *(("runtime", ["assistant", key])
              for key in self.documents["runtime"]["assistant"]),
            *(("runtime", ["assistant", "budget", key])
              for key in self.documents["runtime"]["assistant"]["budget"]),
            *(("release", ["assistant", key])
              for key in self.documents["release"]["assistant"]),
        ):
            with self.subTest(document=document, path=path):
                self.documents = copy.deepcopy(self.fixtures["valid"])
                target = self.documents[document]
                for key in path[:-1]:
                    target = target[key]
                del target[path[-1]]
                self.rejected(self.command(), "missing_field")

    def test_assistant_rebinding_changes_config_and_invalidates_desired_pin(self):
        original = self.success(self.command())["config_sha256"]
        for path, setting in (
            (["agent_id"], "agent_other"), (["agent_version"], "8"),
            (["environment_id"], "env_other"),
            (["budget", "prior_cents"], 126),
        ):
            with self.subTest(path=path):
                self.documents = copy.deepcopy(self.fixtures["valid"])
                target = self.documents["runtime"]["assistant"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = setting
                self.assertNotEqual(self.success(self.command())["config_sha256"], original)
                self.rejected(self.command("validate", desired=True), "config_pin")

    def test_shared_approval_conversion_is_explicit_and_never_increases_by_rounding(self):
        budget = self.documents["runtime"]["assistant"]["budget"]
        self.assertEqual((budget["approved_minor"], budget["approved_currency"]), (10000, "EUR"))
        budget["usd_per_approved_currency"] = "1.12345678"
        budget["total_cents"] = 11234
        preview = self.success(self.command())["preview"]
        environment = preview["compose"]["services"]["app"]["environment"]
        self.assertEqual(environment["HYPRN_MVP_ASSISTANT_TOTAL_CENTS"], "11234")
        self.assertEqual(environment["HYPRN_MVP_ASSISTANT_APPROVED_MINOR"], "10000")
        self.assertEqual(environment["HYPRN_MVP_ASSISTANT_APPROVED_CURRENCY"], "EUR")
        budget["total_cents"] = 11235
        self.rejected(self.command(), "assistant_conversion")
        budget.update(approved_minor=15000, total_cents=15000,
                      approved_currency="USD", usd_per_approved_currency="1.0")
        self.success(self.command())
        budget.update(total_cents=16500, usd_per_approved_currency="1.1")
        self.rejected(self.command(), "assistant_conversion")

    def test_effective_render_preserves_assistant_settings_and_accounting_gate(self):
        spec = importlib.util.spec_from_file_location("contract", CLI)
        contract = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(contract)
        baseline = self.success(self.command())["preview"]
        mutations = [
            lambda p: p["compose"]["services"]["app"]["environment"].update(
                HYPRN_MVP_ASSISTANT_KEY_FILE="/tmp/key"),
            lambda p: p["compose"]["services"]["app"]["environment"].update(
                HYPRN_MVP_ASSISTANT_PRIOR_CENTS="0"),
            lambda p: p["compose"]["services"]["app"]["environment"].update(
                HYPRN_MVP_ASSISTANT_SESSION_CENTS="100"),
            lambda p: p["compose"]["services"]["modeling"]["environment"].update(
                HYPRN_MVP_ASSISTANT_KEY_FILE="/run/secrets/assistant-provider"),
            lambda p: p["worker"].update(environment={"HYPRN_MVP_ASSISTANT_KEY_FILE": "key"}),
            lambda p: p["assistant"]["budget"].update(prior_spending_policy="reset"),
            lambda p: p["start_requires"].remove("assistant-shared-spending-continuity-reconciled"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                preview = copy.deepcopy(baseline)
                mutate(preview)
                with self.assertRaises(contract.Invalid) as caught:
                    contract.check_render(preview, self.documents["runtime"],
                                          self.documents["release"])
                self.assertEqual(caught.exception.code, "render_policy")

    def test_effective_render_rejects_dispatcher_authority_expansion(self):
        spec = importlib.util.spec_from_file_location("contract", CLI)
        contract = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(contract)
        baseline = self.success(self.command())["preview"]
        mutations = [
            lambda p: p["compose"]["services"]["dispatcher"].update(ports=["8000:8000"]),
            lambda p: p["compose"]["services"]["dispatcher"].update(command=["arbitrary"]),
            lambda p: p["compose"]["services"]["dispatcher"]["networks"].update({"application": {}}),
            lambda p: p["compose"]["services"]["dispatcher"]["volumes"].append(
                {"source": "/var/run/docker.sock", "target": "/var/run/docker.sock"}),
            lambda p: p["compose"]["services"]["dispatcher"]["environment"].update(
                HYPRN_SECRET_ASSISTANT_PROVIDER_FILE="/run/secrets/assistant-provider"),
            lambda p: p["compose"]["services"]["dispatcher"]["environment"].update(
                HYPRN_MVP_DATABASE_ROLE="hyprn_migration"),
            lambda p: p["compose"]["services"]["dispatcher"]["environment"].update(
                HYPRN_MVP_DATABASE_SSLMODE="disable"),
            lambda p: p["secret_loads"].append(
                {"consumer": "dispatcher", "alias": "assistant-provider"}),
            lambda p: p["execution"]["application_secrets"].append("db-app-request"),
            lambda p: p["dispatcher_egress"].update(default="allow"),
            lambda p: p["dispatcher_bridge"].update(transport="tcp"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                preview = copy.deepcopy(baseline)
                mutate(preview)
                with self.assertRaises(contract.Invalid) as caught:
                    contract.check_render(preview, self.documents["runtime"],
                                          self.documents["release"])
                self.assertEqual(caught.exception.code, "render_policy")

    def test_negative_fixtures_fail_before_rendering(self):
        for row in self.fixtures["negative"]:
            with self.subTest(row["name"]):
                self.documents = copy.deepcopy(self.fixtures["valid"])
                target = self.documents[row["document"]]
                for key in row["path"][:-1]:
                    target = target[key]
                target[row["path"][-1]] = row["value"]
                self.rejected(self.command(desired=row["document"] == "desired"), row["code"])
                if row["value"] == "secret-marker":
                    result = self.command()
                    self.assertNotIn("secret-marker", result.stdout + result.stderr)

    def test_duplicate_keys_nonfinite_and_yaml_are_rejected_without_echoing_values(self):
        for source, code in [
            ('{"schema":"runtime/v1","schema":"secret-marker"}', "duplicate_key"),
            ('{"secret-marker":NaN}', "invalid_json"),
            ('{"secret-marker":Infinity}', "invalid_json"),
            ("!!python/object/apply:os.system ['secret-marker']", "invalid_json"),
        ]:
            with self.subTest(code=code, source=source):
                result = self.command(raw={"runtime": source})
                self.rejected(result, code)
                self.assertNotIn("secret-marker", result.stderr)

    def test_desired_pins_release_artifacts_configuration_and_environment(self):
        preview = self.success(self.command())
        self.documents["desired"]["config_sha256"] = preview["config_sha256"]
        self.success(self.command("validate", desired=True))
        for path, value, code in [
            (["config_sha256"], "0" * 64, "config_pin"),
            (["release_sha256"], "0" * 64, "release_pin"),
            (["project_number"], "999999999999", "identity_mismatch"),
            (["platform_commit"], "c" * 40, "identity_mismatch"),
            (["artifacts", "ui_manifest_sha256"], "0" * 64, "artifact_mismatch"),
            (["evidence", "tests"], "0" * 64, "evidence_mismatch"),
        ]:
            with self.subTest(path=path):
                saved = copy.deepcopy(self.documents["desired"])
                target = self.documents["desired"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.rejected(self.command(desired=True), code)
                self.documents["desired"] = saved

    def test_only_documented_cloudsql_dns_identities_are_accepted(self):
        for suffix in ("sql.goog", "sql-psa.goog"):
            with self.subTest(suffix=suffix):
                server = "1a23b4cd5e67.1a2b345c6d27.europe-west1." + suffix
                self.documents["runtime"]["database"]["server_name"] = server
                preview = self.success(self.command())["preview"]
                app = preview["compose"]["services"]["app"]
                self.assertEqual(app["environment"]["HYPRN_MVP_DATABASE_TLS_SERVER_NAME"], server + ".")
                self.assertEqual(app["environment"]["HYPRN_MVP_DATABASE_SSLMODE"], "verify-full")
        for server in (
            "metadata.google.internal", "10.20.0.3", "attacker.example",
            "a.b.europe-west1.sql-psa.goog.attacker.example",
            "a..europe-west1.sql-psa.goog", "a.b.europe-west1.sql-evil.goog",
            "-a.b.europe-west1.sql-psa.goog", "a.b.europe-west1.sql-psa.goog.",
        ):
            with self.subTest(server=server):
                self.documents["runtime"]["database"]["server_name"] = server
                self.rejected(self.command(), "schema_value")

    def test_store_compatibility_and_registry_are_enforced(self):
        self.documents["release"]["stores"]["application"]["write_version"] = 2
        self.rejected(self.command(), "store_compatibility")
        self.documents = copy.deepcopy(self.fixtures["valid"])
        self.documents["release"]["images"]["app"] = (
            "attacker.example/image@sha256:" + "a" * 64
        )
        self.rejected(self.command(), "registry_mismatch")

    def archive(self, entries):
        path = self.directory / "bundle.tar"
        with tarfile.open(path, "w") as archive:
            for name, kind, size in entries:
                item = tarfile.TarInfo(name)
                item.type = kind
                item.mode = 0o644
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    item.linkname = "/etc/passwd"
                if kind == tarfile.REGTYPE:
                    item.size = size
                    archive.addfile(item, io.BytesIO(b"x" * size))
                else:
                    archive.addfile(item)
        data = path.read_bytes()
        self.documents["release"]["native_bundle"] = {
            "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)
        }
        self.documents["release"]["execution"]["native_sha256"] = hashlib.sha256(data).hexdigest()
        return path

    def test_bundle_is_verified_without_extraction(self):
        path = self.archive([("bin/python", tarfile.REGTYPE, 4)])
        result = self.success(self.command(bundle=path))
        self.assertTrue(result["bundle_verified"])
        self.assertFalse((self.directory / "bin").exists())
        self.documents["release"]["native_bundle"]["sha256"] = "0" * 64
        self.documents["release"]["execution"]["native_sha256"] = "0" * 64
        self.rejected(self.command(bundle=path), "bundle_digest")

    def test_unsafe_bundle_members_fail_closed(self):
        cases = [
            [("../escape", tarfile.REGTYPE, 1)],
            [("/absolute", tarfile.REGTYPE, 1)],
            [("a/../escape", tarfile.REGTYPE, 1)],
            [("a\\escape", tarfile.REGTYPE, 1)],
            [("link", tarfile.SYMTYPE, 0)],
            [("link", tarfile.LNKTYPE, 0)],
            [("device", tarfile.CHRTYPE, 0)],
            [("duplicate", tarfile.REGTYPE, 1), ("duplicate", tarfile.REGTYPE, 1)],
            [("file", tarfile.REGTYPE, 1), ("file/child", tarfile.REGTYPE, 1)],
        ]
        for entries in cases:
            with self.subTest(entries=entries):
                self.rejected(self.command(bundle=self.archive(entries)), "unsafe_bundle")

    def test_schema_has_closed_definitions_and_pins_exact_bytes(self):
        schema_path = ROOT / "contracts/v1/deployment.schema.json"
        schema = json.loads(schema_path.read_text())
        for name in ("workload", "release", "runtime", "desired"):
            self.assertFalse(schema["$defs"][name]["additionalProperties"])
        self.assertEqual(self.documents["release"]["platform_contract"]["schema_sha256"],
                         hashlib.sha256(schema_path.read_bytes()).hexdigest())
        self.success(self.command("validate", desired=True))

    def test_numbers_missing_fields_and_nested_input_fail_without_tracebacks(self):
        for document, path, value, code in [
            ("runtime", ["secrets", "db-app-request", "version"], True, "schema_type"),
            ("release", ["native_bundle", "size_bytes"], 1.25, "schema_type"),
            ("release", ["source_inventory_sha256"], "../untrusted", "schema_value"),
            ("runtime", ["database", "request_role"], "hyprn_migration", "schema_value"),
            ("runtime", ["database", "authentication_role"], "hyprn_migration", "schema_value"),
            ("runtime", ["database", "sslmode"], "disable", "schema_value"),
            ("runtime", ["database", "server_name"], "metadata.google.internal", "schema_value"),
            ("release", ["platform_contract", "workload_sha256"], "0" * 64, "workload_pin"),
        ]:
            with self.subTest(path=path):
                self.documents = copy.deepcopy(self.fixtures["valid"])
                target = self.documents[document]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.rejected(self.command(), code)
        self.documents = copy.deepcopy(self.fixtures["valid"])
        del self.documents["runtime"]["database"]["ca_sha256"]
        self.rejected(self.command(), "missing_field")
        self.documents = copy.deepcopy(self.fixtures["valid"])
        self.rejected(self.command(raw={"runtime": "[" * 1500 + "]" * 1500}), "invalid_json")

    def test_compressed_expansion_and_bundle_symlinks_are_rejected(self):
        path = self.directory / "compressed.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            item = tarfile.TarInfo("large")
            item.size = 2 * 1024 * 1024
            archive.addfile(item, io.BytesIO(b"x" * item.size))
        data = path.read_bytes()
        self.documents["release"]["native_bundle"] = {
            "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)
        }
        self.documents["release"]["execution"]["native_sha256"] = hashlib.sha256(data).hexdigest()
        self.rejected(self.command(bundle=path), "unsafe_bundle")
        link = self.directory / "link.tar"
        link.symlink_to(path)
        self.rejected(self.command(bundle=link), "input_unreadable")

    def test_runner_unknown_and_missing_groups_fail(self):
        runner = ROOT / "tests/platform/run.sh"
        missing = [name for name in ("delivery", "reconcile", "infrastructure")
                   if not (ROOT / "tests/platform" / ("test_" + name + ".py")).exists()]
        for group in ["unknown"] + missing:
            result = subprocess.run([str(runner), group], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("group", result.stderr.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
