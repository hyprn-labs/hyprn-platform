# Deployment contract v1

The staging contract joins a product release to platform-owned runtime bindings.
Its four JSON documents are defined in `deployment.schema.json`:

| Document | Owner | Content |
|---|---|---|
| `hyprn-workload/v1` | Product, within platform policy | Fixed components and lifecycle operations |
| `release/v1` | Product release builder | Exact source, schema, renderer, image, bundle, store and evidence pins |
| `runtime/v1` | Platform | Staging identity, storage, quotas, Cloudflare admission and secret references |
| `hyprn-desired/v1` | Environment publisher | Sequence, exact release, rendered configuration and artifact inventory |

All fields are closed. JSON text is accepted regardless of filename extension.
Hashes are lowercase hexadecimal SHA-256; image references include `@sha256:`.
JSON document hashes use UTF-8 JSON with sorted keys, no whitespace and no
non-finite numbers. Schema, renderer, archive and asset hashes identify file bytes.
The product pins this repository's full commit and the exact schema and renderer
hashes. Changes to either file require a new release pin.

## Validate and preview

```sh
python3 -B host/contract.py preview \
  --workload workload.json --release release.json --runtime runtime.json
python3 -B host/contract.py validate \
  --workload workload.json --release release.json --runtime runtime.json \
  --desired desired.json --bundle native.tar.gz
tests/platform/run.sh contracts
```

`preview` returns `config_sha256`, `release_sha256`, verification flags and the
platform-rendered configuration. `validate` returns the same identity fields
without the configuration. Validation failures exit 2 with a stable `error` code
and field `location`; input values are never echoed. Successful preview exits 0.
No operation creates, extracts, starts or changes a resource.

The desired configuration hash is obtained from the preview. The publisher then
adds the monotonic sequence and exact release inventory. Sequence monotonicity,
publisher authority and release freshness are enforced by the reconciler, not
by this stateless validator.

`fixtures.json` contains synthetic golden documents and negative mutations.
Its names, commits, addresses and digest pins are examples, not deployed resources
or evidence of scientific qualification.

## Runtime boundaries

The Compose portion runs only the existing app and modeling image entrypoints.
It uses their existing UIDs, read-only roots, dropped capabilities, bounded
resources and no published ports. Execution is a separate trusted host service;
its workers have no network or credentials. The host adapter must attach the
trusted tunnel ingress, enforce network/metadata policy, verify disk identity
and acquire writer fencing before any start.

Each secret is a pinned numeric Secret Manager version delivered as one
read-only file:

| Consumer | Aliases |
|---|---|
| Application | `modeling-auth`, `assistant-provider`, `db-app-request` |
| Modeling | `modeling-auth`, `modeling-rails` |
| Migration operation | `db-app-migration` |
| Backup operation | `db-app-backup` |
| Scientific execution and workers | None |

Secret paths are emitted as `HYPRN_SECRET_<ALIAS>_FILE` with uppercase underscore
alias spelling. They are interface inputs for the cloud adapter, not secret
values. The application request process never receives migration or backup
credentials. Platform identity supplies the secret project; descriptors cannot
add secret consumers or arbitrary paths.

Database binding separates the private connection address from the verified TLS
server name and pins the CA file bytes. A matching Cloud SQL certificate/DNS
configuration and cloud database adapter are required; disabling certificate
verification is not an alternative. The CA is public trust configuration,
mounted read-only at `/etc/hyprn/trust/cloudsql-server-ca.pem`.

The embedded Assistant runs inside the application. No external MCP, ChatGPT
transport or Managed OAuth scope is part of this contract, following
[product ADR-0014](../../../hyprn-mvp/docs/adr/0014-embedded-assistant-staging.md).

## What validation proves

The CLI checks structure, pins, fixed authority, source identity shape, store
compatibility and agreement between documents. With `--bundle` it checks archive
size/hash and rejects unsafe members without extraction. It does not download or
verify image bytes, authenticate evidence, verify a host attestation, establish
database permissions, enforce a firewall, or prove the images boot successfully.
`artifact_bytes_verified` therefore remains false. Those are host/release
acceptance obligations; this preview alone is never authorization to start.
