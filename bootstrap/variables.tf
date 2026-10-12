variable "org_id" {
  description = "Numeric ID of the hyprn.ai organization."
  type        = string
}

variable "directory_customer_id" {
  description = "Directory customer ID allowed in IAM policies (iam.allowedPolicyMemberDomains)."
  type        = string
}

variable "billing_account" {
  description = "Company billing account ID."
  type        = string
}

variable "admins_group" {
  description = "Group holding the cloud administrator roles."
  type        = string
}

variable "region" {
  description = "Default region for regional resources."
  type        = string
  default     = "europe-west1"
}

variable "bootstrap_project_id" {
  description = "Project holding the bootstrap state and serving as quota project."
  type        = string
  default     = "hyprn-bootstrap"
}

variable "agents_project_id" {
  description = "Project for the agent fleet (ADR-0001)."
  type        = string
  default     = "hyprn-agents"
}

variable "agents_monthly_budget_eur" {
  description = "Monthly budget for the agents project, in EUR (alerts only, no cap)."
  type        = number
  default     = 100
}
