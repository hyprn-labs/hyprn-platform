terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "8.6.0" }
  }
}
locals {
  labels = { product = "hyprn-mvp", environment = "staging", managed_by = "terraform" }
  services = toset([
    "compute.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com",
    "iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com",
    "cloudresourcemanager.googleapis.com", "serviceusage.googleapis.com", "storage.googleapis.com",
    "logging.googleapis.com", "monitoring.googleapis.com", "iap.googleapis.com",
    "oslogin.googleapis.com", "sqladmin.googleapis.com", "servicenetworking.googleapis.com",
    "dns.googleapis.com"
  ])
  secret_aliases = toset([
    "modeling-auth", "modeling-rails", "assistant-provider", "db-app-request", "db-app-auth",
    "db-app-migration", "db-app-backup", "cloudflare-tunnel",
    "db-assistant-background", "db-dispatcher-background"
  ])
}
resource "google_project" "staging" {
  project_id          = var.project_id
  name                = "HYPRN staging"
  org_id              = var.organization_id
  billing_account     = var.billing_account
  auto_create_network = false
  deletion_policy     = "PREVENT"
  labels              = local.labels
}
resource "google_project_service" "required" {
  for_each           = local.services
  project            = google_project.staging.project_id
  service            = each.key
  disable_on_destroy = false
}
resource "google_compute_network" "staging" {
  project                         = google_project.staging.project_id
  name                            = "hyprn-staging"
  auto_create_subnetworks         = false
  delete_default_routes_on_create = true
  depends_on                      = [google_project_service.required]
}
resource "google_compute_subnetwork" "staging" {
  project                  = var.project_id
  name                     = "hyprn-staging"
  region                   = var.region
  network                  = google_compute_network.staging.id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true
  stack_type               = "IPV4_ONLY"
}
resource "google_compute_route" "outbound" {
  project          = var.project_id
  name             = "hyprn-staging-outbound"
  network          = google_compute_network.staging.id
  dest_range       = "0.0.0.0/0"
  next_hop_gateway = "default-internet-gateway"
  priority         = 1000
}
resource "google_compute_address" "nat" {
  project    = var.project_id
  name       = "hyprn-staging-nat"
  region     = var.region
  depends_on = [google_project_service.required]
}
resource "google_compute_router" "staging" {
  project = var.project_id
  name    = "hyprn-staging"
  region  = var.region
  network = google_compute_network.staging.id
}
resource "google_compute_router_nat" "staging" {
  project                            = var.project_id
  name                               = "hyprn-staging"
  region                             = var.region
  router                             = google_compute_router.staging.name
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = [google_compute_address.nat.self_link]
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  subnetwork {
    name                    = google_compute_subnetwork.staging.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
resource "google_compute_firewall" "iap" {
  project                 = var.project_id
  name                    = "hyprn-staging-iap"
  network                 = google_compute_network.staging.id
  source_ranges           = ["35.235.240.0/20"]
  target_service_accounts = [google_service_account.runtime.email]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
resource "google_compute_firewall" "deny_egress" {
  project                 = var.project_id
  name                    = "hyprn-staging-deny-egress"
  network                 = google_compute_network.staging.id
  direction               = "EGRESS"
  priority                = 65000
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.runtime.email]
  deny { protocol = "all" }
}
resource "google_compute_firewall" "https" {
  project                 = var.project_id
  name                    = "hyprn-staging-https"
  network                 = google_compute_network.staging.id
  direction               = "EGRESS"
  priority                = 1000
  destination_ranges      = setunion(var.https_egress_cidrs, ["199.36.153.8/30"])
  target_service_accounts = [google_service_account.runtime.email]
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}
resource "google_compute_firewall" "tunnel" {
  project                 = var.project_id
  name                    = "hyprn-staging-tunnel"
  network                 = google_compute_network.staging.id
  direction               = "EGRESS"
  priority                = 1000
  destination_ranges      = var.tunnel_egress_cidrs
  target_service_accounts = [google_service_account.runtime.email]
  allow {
    protocol = "tcp"
    ports    = ["7844"]
  }
  allow {
    protocol = "udp"
    ports    = ["7844"]
  }
}
resource "google_compute_global_address" "sql" {
  project       = var.project_id
  name          = "hyprn-staging-sql"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  address       = var.sql_address
  network       = google_compute_network.staging.id
}
resource "google_service_networking_connection" "sql" {
  network                 = google_compute_network.staging.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql.name]
  deletion_policy         = "ABANDON"
}
resource "google_compute_firewall" "sql" {
  project                 = var.project_id
  name                    = "hyprn-staging-sql"
  network                 = google_compute_network.staging.id
  direction               = "EGRESS"
  priority                = 1000
  destination_ranges      = ["${var.sql_address}/16"]
  target_service_accounts = [google_service_account.runtime.email]
  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }
}
resource "google_sql_database_instance" "app" {
  project             = var.project_id
  name                = "hyprn-staging-app"
  region              = var.region
  database_version    = "POSTGRES_17"
  deletion_protection = true
  settings {
    tier                        = "db-custom-1-3840"
    edition                     = "ENTERPRISE"
    availability_type           = "ZONAL"
    disk_type                   = "PD_SSD"
    disk_size                   = 20
    disk_autoresize             = true
    disk_autoresize_limit       = 100
    deletion_protection_enabled = true
    user_labels                 = local.labels
    ip_configuration {
      ipv4_enabled                     = false
      private_network                  = google_compute_network.staging.id
      allocated_ip_range               = google_compute_global_address.sql.name
      ssl_mode                         = "ENCRYPTED_ONLY"
      server_ca_mode                   = "GOOGLE_MANAGED_CAS_CA"
      server_certificate_rotation_mode = "AUTOMATIC_ROTATION_DURING_MAINTENANCE"
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      start_time                     = "02:00"
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
  }
  depends_on = [google_service_networking_connection.sql]
  lifecycle { prevent_destroy = true }
}
resource "google_sql_database" "app" {
  project  = var.project_id
  instance = google_sql_database_instance.app.name
  name     = "hyprn"
}
locals {
  sql_dns_name = one([
    for entry in google_sql_database_instance.app.dns_names : entry.name
    if entry.connection_type == "PRIVATE_SERVICES_ACCESS" && entry.dns_scope == "INSTANCE"
  ])
}
resource "google_dns_managed_zone" "sql" {
  project    = var.project_id
  name       = "hyprn-staging-sql"
  dns_name   = "${trimsuffix(local.sql_dns_name, ".")}."
  visibility = "private"
  private_visibility_config {
    networks { network_url = google_compute_network.staging.id }
  }
}
resource "google_dns_record_set" "sql" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.sql.name
  name         = google_dns_managed_zone.sql.dns_name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_sql_database_instance.app.private_ip_address]
}
resource "google_storage_bucket" "purpose" {
  for_each                    = var.bucket_names
  project                     = var.project_id
  name                        = each.value
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = merge(local.labels, { component = each.key })
  versioning { enabled = true }
  soft_delete_policy { retention_duration_seconds = 604800 }
  lifecycle { prevent_destroy = true }
  depends_on = [google_project_service.required]
}
resource "google_storage_bucket_iam_member" "runtime" {
  for_each = {
    artifacts = "roles/storage.objectViewer"
    desired   = "roles/storage.objectViewer"
    backup    = "roles/storage.objectCreator"
  }
  bucket = google_storage_bucket.purpose[each.key].name
  role   = each.value
  member = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_storage_bucket_iam_member" "recovery" {
  bucket = google_storage_bucket.purpose["backup"].name
  role   = "roles/storage.objectViewer"
  member = "group:${var.recovery_group}"
}
resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.region
  repository_id = "hyprn"
  format        = "DOCKER"
  labels        = local.labels
  docker_config { immutable_tags = true }
  depends_on = [google_project_service.required]
}
resource "google_artifact_registry_repository_iam_member" "runtime" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_secret_manager_secret" "runtime" {
  for_each  = local.secret_aliases
  project   = var.project_id
  secret_id = "hyprn-staging-${each.key}"
  labels    = local.labels
  replication {
    user_managed {
      replicas { location = var.region }
    }
  }
  depends_on = [google_project_service.required]
  lifecycle { prevent_destroy = true }
}
resource "google_secret_manager_secret_iam_member" "runtime" {
  for_each  = google_secret_manager_secret.runtime
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_service_account" "runtime" {
  project      = google_project.staging.project_id
  account_id   = "hyprn-staging-runtime"
  display_name = "HYPRN staging trusted host"
  depends_on   = [google_project_service.required]
}

resource "google_dns_managed_zone" "google_apis" {
  project    = var.project_id
  name       = "hyprn-staging-googleapis"
  dns_name   = "googleapis.com."
  visibility = "private"
  private_visibility_config {
    networks { network_url = google_compute_network.staging.id }
  }
}
resource "google_dns_record_set" "google_apis_address" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.google_apis.name
  name         = "private.googleapis.com."
  type         = "A"
  ttl          = 300
  rrdatas      = ["199.36.153.8", "199.36.153.9", "199.36.153.10", "199.36.153.11"]
}
resource "google_dns_record_set" "google_apis_wildcard" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.google_apis.name
  name         = "*.googleapis.com."
  type         = "CNAME"
  ttl          = 300
  rrdatas      = [google_dns_record_set.google_apis_address.name]
}
resource "google_dns_managed_zone" "registry" {
  project    = var.project_id
  name       = "hyprn-staging-registry"
  dns_name   = "pkg.dev."
  visibility = "private"
  private_visibility_config {
    networks { network_url = google_compute_network.staging.id }
  }
}
resource "google_dns_record_set" "registry_wildcard" {
  project      = var.project_id
  managed_zone = google_dns_managed_zone.registry.name
  name         = "*.pkg.dev."
  type         = "CNAME"
  ttl          = 300
  rrdatas      = [google_dns_record_set.google_apis_address.name]
}
