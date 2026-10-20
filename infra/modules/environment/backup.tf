# Managed instance backups preserve FORCE RLS without a bypass database login.
resource "google_project_iam_custom_role" "runtime_database_backup" {
  project     = google_project.staging.project_id
  role_id     = "hyprnStagingDatabaseBackup"
  title       = "HYPRN staging database backup"
  description = "Create and inspect managed backups of the staging database."
  permissions = [
    "cloudsql.backupRuns.create",
    "cloudsql.backupRuns.get",
    "cloudsql.backupRuns.list",
    "cloudsql.instances.get",
  ]
}

locals {
  backup_instance_resource = "projects/${var.project_id}/instances/${google_sql_database_instance.app.name}"
  backup_resource_condition = join(" || ", [
    "(resource.type == \"sqladmin.googleapis.com/Instance\" && resource.name == \"${local.backup_instance_resource}\")",
    "(resource.type == \"sqladmin.googleapis.com/BackupRun\" && (resource.name == \"${local.backup_instance_resource}\" || resource.name.startsWith(\"${local.backup_instance_resource}/\")))",
  ])
}

resource "google_project_iam_member" "runtime_database_backup" {
  project = google_project.staging.project_id
  role    = google_project_iam_custom_role.runtime_database_backup.name
  member  = "serviceAccount:${google_service_account.runtime.email}"
  condition {
    title       = "staging-database-backups-only"
    description = "Exact staging instance and its backups; no restore or delete authority."
    expression  = local.backup_resource_condition
  }
}
