# Cloudflare Terraform provider

Reviewed 2026-10-20, before binary acquisition.

- Provider: cloudflare/cloudflare 5.28.0, official release published 2026-10-13.
- Source: https://github.com/cloudflare/terraform-provider-cloudflare/tree/fa63ebaea80e153d0d9325f818adc36187a8e12a
- Licence: Apache-2.0, verified at https://github.com/cloudflare/terraform-provider-cloudflare/blob/v5.28.0/LICENSE
- Release: https://github.com/cloudflare/terraform-provider-cloudflare/releases/tag/v5.28.0
- darwin_arm64 archive: terraform-provider-cloudflare_5.28.0_darwin_arm64.zip
- Archive SHA256: 886714cfd9ada7876dd39ed857661766d9b75ba205079c3b70c4d5b56e9955b8
- Publisher checksums: https://github.com/cloudflare/terraform-provider-cloudflare/releases/download/v5.28.0/terraform-provider-cloudflare_5.28.0_SHA256SUMS
- Verification uses the exact publisher HTTPS checksum; this is not an independent
  signing-key verification. No transitive package installation is needed.
- Terraform 1.16.5 is the existing reviewed executable documented in
  runbooks/product-staging.md; this task does not acquire Terraform.

## State boundary

The pinned zero_trust_tunnel_cloudflared model has optional, no_refresh
tunnel_secret and no token attribute. Create uses UnmarshalComputed; update/read
restore the configured secret. Omitting tunnel_secret for config_src=cloudflare
keeps it null. No tunnel-token data source is used. The provider API token is
supplied through CLOUDFLARE_API_TOKEN by the operator, never as a Terraform variable.
The pinned schema and evaluated plans are checked by access-infrastructure.

The future approved runtime step obtains the remotely managed tunnel token
directly from the Cloudflare token endpoint into Secret Manager through a
nonlogging operator process. It must never pass through Terraform, stdout,
command arguments, repository files, outputs or state. Application/IdP/tunnel IDs,
audience and hostname are metadata. Invited emails are personal data: outside Git
as inputs, and protected in the isolated remote state and saved plan.

## Official schema references

All resource schemas below are from the same audited tag:
https://github.com/cloudflare/terraform-provider-cloudflare/tree/v5.28.0/docs/resources

- zero_trust_access_identity_provider: onetimepin with empty config.
- zero_trust_access_policy: exact email includes and allow decision.
- zero_trust_access_application: self_hosted, one IdP and one policy.
- zero_trust_tunnel_cloudflared: config_src=cloudflare, omitted tunnel_secret.
- zero_trust_tunnel_cloudflared_config: hostname ingress and final http_status:404.
- dns_record: proxied CNAME to the tunnel.
