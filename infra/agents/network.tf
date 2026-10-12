resource "google_compute_network" "agents" {
  name                    = "hyprn-agents-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "agents" {
  name                     = "hyprn-agents-subnet"
  network                  = google_compute_network.agents.id
  region                   = var.region
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true
}

# SSH only from IAP's TCP forwarding range, only to the host's identity.
# All other ingress is denied by the VPC's implied rule.
resource "google_compute_firewall" "allow_iap_ssh" {
  name          = "hyprn-agents-allow-iap-ssh"
  network       = google_compute_network.agents.id
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  target_service_accounts = [
    google_service_account.host.email,
    google_service_account.wake.email,
  ]
}

# Outbound internet (GitHub, Slack, Anthropic, package mirrors) without a
# public IP on the VM.
resource "google_compute_router" "agents" {
  name    = "hyprn-agents-router"
  network = google_compute_network.agents.id
  region  = var.region
}

resource "google_compute_router_nat" "agents" {
  name                               = "hyprn-agents-nat"
  router                             = google_compute_router.agents.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
