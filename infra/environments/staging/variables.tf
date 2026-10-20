variable "project_id" {
  type = string
  validation {
    condition     = can(regex("^hyprn-staging(-[a-z0-9]+)?$", var.project_id))
    error_message = "Use a dedicated hyprn-staging project, never bootstrap, fleet or production."
  }
}
variable "organization_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]+$", var.organization_id))
    error_message = "Supply the reviewed organization numeric ID."
  }
}
variable "billing_account" { type = string }
variable "region" { type = string }
variable "zone" {
  type = string
  validation {
    condition     = startswith(var.zone, "${var.region}-")
    error_message = "Zone must belong to the selected region."
  }
}
variable "host_image" {
  type = string
  validation {
    condition     = can(regex("^projects/[a-z0-9-]+/global/images/[a-z0-9-]+$", var.host_image))
    error_message = "Supply an exact reviewed image path, not an image family."
  }
}
variable "subnet_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.subnet_cidr))
    error_message = "Supply a reviewed IPv4 subnet."
  }
}
variable "sql_address" {
  type = string
  validation {
    condition     = can(cidrnetmask("${var.sql_address}/16"))
    error_message = "Supply the reviewed nonoverlapping /16 base address for SQL peering."
  }
}
variable "bucket_names" {
  type = object({ artifacts = string, desired = string, backup = string })
  validation {
    condition     = length(toset(values(var.bucket_names))) == 3
    error_message = "Artifacts, desired state and backups need distinct buckets."
  }
}
variable "operator_group" { type = string }
variable "recovery_group" { type = string }
variable "https_egress_cidrs" {
  type = set(string)
  validation {
    condition = length(var.https_egress_cidrs) > 0 && alltrue([
      for cidr in var.https_egress_cidrs : can(cidrnetmask(cidr)) && try(tonumber(split("/", cidr)[1]) >= 8, false)
    ])
    error_message = "Supply explicit reviewed IPv4 HTTPS destinations; default-wide routes are not allowed."
  }
}
variable "tunnel_egress_cidrs" {
  type = set(string)
  validation {
    condition = length(var.tunnel_egress_cidrs) > 0 && alltrue([
      for cidr in var.tunnel_egress_cidrs : can(cidrnetmask(cidr)) && try(tonumber(split("/", cidr)[1]) >= 8, false)
    ])
    error_message = "Supply explicit Cloudflare Tunnel IPv4 destinations."
  }
}
