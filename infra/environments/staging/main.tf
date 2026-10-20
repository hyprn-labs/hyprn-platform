module "environment" {
  source              = "../../modules/environment"
  project_id          = var.project_id
  organization_id     = var.organization_id
  billing_account     = var.billing_account
  region              = var.region
  subnet_cidr         = var.subnet_cidr
  sql_address         = var.sql_address
  bucket_names        = var.bucket_names
  recovery_group      = var.recovery_group
  https_egress_cidrs  = var.https_egress_cidrs
  tunnel_egress_cidrs = var.tunnel_egress_cidrs
}
resource "google_project_iam_member" "runtime_observability" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter"])
  project  = module.environment.project_id
  role     = each.key
  member   = "serviceAccount:${module.environment.runtime_service_account}"
}
module "host" {
  source                  = "../../modules/host"
  project_id              = module.environment.project_id
  zone                    = var.zone
  subnetwork              = module.environment.subnetwork
  host_image              = var.host_image
  runtime_service_account = module.environment.runtime_service_account
  operator_group          = var.operator_group
  depends_on              = [module.environment, google_project_iam_member.runtime_observability]
}
