output "infrastructure" {
  value = {
    project_id     = module.environment.project_id
    project_number = module.environment.project_number
    host_id        = module.host.host_id
    data_disk      = module.host.data_disk
    registry       = module.environment.registry
    buckets        = module.environment.buckets
    database       = module.environment.database
    secret_names   = module.environment.secret_names
  }
}
output "offline_policy" {
  value = { environment = module.environment.policy, host = module.host.policy }
}
