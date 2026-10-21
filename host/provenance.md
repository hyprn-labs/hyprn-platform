# Host runtime packages

`host-packages.json` pins the Debian 12 AMD64 host packages, their original URLs,
lengths, archive SHA256 values, installed executable SHA256 values and upstream
licence identities. Archives stay outside Git. No package is installed by planning.

| Component | Pinned release | Official source | Licence |
|---|---|---|---|
| Docker Engine and CLI |29.8.2|[Docker Debian repository](https://download.docker.com/linux/debian/)|Apache-2.0|
| containerd (including runc) |2.3.6|[Docker Debian repository](https://download.docker.com/linux/debian/)|Apache-2.0|
| Docker Compose plugin |5.6.0|[Docker Compose](https://github.com/docker/compose/releases/tag/v5.6.0)|Apache-2.0|
| Cloudflare connector |2026.10.2|[Cloudflare release](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.2)|Apache-2.0|

The Docker index is authenticated by its signed Bookworm InRelease and the
Docker signing-key fingerprint `9DC858229FC7DD38854AE2D88D81803C0EBFCD88`.
The connector archive matches the SHA256 published in its official release and
release-asset metadata. Binary hashes come from reading the authenticated Debian
archives. Upstream licence texts are separately hashed in the package manifest;
the engine's Apache notice is also present in its packaged service files.
Bundled notices remain in the unmodified packages. Existing Debian OS libraries
retain their distribution licences and are checked as prerequisites; this setup
does not silently upgrade or download missing dependencies.

Installation uses the [official Debian package format](https://docs.docker.com/engine/install/debian/#install-from-a-package).
Automatic upstream repositories and convenience installers are not configured;
updates require a new reviewed package pin and host operation. Compose is the
current CLI plugin invoked as `docker compose`; its major 5 release is accepted
alongside major 2, always with an exact version and executable hash. Legacy Python
Compose remains unsupported.


## Explicit Debian host dependencies

The host package manifest also pins `libjansson4` 2.14-2 (MIT/Expat),
`libnftables1` and `nftables` 1.0.6-2+deb12u2 (GPL-2/GPL-2+, with
CC-BY-SA-4.0 documentation). These are unmodified operating-system packages,
not linked into or redistributed as the HYPRN application. Their Debian copyright
files are retained by installation and hashed in the manifest. The manifest's
per-package `scope` distinguishes these host dependencies from product libraries.

Archives come from the official Debian Bookworm repository. The exact Packages.xz
hash is verified against InRelease, authenticated by the Bookworm archive signing
subkey `4CB50190207B4758A3F73A796ED0E7B82643E131` in the reviewed Debian keyring.
The older keyring verifies that Bookworm signature but cannot verify the second,
newer archive signature; the accepted authentication is explicitly the valid
Bookworm signature, not a claim that every signature verified.

All declared dependencies and pre-dependencies are checked explicitly using
installed package states and Debian version comparison. Unsupported dependency
syntax is refused. A package installation dry-run alone does not establish that
configure-time dependencies are met. Separate bounded diagnostics distinguish
that dry-run from actual package installation and configuration failures.

## Restricted application HTTPS proxy

`egress-proxy.json` pins Envoy 1.40.0's official Linux x86-64 executable,
SHA256, length, Apache-2.0 licence and upstream notice. The downloaded bytes
match the SHA256 in the upstream GitHub release asset metadata. This is a
host-only dependency, separately proposed for installation; it is not part of
candidate execution or the product's Python dependencies.

The renderer enables two exact CONNECT destinations, with TLS remaining between
the application and its provider. No dynamic destination discovery, administrative
listener, caching, TLS interception or optional protocol modules are configured.
The proxy runs under a dedicated unprivileged identity with resource limits;
host output rules deny private and metadata destinations even after DNS changes.
Only the application's designated address may reach its listener.

The Debian Bookworm Squid package was not selected: its security tracker lists
unresolved request-parsing issues in 5.7-2+deb12u6. No Squid package was installed.
Current official Envoy source and release metadata are recorded in the manifest.
Live staging containment remains a separate acceptance requirement.
