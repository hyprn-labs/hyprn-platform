variable "project_id" {
  description = "Agent fleet project, created by bootstrap/."
  type        = string
  default     = "hyprn-agents"
}

variable "region" {
  type    = string
  default = "europe-west1"
}

variable "zone" {
  type    = string
  default = "europe-west1-b"
}

variable "admins_group" {
  description = "Group allowed to reach the host through IAP and OS Login."
  type        = string
  default     = "gcp-admins@hyprn.ai"
}

variable "subnet_cidr" {
  type    = string
  default = "10.10.0.0/24"
}

variable "host_machine_type" {
  description = "Sized for build and test load; runs only when in use (ADR-0002)."
  type        = string
  default     = "t2d-standard-8"
}

variable "host_disk_gb" {
  type    = number
  default = 100
}

variable "wake_machine_type" {
  description = "Always-on wake service; outbound only (ADR-0002)."
  type        = string
  default     = "e2-micro"
}

variable "host_image" {
  description = "Pinned Debian 12 image; updated by a reviewed change, never by family lookup."
  type        = string
  default     = "projects/debian-cloud/global/images/debian-12-bookworm-v20261006"
}

variable "agents" {
  description = "Agent names (agents/host/agents.txt); each gets a GitHub App key secret."
  type        = list(string)
  default     = ["ada", "codd"]
}

variable "slack_agents" {
  description = "Agents steered from Slack; each gets Slack token secrets."
  type        = list(string)
  default     = ["ada"]
}
