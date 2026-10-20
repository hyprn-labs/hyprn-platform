"""Evaluate Terraform plans offline; no credentials or live cloud API calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = """
mock_provider "google" {
  override_during = plan
  mock_resource "google_project" {
    defaults = { number = "123456789012" }
  }
  mock_resource "google_sql_database_instance" {
    defaults = {
      private_ip_address = "10.82.0.3"
      dns_names = [{
        name = "012345abcdef.abcdef012345.europe-west1.sql-psa.goog."
        connection_type = "PRIVATE_SERVICES_ACCESS"
        dns_scope = "INSTANCE"
      }]
    }
  }
}
variables {
  project_id = "hyprn-staging-test"
  organization_id = "123456789012"
  billing_account = "ABCDEF-ABCDEF-ABCDEF"
  region = "europe-west1"
  zone = "europe-west1-b"
  host_image = "projects/debian-cloud/global/images/debian-12-test"
  subnet_cidr = "10.81.0.0/24"
  sql_address = "10.82.0.0"
  bucket_names = {
    artifacts = "hyprn-staging-test-artifacts"
    desired = "hyprn-staging-test-desired"
    backup = "hyprn-staging-test-backup"
  }
  operator_group = "staging-operators@example.invalid"
  recovery_group = "recovery-operators@example.invalid"
  https_egress_cidrs = ["199.36.153.8/30"]
  tunnel_egress_cidrs = ["198.41.192.0/24", "198.41.200.0/24"]
}
run "private_stopped_host_and_database" {
  command = plan
  assert {
    condition = output.offline_policy.host.public_addresses == 0 && output.offline_policy.host.status == "TERMINATED"
    error_message = "An unqualified host must be stopped with no public address."
  }
  assert {
    condition = output.offline_policy.host.deletion_protection && output.offline_policy.host.oslogin == "TRUE"
    error_message = "Require deletion protection and OS Login."
  }
  assert {
    condition = !output.offline_policy.environment.public_database && output.offline_policy.environment.pitr && output.infrastructure.database.version == "POSTGRES_17"
    error_message = "Require private PostgreSQL 17 and point-in-time recovery."
  }
  assert {
    condition = output.infrastructure.database.host == "012345abcdef.abcdef012345.europe-west1.sql-psa.goog" && output.infrastructure.database.ca_mode == "GOOGLE_MANAGED_CAS_CA" && output.infrastructure.database.ssl_mode == "ENCRYPTED_ONLY"
    error_message = "Private DNS must match the shared-CA server identity."
  }
  assert {
    condition = output.offline_policy.environment.private_google_access && output.offline_policy.environment.ingress_ranges == toset(["35.235.240.0/20"]) && output.offline_policy.environment.ingress_ports == tolist(["22"])
    error_message = "Only IAP SSH may enter; private Google access is required."
  }
  assert {
    condition = output.offline_policy.environment.backup_runtime_role == "roles/storage.objectCreator" && output.offline_policy.environment.desired_runtime_role == "roles/storage.objectViewer"
    error_message = "Runtime may not replace desired state or delete backups."
  }
  assert {
    condition = alltrue([for policy in output.offline_policy.environment.public_buckets : policy == "enforced"])
    error_message = "No public buckets."
  }
  assert {
    condition = contains(output.offline_policy.environment.secrets, "db-app-auth") && contains(output.offline_policy.environment.secrets, "db-app-migration") && contains(output.offline_policy.environment.secrets, "db-assistant-background") && contains(output.offline_policy.environment.secrets, "db-dispatcher-background")
    error_message = "Request, authentication, migration and background roles need separate secret metadata."
  }
}
run "organization_root" {
  command = plan
  assert {
    condition = output.offline_policy.environment.organization_id == var.organization_id
    error_message = "The staging project must use the reviewed organization root."
  }
}
run "private_google_dns" {
  command = plan
  assert {
    condition = contains(output.offline_policy.environment.google_api_addresses, "199.36.153.8") && output.offline_policy.environment.registry_alias == tolist(["private.googleapis.com."])
    error_message = "Google APIs and registry must resolve through private Google access."
  }
}
run "reject_fleet_project" {
  command = plan
  variables { project_id = "hyprn-agents" }
  expect_failures = [var.project_id]
}
run "reject_image_family" {
  command = plan
  variables { host_image = "projects/debian-cloud/global/images/family/debian-12" }
  expect_failures = [var.host_image]
}
run "reject_unbounded_https" {
  command = plan
  variables { https_egress_cidrs = ["0.0.0.0/0"] }
  expect_failures = [var.https_egress_cidrs]
}
run "reject_merged_storage" {
  command = plan
  variables {
    bucket_names = {
      artifacts = "hyprn-staging-test-artifacts"
      desired = "hyprn-staging-test-artifacts"
      backup = "hyprn-staging-test-backup"
    }
  }
  expect_failures = [var.bucket_names]
}
run "reject_other_region_zone" {
  command = plan
  variables { zone = "us-central1-a" }
  expect_failures = [var.zone]
}
"""


class InfrastructureTests(unittest.TestCase):
    def test_provider_validates_and_evaluates_staging_policy(self):
        terraform = shutil.which("terraform")
        self.assertIsNotNone(terraform, "Install the reviewed Terraform version first.")
        provider_dir = os.environ.get("HYPRN_TF_PROVIDER_DIR")
        self.assertTrue(provider_dir, "Set HYPRN_TF_PROVIDER_DIR to a reviewed provider cache.")
        self.assertTrue(Path(provider_dir).is_dir())
        with tempfile.TemporaryDirectory(prefix="hyprn-infrastructure-") as directory:
            scratch = Path(directory)
            for name in ("modules/environment", "modules/host", "environments/staging"):
                source = ROOT / "infra" / name
                target = scratch / "infra" / name
                target.mkdir(parents=True)
                for path in source.iterdir():
                    if path.suffix == ".tf" or path.name == ".terraform.lock.hcl":
                        shutil.copy2(path, target / path.name)
            root = scratch / "infra/environments/staging"
            (root / "policy.tftest.hcl").write_text(FIXTURE)
            cli = scratch / "terraform.rc"
            cli.write_text("disable_checkpoint = true\n")
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("GOOGLE_", "TF_VAR_", "TF_CLI_ARGS", "CLOUDSDK_"))}
            env.update({
                "TF_DATA_DIR": str(scratch / "terraform-data"),
                "TF_CLI_CONFIG_FILE": str(cli),
                "TF_IN_AUTOMATION": "1",
                "CHECKPOINT_DISABLE": "1",
                "CLOUDSDK_CONFIG": str(scratch / "gcloud"),
                "GOOGLE_APPLICATION_CREDENTIALS": str(scratch / "no-credentials.json"),
                "GH_CONFIG_DIR": str(scratch / "github"),
            })
            for args in (
                ["init", "-backend=false", "-input=false", "-lockfile=readonly",
                 "-plugin-dir=" + str(Path(provider_dir).resolve())],
                ["validate", "-json"],
                ["test", "-json"],
            ):
                result = subprocess.run(
                    [terraform, "-chdir=" + str(root), *args], env=env,
                    capture_output=True, text=True, timeout=120, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if args[0] == "validate":
                    self.assertTrue(json.loads(result.stdout)["valid"])
                if args[0] == "test":
                    events = [json.loads(line) for line in result.stdout.splitlines()]
                    summary = next(event["test_summary"] for event in events
                                   if event.get("type") == "test_summary")
                    self.assertEqual(summary["passed"], 8)
                    self.assertEqual(summary["failed"], 0)

    def test_access_template_has_no_bypass_and_requires_explicit_admission(self):
        document = json.loads((ROOT / "environments/staging/access.json").read_text())
        self.assertEqual(document["status"], "review-template")
        application = document["request_templates"]["application"]
        self.assertEqual(application["domain"], "staging.hyprn.ai")
        self.assertEqual(application["type"], "self_hosted")
        self.assertEqual(application["allowed_idps"], ["${email_pin_idp_id}"])
        policy = document["request_templates"]["policy"]
        self.assertEqual(policy["decision"], "allow")
        self.assertEqual(policy["include"], [{"email": {"email": "${admitted_email}"}}])
        ingress = document["request_templates"]["tunnel_configuration"]["config"]["ingress"]
        self.assertEqual(ingress[-1], {"service": "http_status:404"})
        self.assertEqual(len(ingress), 2)
        self.assertNotIn("bypass", json.dumps(document["request_templates"]))


if __name__ == "__main__":
    unittest.main()
