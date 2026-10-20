"""Validate the real Cloudflare schema and evaluated plans without cloud credentials."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = r"""
mock_provider "cloudflare" {
  override_during = plan
  mock_resource "cloudflare_zero_trust_access_identity_provider" {
    defaults = { id = "11111111-1111-4111-8111-111111111111" }
  }
  mock_resource "cloudflare_zero_trust_access_policy" {
    defaults = { id = "22222222-2222-4222-8222-222222222222" }
  }
  mock_resource "cloudflare_zero_trust_access_application" {
    defaults = { id = "33333333-3333-4333-8333-333333333333", aud = "test-audience" }
  }
  mock_resource "cloudflare_zero_trust_tunnel_cloudflared" {
    defaults = { id = "44444444-4444-4444-8444-444444444444" }
  }
}
variables {
  account_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  zone_id = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  team_name = "synthetic-staging"
  admitted_emails = ["operator@example.invalid", "reviewer@example.invalid"]
  loopback_origin = "http://127.0.0.1:8080"
}
run "named_email_boundary" {
  command = plan
  assert {
    condition = output.review.policy.decision == "allow" && length(output.review.policy.include) == 2 && toset([for rule in output.review.policy.include : rule.email.email]) == toset(var.admitted_emails)
    error_message = "Only exact named emails may be admitted."
  }
  assert {
    condition = alltrue(flatten([for rule in output.review.policy.include : [for key, value in rule : key == "email" || value == null]]))
    error_message = "Domain, everyone, token, IP and other bypass selectors are forbidden."
  }
  assert {
    condition = length(output.review.policy.exclude) == 0 && length(output.review.policy.require) == 0 && output.review.idp.type == "onetimepin"
    error_message = "Use the one-time email PIN provider and explicit named admission."
  }
  assert {
    condition = output.review.application.domain == "staging.app.hyprn.ai" && output.review.application.type == "self_hosted" && output.review.application.allowed_idps == toset([output.review.idp.id]) && length(output.review.application.policies) == 1 && output.review.application.policies[0].id == output.review.policy.id
    error_message = "The complete application hostname must use the one reviewed IdP and policy."
  }
  assert {
    condition = !output.review.application.options_preflight_bypass && output.review.application.oauth_configuration == null && output.review.application.session_duration == "8h"
    error_message = "No preflight bypass or external OAuth is admitted."
  }
}
run "tunnel_origin_and_dns" {
  command = plan
  assert {
    condition = output.review.tunnel.config_src == "cloudflare" && output.review.tunnel.tunnel_secret == null
    error_message = "Remote tunnel metadata must not put credentials in state."
  }
  assert {
    condition = length(output.review.config.config.ingress) == 2 && output.review.config.config.ingress[0].hostname == output.review.application.domain && output.review.config.config.ingress[0].service == var.loopback_origin && output.review.config.config.ingress[0].path == null && output.review.config.config.ingress[1].service == "http_status:404" && output.review.config.config.ingress[1].hostname == null
    error_message = "Route only the exact host to loopback, with a final fail-closed 404."
  }
  assert {
    condition = output.review.config.config.ingress[0].origin_request.access.required && output.review.config.config.ingress[0].origin_request.access.aud_tag == tolist([output.review.application.aud]) && output.review.config.config.ingress[0].origin_request.access.team_name == var.team_name
    error_message = "The connector must verify Access JWTs against the exact team and audience."
  }
  assert {
    condition = output.review.dns.proxied && output.review.dns.type == "CNAME" && output.review.dns.name == output.review.application.domain && output.review.dns.content == "${output.review.tunnel.id}.cfargotunnel.com" && output.review.dns.ttl == 1
    error_message = "Publish only the proxied tunnel hostname."
  }
}
run "reject_empty_allowlist" {
 command = plan
 variables { admitted_emails = [] }
 expect_failures = [var.admitted_emails]
}
run "reject_wildcard_email" {
 command = plan
 variables { admitted_emails = ["*@example.invalid"] }
 expect_failures = [var.admitted_emails]
}
run "reject_domain_only" {
 command = plan
 variables { admitted_emails = ["example.invalid"] }
 expect_failures = [var.admitted_emails]
}
run "reject_wildcard_domain" {
 command = plan
 variables { admitted_emails = ["user@*.invalid"] }
 expect_failures = [var.admitted_emails]
}
run "reject_public_origin" {
 command = plan
 variables { loopback_origin = "http://0.0.0.0:8080" }
 expect_failures = [var.loopback_origin]
}
run "reject_remote_origin" {
 command = plan
 variables { loopback_origin = "http://169.254.169.254:80" }
 expect_failures = [var.loopback_origin]
}
run "reject_origin_userinfo" {
 command = plan
 variables { loopback_origin = "http://127.0.0.1:8080@evil.invalid" }
 expect_failures = [var.loopback_origin]
}
run "reject_origin_path" {
 command = plan
 variables { loopback_origin = "http://127.0.0.1:8080/mcp" }
 expect_failures = [var.loopback_origin]
}
run "reject_origin_port" {
 command = plan
 variables { loopback_origin = "http://127.0.0.1:65536" }
 expect_failures = [var.loopback_origin]
}
run "reject_invalid_account" {
 command = plan
 variables { account_id = "wrong-account" }
 expect_failures = [var.account_id]
}
"""

class AccessInfrastructureTests(unittest.TestCase):
    def test_evaluated_access_boundary(self):
        source = ROOT / "infra/environments/staging-access"
        self.assertTrue((source / "main.tf").is_file(),
                        "The declarative staging Access boundary must exist.")
        terraform = shutil.which("terraform")
        self.assertIsNotNone(terraform, "Use the reviewed Terraform 1.16.5 executable.")
        cache = os.environ.get("HYPRN_CF_PROVIDER_DIR")
        self.assertTrue(cache, "Set HYPRN_CF_PROVIDER_DIR to the audited provider cache.")
        self.assertTrue(Path(cache).is_dir())
        with tempfile.TemporaryDirectory(prefix="hyprn-access-infrastructure-") as directory:
            scratch = Path(directory)
            for relative in ("modules/access", "environments/staging-access"):
                target = scratch / "infra" / relative
                target.mkdir(parents=True)
                for path in (ROOT / "infra" / relative).iterdir():
                    if path.suffix == ".tf" or path.name == ".terraform.lock.hcl":
                        shutil.copy2(path, target / path.name)
            root = scratch / "infra/environments/staging-access"
            (root / "policy.tftest.hcl").write_text(FIXTURE)
            # Override only persistence inside scratch; never initialize the GCS backend.
            (root / "test_backend_override.tf").write_text('terraform {\n  backend "local" {}\n}\n')
            config = scratch / "terraform.rc"
            config.write_text("disable_checkpoint = true\n")
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("CLOUDFLARE_", "CF_", "GOOGLE_", "CLOUDSDK_",
                                          "TF_", "GH_", "GITHUB_"))}
            env.update(TF_DATA_DIR=str(scratch / "data"), TF_CLI_CONFIG_FILE=str(config),
                       TF_IN_AUTOMATION="1", CHECKPOINT_DISABLE="1",
                       CLOUDSDK_CONFIG=str(scratch / "gcloud"),
                       GOOGLE_APPLICATION_CREDENTIALS=str(scratch / "no-credentials.json"),
                       GH_CONFIG_DIR=str(scratch / "github"))
            def run(*args, success=True):
                result = subprocess.run([terraform, "-chdir=" + str(root), *args],
                                        env=env, capture_output=True, text=True, timeout=120)
                if success:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result
            version = json.loads(run("version", "-json").stdout)
            self.assertEqual(version["terraform_version"], "1.16.5")
            run("init", "-input=false", "-lockfile=readonly",
                "-plugin-dir=" + str(Path(cache).resolve()))
            self.assertTrue(json.loads(run("validate", "-json").stdout)["valid"])
            schemas = json.loads(run("providers", "schema", "-json").stdout)
            cf = schemas["provider_schemas"]["registry.terraform.io/cloudflare/cloudflare"]
            tunnel = cf["resource_schemas"]["cloudflare_zero_trust_tunnel_cloudflared"]["block"]["attributes"]
            self.assertTrue(tunnel["tunnel_secret"]["optional"])
            self.assertFalse(tunnel["tunnel_secret"].get("computed", False))
            self.assertFalse(any("token" in key for key in tunnel))
            result = run("test", "-json")
            events = [json.loads(line) for line in result.stdout.splitlines()]
            summary = next(e["test_summary"] for e in events if e.get("type") == "test_summary")
            self.assertEqual(summary["passed"], 12)
            self.assertEqual(summary["failed"], 0)
            self.assertEqual(summary["skipped"], 0)
            graph = run("graph").stdout
            edges = {}
            for start, end in re.findall(r'"([^"]+)" -> "([^"]+)"', graph):
                edges.setdefault(start, set()).add(end)
            def reaches(start, end, visited=None):
                visited = set() if visited is None else visited
                if start == end:
                    return True
                if start in visited:
                    return False
                visited.add(start)
                return any(reaches(n, end, visited) for n in edges.get(start, ()))
            prefix = "module.access."
            self.assertTrue(reaches(prefix + "cloudflare_dns_record.staging",
                                    prefix + "cloudflare_zero_trust_access_application.staging"), graph)
            self.assertTrue(reaches(prefix + "cloudflare_dns_record.staging",
                                    prefix + "cloudflare_zero_trust_access_policy.invited"), graph)
            self.assertTrue(reaches(prefix + "cloudflare_dns_record.staging",
                                    prefix + "cloudflare_zero_trust_tunnel_cloudflared_config.staging"), graph)
            # A bypass regression must fail the evaluated assertion, not just a text scan.
            module = scratch / "infra/modules/access/main.tf"
            original = module.read_text()
            changed, count = re.subn(r'decision\s*=\s*"allow"', 'decision = "bypass"', original)
            self.assertEqual(count, 1)
            module.write_text(changed)
            bad = run("test", "-json", success=False)
            self.assertNotEqual(bad.returncode, 0)
            diagnostics = [json.loads(line) for line in bad.stdout.splitlines()]
            self.assertTrue(any(e.get("diagnostic", {}).get("summary") == "Test assertion failed"
                                for e in diagnostics), bad.stdout + bad.stderr)
            module.write_text(original)

if __name__ == "__main__":
    unittest.main()
