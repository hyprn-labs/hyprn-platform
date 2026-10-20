terraform {
  required_version = "= 1.16.5"
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare", version = "= 5.28.0" }
  }
  backend "gcs" {}
}
# Authentication is injected through CLOUDFLARE_API_TOKEN, never a tfvar.
provider "cloudflare" {}
