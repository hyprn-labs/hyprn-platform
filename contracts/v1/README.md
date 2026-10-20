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

The Compose portion declares the app and modeling services plus a dispatcher
template using the exact app image pin.
It uses their existing UIDs, read-only roots, dropped capabilities, bounded
resources and no published ports. Execution is a separate trusted host service;
its workers have no network or credentials. The host adapter must attach the
trusted tunnel ingress, enforce network/metadata policy, verify disk identity
and acquire writer fencing before any start.

Each secret is a pinned numeric Secret Manager version delivered as one
read-only file:

| Consumer | Aliases |
|---|---|
| Application | `modeling-auth`, `assistant-provider`, `db-app-request`, `db-app-auth`, `db-assistant-background` |
| Dispatcher | `modeling-auth`, `db-app-request`, `db-dispatcher-background` |
| Modeling | `modeling-auth`, `modeling-rails` |
| Migration operation | `db-app-migration` |
| Backup operation | `db-app-backup` |
| Scientific execution and workers | None |

Secret paths are emitted as `HYPRN_SECRET_<ALIAS>_FILE` with uppercase underscore
alias spelling. They are interface inputs for the cloud adapter, not secret
values. `db-app-auth` belongs to the separate read-only credential lookup role
`hyprn_auth`; study access uses `hyprn_request`. The application never receives migration or backup
credentials. Platform identity supplies the secret project; descriptors cannot
add secret consumers or arbitrary paths.

The assistant and dispatcher discovery roles are respectively
`hyprn_assistant_background` and `hyprn_dispatcher_background`, bound by required
`assistant_background_role` and `dispatcher_background_role` fields. Their
credentials authorize only bounded database discovery functions; each returned
item then uses the request connection with its actor context. Database grants
and discovery behavior are product migration/adapter acceptance obligations.

The dispatcher has the app UID, a writable application artifact subdirectory,
and a read-only TLS CA. It receives no authentication, provider, migration or
backup credential. Its `host-dispatcher` profile excludes it from ordinary
Compose startup. The host owns run/attach, fixed stdio, child lifetime and the
fixed `python -B -m hyprn_mvp_app.dispatcher --with-exports` invocation, with
open stdin and no TTY. The dispatcher has no public port, Docker socket or
native execution credentials. The native execution host still receives no
application credentials.

Dispatcher egress defaults to deny and permits only modeling TCP 3000 and the
bound database address TCP 5432. The internal dispatcher network requires a
host-controlled private database route and firewall enforcement; internal
network membership alone does not provide that route. Provider and metadata
egress remain denied. Those requirements appear in `start_requires`.
Product phase 06-05 implements and verifies the cloud entrypoint, host-owned
bridge lifecycle and effective network policy. The existing local launcher
executes the dispatcher inside the request app; it does not implement this
separate cloud template. No boot or connectivity result follows from preview.

Database binding separates the private connection address from the verified TLS
server name and pins the CA file bytes. A matching Cloud SQL certificate/DNS
configuration and cloud database adapter are required; disabling certificate
verification is not an alternative. The CA is public trust configuration,
mounted read-only at `/etc/hyprn/trust/cloudsql-server-ca.pem`.
Infrastructure must select a Cloud SQL server-CA mode that supports the chosen
verified DNS name, then obtain and verify the actual instance certificate SAN
and CA bytes. A default self-signed certificate's common name is not assumed
to match a Cloud SQL DNS name.

The embedded Assistant runs inside the application. No external MCP, ChatGPT
transport or Managed OAuth scope is part of this contract, following
[product ADR-0014](../../../hyprn-mvp/docs/adr/0014-embedded-assistant-staging.md).

### Managed Assistant binding

`release.assistant` pins `definitions_sha256` and `configuration_sha256` from
the product's release-bound managed setup. `runtime.assistant` repeats those
exact hashes and supplies `provider: claude-managed-agents`, `agent_id`,
`agent_version` (canonical positive decimal string), `environment_id` and
`budget`. Provider IDs use the product adapter's 1–128 character identity
format. The setup command's successful reviewed readback supplies the IDs,
version and hashes; the examples in fixtures are synthetic.

Only the application receives these settings:

| Runtime field | Product environment suffix after `HYPRN_MVP_ASSISTANT_` |
|---|---|
| `agent_id`, `agent_version`, `environment_id` | `AGENT_ID`, `AGENT_VERSION`, `ENVIRONMENT_ID` |
| `definitions_sha256`, `configuration_sha256` | `DEFINITIONS_SHA256`, `CONFIGURATION_SHA256` |
| `budget.total_cents`, `budget.prior_cents` | `TOTAL_CENTS`, `PRIOR_CENTS` |
| `budget.approved_minor`, `budget.approved_currency` | `APPROVED_MINOR`, `APPROVED_CURRENCY` |
| Date portion of `budget.conversion_timestamp` | `CONVERSION_DATE` |
| Existing `assistant-provider` secret file | `KEY_FILE=/run/secrets/assistant-provider` |

The generic `HYPRN_SECRET_ASSISTANT_PROVIDER_FILE` remains an alias for the same
file. The numeric Secret Manager version stays in `runtime.secrets`; credential
bytes never enter a descriptor, argument or environment value. The host secret
loader must create an app-owned regular file with mode 0600 before mounting it
read-only: the product credential reader rejects symlinks, wrong ownership and
group/world permissions. Dispatcher, modeling, execution and workers receive no
Assistant settings or provider credential.

The closed budget object requires `scope: installation`, `currency: USD`,
`total_cents` from 1 to 1,000,000, explicit `prior_cents` from zero to less than
the total, `prior_spending_policy: carry-forward-untracked-spend` and
`history_policy: preserve-and-reconcile-all-sessions`. The total is the shared
ceiling, including prior spending; it is not a new allowance for each study,
session, child agent, restart or release. Prior cents cover spending outside
the retained session inventory and must not double-count those sessions.
Provider session caps are derived by the product from remaining shared allowance.

`approved_minor` is a positive integer up to 1,000,000; `approved_currency` is
EUR or USD, both with cents as their minor unit. Provider billing is USD. The binding requires
an explicit decimal-string `usd_per_approved_currency`, UTC
`conversion_timestamp` and `conversion_policy: floor-to-provider-cent`.
`total_cents` must equal the exact decimal product of approved minor units and
the conversion rate, rounded down to a USD cent. The validator neither obtains
an exchange rate nor treats EUR cents as USD cents. The fixture's 1.10 rate and
timestamp and EUR 100 approval are synthetic, not live spending authorization.
For USD approval the rate must equal one. The startup review must
verify the rate's provenance and the approved conversion before activation.

Startup requires `assistant-resource-readback-and-release-definition-match`
and `assistant-shared-spending-continuity-reconciled`. The host/product startup
consumer must compare the setup configuration to the pinned release and re-read
the provider resources, preserve all session accounting across replacement or
rollback, reconcile uncertain sessions and carried spending, and refuse startup
if continuity is unknown. Changing a release or resource must not reset prior
spending. Changing an approved amount or converted USD ceiling requires a
separately reviewed runtime update. Actual spending authorization belongs in
the deployment's private operational review, not the platform schema or fixtures.
The desired configuration hash changes with every resource or budget
change. This stateless validator cannot determine whether a supplied zero is
historically correct or enforce a transition from an earlier runtime.

The product currently reads every setting above except `CONFIGURATION_SHA256`:
that hash is retained for the startup/release consumer. Its allowance admission
reads recorded provider sessions afresh and adds explicit prior spending before
permitting a turn. Provider readback, historical continuity, secret file ownership
and effective egress still require cloud adapter/host acceptance. Preview makes
no provider request and supplies no cloud boot or spending qualification.

## What validation proves

The CLI checks structure, pins, fixed authority, source identity shape, store
compatibility and agreement between documents. With `--bundle` it checks archive
size/hash and rejects unsafe members without extraction. It does not download or
verify image bytes, authenticate evidence, verify a host attestation, establish
database permissions, enforce a firewall, or prove the images boot successfully.
`artifact_bytes_verified` therefore remains false. Those are host/release
acceptance obligations; this preview alone is never authorization to start.

For shared-CA server identity, the binding accepts the documented
`INSTANCE_UID.PROJECT_DNS_LABEL.REGION.sql-psa.goog` name for private services
access, or `INSTANCE_UID.PROJECT_DNS_LABEL.REGION.sql.goog` for Private Service
Connect/public IP. Record the actual instance SAN name, without a terminal DNS
root dot; arbitrary hostnames, IP literals and suffix extensions are rejected.
The private connection address remains separate and `verify-full` remains
mandatory. These formats follow Google's
[server identity verification documentation](https://docs.cloud.google.com/sql/docs/postgres/configure-ssl-instance#server-identity-verification),
verified on 2026-10-20. This is a structural allowlist, not a substitute for the
live certificate and CA check.
