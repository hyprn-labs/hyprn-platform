resource "cloudflare_zero_trust_access_identity_provider" "email_pin" {
  account_id = var.account_id
  name       = "HYPRN staging email PIN"
  type       = "onetimepin"
  config     = {}
}

resource "cloudflare_zero_trust_access_policy" "invited" {
  account_id       = var.account_id
  name             = "HYPRN staging invited users"
  decision         = "allow"
  include          = [for email in sort(tolist(var.admitted_emails)) : { email = { email = email } }]
  exclude          = []
  require          = []
  session_duration = "8h"
}

resource "cloudflare_zero_trust_access_application" "staging" {
  account_id                 = var.account_id
  name                       = "HYPRN staging"
  type                       = "self_hosted"
  domain                     = "staging.hyprn.ai"
  session_duration           = "8h"
  allowed_idps               = [cloudflare_zero_trust_access_identity_provider.email_pin.id]
  auto_redirect_to_identity  = true
  options_preflight_bypass   = false
  http_only_cookie_attribute = true
  same_site_cookie_attribute = "lax"
  policies = [{
    id         = cloudflare_zero_trust_access_policy.invited.id
    precedence = 1
  }]
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "staging" {
  account_id = var.account_id
  name       = "hyprn-staging"
  config_src = "cloudflare"
  # Omitted tunnel_secret: remote credentials never enter Terraform state.
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "staging" {
  account_id = var.account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.staging.id
  source     = "cloudflare"
  config = {
    ingress = [
      {
        hostname = cloudflare_zero_trust_access_application.staging.domain
        service  = var.loopback_origin
        origin_request = {
          access = {
            required  = true
            team_name = var.team_name
            aud_tag   = [cloudflare_zero_trust_access_application.staging.aud]
          }
        }
      },
      { service = "http_status:404" }
    ]
  }
}

resource "cloudflare_dns_record" "staging" {
  zone_id = var.zone_id
  name    = cloudflare_zero_trust_access_application.staging.domain
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.staging.id}.cfargotunnel.com"
  proxied = true
  ttl     = 1
  # Access and connector enforcement must exist before hostname publication.
  depends_on = [cloudflare_zero_trust_tunnel_cloudflared_config.staging]
}
