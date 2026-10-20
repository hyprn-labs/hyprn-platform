# Runtime secret delivery

`host/secrets.py` supplies fixed, numeric-version runtime secrets to individual
consumers. It also provides a separate, explicitly approved transfer of an
existing private provider key file to the existing `assistant-provider` secret.
Terraform creates secret metadata; it never carries credential bytes or versions
with secret payloads in configuration, plans or state.

## Preconditions

Use the reviewed runtime document, expected project ID and numeric project number.
Delivery requires an explicit `--identity-mode`. On GCP hosts, select
`attached-service-account`: the standard-library client checks the fixed metadata
server's project ID, project number and principal against the Terraform-owned
`hyprn-staging-runtime@PROJECT_ID.iam.gserviceaccount.com` identity before requesting
a short-lived token. It reads exact versions from the fixed Secret Manager HTTPS
endpoint, checks returned resource identity and CRC32C, and keeps the token only
in process memory. No gcloud, ADC, proxy, environment credential, configurable
endpoint, redirect or authentication fallback is used in this mode. Host firewall
policy must reserve metadata access to trusted host services and deny containers.
Metadata answers are trusted only within that GCP host boundary; this command
does not establish host attestation or prevent a compromised root from lying.

`dedicated-operator` uses the audited Google Cloud CLI with dedicated HYPRN
`CLOUDSDK_CONFIG` and `GOOGLE_APPLICATION_CREDENTIALS`; missing paths fail closed.
Use it for isolated operator delivery checks, not VM personal credentials.
Transfer always uses this operator identity. CLI configurations must not contain
unreviewed endpoint, impersonation or credential overrides. Supply the reviewed
absolute gcloud executable path. These are authority inputs, not product-controlled settings. The tool validates the
closed runtime schema, exact secret-name aliases and explicit project identity;
the parent reconciler remains responsible for release validation and fencing.

Production delivery requires Linux root, an existing root-owned mode 0700
directory on tmpfs, and disabled swap. Every path component must be a real
directory owned by root or the caller; writable parents must have the sticky bit.
Core dumps are disabled. Provision the tmpfs mount and lifetime in the host
setup; this command neither mounts filesystems nor starts/stops services.
The renderer expects `runtime.mounts.secrets` as the supplied root; another root
is for a separately mounted isolated acceptance installation only.

## Deliver and remove

```sh
python3 -B host/secrets.py deliver --runtime "$RUNTIME" \
  --project-id "$PROJECT_ID" --project-number "$PROJECT_NUMBER" \
  --identity-mode attached-service-account --root "$SECRET_ROOT" --consumer app
python3 -B host/secrets.py cleanup --runtime "$RUNTIME" \
  --project-id "$PROJECT_ID" --project-number "$PROJECT_NUMBER" \
  --root "$SECRET_ROOT" --consumer app
```

Consumers are exactly `app`, `dispatcher`, `modeling`, `migration`, and `backup`.
The fixed contract mapping supplies their aliases. App, dispatcher and the two
application database operations use UID/GID 10002; modeling uses 10001. Each file
has mode 0600 and its consumer UID; each consumer directory is root-owned 0700.
The container runtime performs single-file, read-only mounts, so the service
does not need host directory traversal. No execution or worker consumer exists.
`cloudflare-tunnel` is not in `SECRET_CONSUMERS` and is not delivered by this CLI.
The host tunnel credential, configuration and lifecycle remain an 08-02 obligation.

Delivery checks Google identity, reads exact pinned versions through its selected
transport, decodes binary payloads in memory, and publishes a
complete consumer directory by rename. Root-directory locking serializes local
delivery and cleanup. No shell command, secret argument, token environment,
payload log or implicit `latest` exists. In operator mode, CLI file/HTTP logging
and telemetry are disabled and stderr discarded.

An existing consumer or interrupted `.loading-CONSUMER` directory blocks delivery.
For rotation, the reconciler must close admission, stop the consumer and unmount
old files before cleanup and delivery at the new numeric pin; existing bind mounts
otherwise retain old inodes. Migration/backup delivery occurs immediately before
the corresponding operation, and cleanup belongs in its guaranteed finalization.
Restart recovery must clean interrupted operation credentials before admission.
Cleanup checks all names, owners, types, permissions and hardlink counts first;
unexpected entries or links stop cleanup without recursive deletion. Controlled
fetch failures remove this invocation's partial files. A process kill can leave
the private staging directory, which the same cleanup command can inspect/remove.
Tampered/partially initialized ownership requires operator inspection, not a
broader delete. No overwriting or automatic rotation of running services occurs.

## Transfer an existing provider key

This command is a cloud write. Obtain the platform owner's go for the exact
project, secret and source file before invoking it. `--approve-resource` records
the caller's explicit target choice; it cannot establish human authorization.
The source remains the master-copy workflow's existing file; it must be mode
0600, owned by the caller, regular, single-link and inside a private directory.
Use a persistent mode 0700 receipt directory outside Git and Terraform state.

```sh
python3 -B host/secrets.py transfer-provider \
  --project-id "$PROJECT_ID" --project-number "$PROJECT_NUMBER" \
  --gcloud "$GCLOUD" --key-file "$PROVIDER_KEY_FILE" \
  --receipt-root "$TRANSFER_RECEIPT_ROOT" \
  --approve-resource "projects/$PROJECT_NUMBER/secrets/hyprn-staging-assistant-provider"
```

Transfer takes explicit staging project identity without a runtime document;
bootstrap precedes the agent IDs and numeric version that runtime will pin.
The command checks project identity and the existing secret resource before
reading the source. The key is passed through stdin to `versions add --data-file=-`,
never through arguments, environment, logs or Terraform. It emits only the new
numeric version resource and leaves the source file intact. Review that version
and explicitly update the runtime pin in the normal deployment workflow.

`assistant-provider-transfer.json` is fsynced before dispatch and records only
target/status, then the returned numeric version on success. Any existing receipt
blocks another attempt. A timeout, process interruption, malformed response or
failed result after dispatch is uncertain: inspect Secret Manager version metadata
and audit records, reconcile the result and record a decision before retrying.
Never remove/change the receipt or choose a fresh directory just to retry. A
later intentional key rotation needs its own reviewed source and receipt scope.
The CLI makes one subprocess call for the write; live Google transport/retry
behavior still needs qualification against the audited installed SDK.

## Evidence and remaining acceptance

`tests/platform/run.sh secrets` exercises the actual parser and command functions
in subprocesses with a fixed synthetic gcloud executable and isolated real files.
Transfer tests use the unmodified CLI. On the development macOS host, delivery
tests replace only Linux/tmpfs qualification and the privileged ownership mapping
inside a test launcher; there is no production bypass flag. They verify isolation,
binary payloads, modes, pins, cleanup, links, locking, redaction, explicit transfer
target checks and refusal to repeat uncertain writes. Attached-service-account
tests replace the HTTP transport, verify wrong-principal rejection before token
request, no ADC/CLI fallback, exact version paths and the standard CRC32C check
vector. They do not prove Linux
UID assignment, effective bind mounts, live IAM or Google transport behavior.

Before enabling host admission, qualify on an isolated GCP Linux tmpfs with the
attached runtime identity, inspect UID/GID 10001/10002 and 0600 modes,
exercise real single-file read-only mounts, verify cross-consumer denial, inject
termination during delivery/transfer, and verify cleanup through the parent
operation lifecycle. Full 08-02 reconciliation remains incomplete.

No cloud write, credential read, live secret payload fetch, service activation or
dependency installation was performed to implement this prerequisite.

Official CLI behavior checked on 2026-10-20:
[binary-safe access](https://docs.cloud.google.com/sdk/gcloud/reference/secrets/versions/access)
and [stdin version creation](https://docs.cloud.google.com/sdk/gcloud/reference/secrets/versions/add).
Attached identity follows [Google metadata](https://docs.cloud.google.com/compute/docs/metadata/querying-metadata)
and [Secret Manager access/integrity](https://docs.cloud.google.com/secret-manager/docs/access-secret-version).

## Approved staging provider transfer — 2026-10-20

After explicit owner approval of the exact resource and source file, the
`transfer-provider` CLI copied the existing provider key to the staging
assistant-provider container. It exited0 and produced numeric version1;
read-only Google metadata confirms that version is ENABLED. The source remains
intact. The receipt and target identifiers are retained in the owner's private
credential directory, not Git. Verification did not retrieve the payload.
Do not repeat this transfer or bypass the receipt on resumed work.

The separately approved restricted Claude environment was created and verified.
Agent creation was definitively rejected because the provider API balance is
too low; the key transfer does not resolve that billing prerequisite. No
conversation/model request or application activation occurred. Live Linux
consumer delivery remains a separate uncompleted acceptance step.
