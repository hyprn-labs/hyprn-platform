"""Exercise the real provider schema and Terraform's state-bucket protections offline."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
VARIABLES = """
mock_provider "google" {}
variables {
  state_bucket_name = "hyprn-staging-test-tfstate"
  location = "EUROPE-WEST1"
}
"""
POLICY = VARIABLES + """
run "private_versioned_state" {
  command = plan
  assert {
    condition = google_storage_bucket.staging_state.project == "hyprn-bootstrap" && google_storage_bucket.staging_state.name == var.state_bucket_name
    error_message = "The dedicated bucket belongs in the existing bootstrap project."
  }
  assert {
    condition = google_storage_bucket.staging_state.uniform_bucket_level_access && google_storage_bucket.staging_state.public_access_prevention == "enforced"
    error_message = "State must have uniform private access."
  }
  assert {
    condition = google_storage_bucket.staging_state.versioning[0].enabled && !google_storage_bucket.staging_state.force_destroy
    error_message = "State history must survive ordinary updates and nonempty bucket deletion."
  }
  assert {
    condition = google_storage_bucket.staging_state.location == var.location && google_storage_bucket.staging_state.storage_class == "STANDARD"
    error_message = "Use the explicit reviewed EU location and standard storage."
  }
}
run "reject_fleet_state" {
  command = plan
  variables { state_bucket_name = "hyprn-agents-tfstate" }
  expect_failures = [var.state_bucket_name]
}
run "reject_bootstrap_state" {
  command = plan
  variables { state_bucket_name = "hyprn-bootstrap-tfstate" }
  expect_failures = [var.state_bucket_name]
}
run "reject_non_eu_location" {
  command = plan
  variables { location = "US-CENTRAL1" }
  expect_failures = [var.location]
}
"""
REPLACEMENT = VARIABLES + """
run "existing_bucket" { command = apply }
run "reject_replacement" {
  command = plan
  variables { state_bucket_name = "hyprn-staging-replacement-tfstate" }
}
"""


class StateBootstrapTests(unittest.TestCase):
    def evaluate(self, fixture):
        terraform = shutil.which("terraform")
        self.assertIsNotNone(terraform, "Use the reviewed Terraform executable.")
        provider = os.environ.get("HYPRN_TF_PROVIDER_DIR")
        self.assertTrue(provider, "Set HYPRN_TF_PROVIDER_DIR to the reviewed Google provider cache.")
        self.assertTrue(Path(provider).is_dir())
        source = ROOT / "infra/bootstrap/staging-state"
        self.assertTrue(source.is_dir(), "The isolated staging-state root must exist.")
        with tempfile.TemporaryDirectory(prefix="hyprn-state-bootstrap-") as directory:
            scratch = Path(directory)
            root = scratch / "root"
            root.mkdir()
            for path in source.iterdir():
                if path.suffix == ".tf" or path.name == ".terraform.lock.hcl":
                    shutil.copy2(path, root / path.name)
            (root / "state.tftest.hcl").write_text(fixture)
            cli = scratch / "terraform.rc"
            cli.write_text("disable_checkpoint = true\n")
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("GOOGLE_", "TF_", "CLOUDSDK_"))}
            env.update(TF_DATA_DIR=str(scratch / "data"),
                       TF_CLI_CONFIG_FILE=str(cli), TF_IN_AUTOMATION="1",
                       CHECKPOINT_DISABLE="1", CLOUDSDK_CONFIG=str(scratch / "gcloud"),
                       GOOGLE_APPLICATION_CREDENTIALS=str(scratch / "no-credentials.json"),
                       GH_CONFIG_DIR=str(scratch / "github"))
            def run(*args):
                return subprocess.run([terraform, "-chdir=" + str(root), *args],
                                      env=env, capture_output=True, text=True, timeout=120)
            init = run("init", "-backend=false", "-input=false", "-lockfile=readonly",
                       "-plugin-dir=" + str(Path(provider).resolve()))
            self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
            validate = run("validate", "-json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            self.assertTrue(json.loads(validate.stdout)["valid"])
            return run("test", "-json", "-verbose")

    def test_private_versioned_dedicated_state_and_invalid_inputs(self):
        result = self.evaluate(POLICY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        summary = next(event["test_summary"] for event in events
                       if event.get("type") == "test_summary")
        self.assertEqual(summary["passed"], 4)
        self.assertEqual(summary["failed"], 0)
        plans = [event["test_plan"] for event in events if event.get("type") == "test_plan"]
        self.assertTrue(plans, "Inspect the evaluated plan, not source text.")
        changes = plans[0]["resource_changes"]
        self.assertEqual([(r["address"], r["change"]["actions"]) for r in changes],
                         [("google_storage_bucket.staging_state", ["create"])])

    def test_prevent_destroy_refuses_bucket_replacement(self):
        result = self.evaluate(REPLACEMENT)
        self.assertNotEqual(result.returncode, 0, "Replacement must be refused.")
        events = [json.loads(line) for line in result.stdout.splitlines()]
        diagnostics = [e["diagnostic"] for e in events if e.get("type") == "diagnostic"]
        self.assertTrue(any(d["summary"] == "Instance cannot be destroyed"
                            and "prevent_destroy" in d["detail"] for d in diagnostics),
                        result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
