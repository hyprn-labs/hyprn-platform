# Runs with the bootstrap administrator's application default credentials.
# Quota and billing for API calls go to the bootstrap project, which user
# credentials require for several APIs (Cloud Identity, Org Policy, Budgets).
provider "google" {
  region                = var.region
  billing_project       = var.bootstrap_project_id
  user_project_override = true
}
