output "bootstrap_state_bucket" {
  value = google_storage_bucket.bootstrap_tfstate.name
}

output "agents_folder" {
  value = google_folder.agents.name
}

output "agents_project_number" {
  value = google_project.agents.number
}

output "agents_state_bucket" {
  value = google_storage_bucket.agents_tfstate.name
}
