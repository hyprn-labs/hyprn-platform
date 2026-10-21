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
