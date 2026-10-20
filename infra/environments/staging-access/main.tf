module "access" {
  source          = "../../modules/access"
  account_id      = var.account_id
  zone_id         = var.zone_id
  team_name       = var.team_name
  admitted_emails = var.admitted_emails
  loopback_origin = var.loopback_origin
}
