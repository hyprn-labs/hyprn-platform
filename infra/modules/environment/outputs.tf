output "project_id" { value = google_project.staging.project_id }
output "project_number" { value = google_project.staging.number }
output "subnetwork" { value = google_compute_subnetwork.staging.id }
output "registry" { value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}" }
output "buckets" { value = { for purpose, bucket in google_storage_bucket.purpose : purpose => bucket.name } }
output "secret_names" { value = { for alias, secret in google_secret_manager_secret.runtime : alias => secret.secret_id } }
output "database" {
  value = {
    host       = trimsuffix(local.sql_dns_name, ".")
    name       = google_sql_database.app.name
    private_ip = google_sql_database_instance.app.private_ip_address
    ca_mode    = google_sql_database_instance.app.settings[0].ip_configuration[0].server_ca_mode
    ssl_mode   = google_sql_database_instance.app.settings[0].ip_configuration[0].ssl_mode
  }
}
output "policy" {
  value = {
    public_database       = google_sql_database_instance.app.settings[0].ip_configuration[0].ipv4_enabled
    private_google_access = google_compute_subnetwork.staging.private_ip_google_access
    pitr                  = google_sql_database_instance.app.settings[0].backup_configuration[0].point_in_time_recovery_enabled
    ingress_ranges        = google_compute_firewall.iap.source_ranges
    ingress_ports         = one(google_compute_firewall.iap.allow).ports
    backup_runtime_role   = google_storage_bucket_iam_member.runtime["backup"].role
    desired_runtime_role  = google_storage_bucket_iam_member.runtime["desired"].role
    public_buckets        = [for bucket in google_storage_bucket.purpose : bucket.public_access_prevention]
    google_api_addresses  = google_dns_record_set.google_apis_address.rrdatas
    registry_alias        = google_dns_record_set.registry_wildcard.rrdatas
    secrets               = keys(google_secret_manager_secret.runtime)
  }
}
output "runtime_service_account" { value = google_service_account.runtime.email }
