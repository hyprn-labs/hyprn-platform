variable "project_id" { type = string }
variable "folder_id" { type = string }
variable "billing_account" { type = string }
variable "region" { type = string }
variable "subnet_cidr" { type = string }
variable "sql_address" { type = string }
variable "bucket_names" {
  type = object({ artifacts = string, desired = string, backup = string })
}
variable "recovery_group" { type = string }
variable "https_egress_cidrs" { type = set(string) }
variable "tunnel_egress_cidrs" { type = set(string) }
