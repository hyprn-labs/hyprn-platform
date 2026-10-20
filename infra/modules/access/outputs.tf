output "binding" {
  value = {
    application_id = cloudflare_zero_trust_access_application.staging.id
    audience       = cloudflare_zero_trust_access_application.staging.aud
    issuer         = "https://${var.team_name}.cloudflareaccess.com"
    origin         = "https://staging.app.hyprn.ai"
    tunnel_id      = cloudflare_zero_trust_tunnel_cloudflared.staging.id
  }
}
# These evaluated values support offline policy assertions. Email data is sensitive.
output "review" {
  sensitive = true
  value = {
    idp         = cloudflare_zero_trust_access_identity_provider.email_pin
    policy      = cloudflare_zero_trust_access_policy.invited
    application = cloudflare_zero_trust_access_application.staging
    tunnel      = cloudflare_zero_trust_tunnel_cloudflared.staging
    config      = cloudflare_zero_trust_tunnel_cloudflared_config.staging
    dns         = cloudflare_dns_record.staging
  }
}
