variable "state_bucket_name" {
  description = "Globally unique dedicated staging Terraform state bucket."
  type        = string
  validation {
    condition     = length(var.state_bucket_name) <= 63 && can(regex("^hyprn-staging(-[a-z0-9]+)*-tfstate$", var.state_bucket_name))
    error_message = "Use a dedicated hyprn-staging state bucket, never fleet or bootstrap state."
  }
}

variable "location" {
  description = "Reviewed EU storage location."
  type        = string
  validation {
    condition     = var.location == "EU" || can(regex("^EUROPE-[A-Z]+[0-9]+$", var.location))
    error_message = "Supply an explicit uppercase EU location."
  }
}
