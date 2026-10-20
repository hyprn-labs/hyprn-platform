variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.account_id))
    error_message = "Supply the reviewed Cloudflare account ID."
  }
}
variable "zone_id" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.zone_id))
    error_message = "Supply the reviewed hyprn.ai zone ID."
  }
}
variable "team_name" {
  type = string
  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", var.team_name))
    error_message = "Supply the exact Cloudflare Access team subdomain."
  }
}
variable "admitted_emails" {
  type      = set(string)
  sensitive = true
  validation {
    condition = length(var.admitted_emails) > 0 && alltrue([
      for email in var.admitted_emails :
      can(regex("^[a-z0-9][a-z0-9._+%-]*@[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$", email))
    ])
    error_message = "Supply nonempty exact lowercase email addresses; wildcards and domain invitations are forbidden."
  }
}
variable "loopback_origin" {
  type = string
  validation {
    condition = try(
      can(regex("^http://127\\.0\\.0\\.1:[1-9][0-9]{0,4}$", var.loopback_origin)) &&
      tonumber(split(":", var.loopback_origin)[2]) <= 65535,
      false
    )
    error_message = "Origin must be http://127.0.0.1 with an explicit valid TCP port and no path."
  }
}
