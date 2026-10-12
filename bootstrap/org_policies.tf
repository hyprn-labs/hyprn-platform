locals {
  org = "organizations/${var.org_id}"

  # Set by Google's secure-by-default organization setup; adopted unchanged.
  existing_enforced = toset([
    "iam.automaticIamGrantsForDefaultServiceAccounts",
    "iam.disableServiceAccountKeyUpload",
    "iam.managed.disableServiceAccountKeyCreation",
    "storage.uniformBucketLevelAccess",
  ])

  # Platform baseline (cloud-platform.md sections 5.2, 5.3, 5.5).
  new_enforced = toset([
    "compute.managed.blockProjectSshKeys",
    "compute.managed.disableSerialPortAccess",
    "compute.managed.requireOsLogin",
    "compute.requireShieldedVm",
    "compute.skipDefaultNetworkCreation",
    "storage.publicAccessPrevention",
  ])
}

import {
  for_each = local.existing_enforced
  to       = google_org_policy_policy.enforced[each.key]
  id       = "${local.org}/policies/${each.key}"
}

resource "google_org_policy_policy" "enforced" {
  for_each = setunion(local.existing_enforced, local.new_enforced)

  name   = "${local.org}/policies/${each.key}"
  parent = local.org

  spec {
    rules {
      enforce = "TRUE"
    }
  }
}

import {
  to = google_org_policy_policy.allowed_member_domains
  id = "${local.org}/policies/iam.allowedPolicyMemberDomains"
}

resource "google_org_policy_policy" "allowed_member_domains" {
  name   = "${local.org}/policies/iam.allowedPolicyMemberDomains"
  parent = local.org

  spec {
    rules {
      values {
        allowed_values = [var.directory_customer_id]
      }
    }
  }
}

import {
  to = google_org_policy_policy.essential_contact_domains
  id = "${local.org}/policies/essentialcontacts.managed.allowedContactDomains"
}

resource "google_org_policy_policy" "essential_contact_domains" {
  name   = "${local.org}/policies/essentialcontacts.managed.allowedContactDomains"
  parent = local.org

  spec {
    rules {
      enforce    = "TRUE"
      parameters = jsonencode({ allowedDomains = ["@hyprn.ai"] })
    }
  }
}

import {
  to = google_org_policy_policy.internal_protocol_forwarding
  id = "${local.org}/policies/compute.managed.restrictProtocolForwardingCreationForTypes"
}

resource "google_org_policy_policy" "internal_protocol_forwarding" {
  name   = "${local.org}/policies/compute.managed.restrictProtocolForwardingCreationForTypes"
  parent = local.org

  spec {
    rules {
      enforce    = "TRUE"
      parameters = jsonencode({ allowedSchemes = ["INTERNAL"] })
    }
  }
}

# EU locations only (residency default, cloud-platform.md Q1).
resource "google_org_policy_policy" "resource_locations" {
  name   = "${local.org}/policies/gcp.resourceLocations"
  parent = local.org

  spec {
    rules {
      values {
        allowed_values = ["in:eu-locations"]
      }
    }
  }
}

resource "google_essential_contacts_contact" "admins" {
  parent                              = local.org
  email                               = var.admins_group
  language_tag                        = "en"
  notification_category_subscriptions = ["ALL"]

  depends_on = [google_project_service.bootstrap]
}
