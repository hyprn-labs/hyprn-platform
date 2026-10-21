# Database and runtime secret operator

`host/database_operator.py` performs the reviewed Cloud SQL bootstrap-user and
Secret Manager writes from the operator machine. It obtains a short-lived token
through the dedicated HYPRN Google CLI configuration, holds it only in memory,
and sends REST bodies directly to fixed Google HTTPS endpoints. The VM retains
its accessor-only service account and receives neither Google CLI nor operator
credentials. [Host role setup](database-setup.md) is the separate private SQL step.

## Plan

The operator policy contains exactly:

- `schema`: `hyprn-database-operator/v1`.
- `database`: the complete host database policy.
- `database_plan_sha256`: the exact generated host plan digest.
- `project_number`: the numeric Google Cloud project identity.
- `operator_account`: the approved active account in the dedicated configuration.
- `gcloud`, `gcloud_sha256`, `gcloud_config`: the approved local executable, its
  bytes' SHA256, and the dedicated configuration directory.

These local values belong in the private deployment review, not in the repository.
Planning checks the host plan digest and pins all four source modules. It creates
no credential and performs no cloud call.

```sh
python3 -B host/database_operator.py plan --policy /review/operator-policy.json
```

Every later operation requires `--policy`, `--private-root` (existing owner-only
`0700` directory) and `--approve-sha256` with that exact operator plan digest.
The fixed mutation scope is one temporary bootstrap user, its later removal, and
one version in each of these nine existing secrets:

- Six `hyprn-staging-db-*` application-role secrets.
- `hyprn-staging-modeling-auth` and `hyprn-staging-modeling-rails`.
- `hyprn-staging-cloudflare-tunnel`.

All nine secrets must have **no prior versions** when their publication starts.
The Assistant provider secret is excluded, as are IAM changes, user password
updates and any creation of a new Secret Manager resource. Cloud SQL metadata is
checked again before each API operation: exact project/instance, PostgreSQL 17,
private-only IPv4, private DNS identity, CA bytes and encrypted connection policy.

## Sequence

1. Run `create-user`. It writes a random bootstrap password in protected local
   storage and records intent before calling the API once. The result must be
   `created`, not merely a successful process invocation. Copy that password to
   host tmpfs through the reviewed authenticated channel, then apply the host
   database plan. No password is placed on a command line or printed.
2. Capture the host's six password files and `complete.json` in protected operator
   storage through that channel. For each role, run `publish-secret --alias ALIAS
   --password-file FILE --preparation-receipt HOST_COMPLETE_JSON`. The prepared
   host receipt must match the role plan, contain all six distinct credential
   hashes and bind the bytes to the selected alias. Publication adds one version,
   verifies its numeric identity, reads it back and checks bytes and CRC32C.
3. Generate modeling credentials with `prepare-secret --alias modeling-auth` and
   `prepare-secret --alias modeling-rails`. This local-only operation needs no
   Google token. It creates a 64-hex password and a plan-bound checksum receipt in
   the operator private root. Publish each using the file and receipt paths
   returned by preparation. Repeated preparation refuses rather than rotates.
4. Read the token of the exact existing tunnel through the separately reviewed
   Cloudflare operation. Keep the returned raw token in an owner-only `0600` file.
   Its separate protected receipt has exactly the following fields; do not
   reinterpret or invent the token's format:

   ```json
   {
     "schema": "hyprn-prepared-secret/v1",
     "plan_sha256": "OPERATOR_PLAN_SHA256",
     "alias": "cloudflare-tunnel",
     "payload_sha256": "SHA256_OF_CAPTURED_TOKEN_BYTES"
   }
   ```

   Publish it with `publish-secret --alias cloudflare-tunnel --password-file FILE
   --preparation-receipt RECEIPT`. Token acquisition provenance and resource identity
   are established by the reviewed reader; this publisher checks the exact bytes.
5. Run `delete-user --preparation-receipt HOST_COMPLETE_JSON`. It requires the
   successful creation receipt, verified host role receipt and all six numeric
   database secret publication receipts. It verifies those versions remain enabled,
   then deletes only the original temporary user and checks its absence.
6. Run host `database_setup.py verify` to confirm bootstrap removal and ordinary
   role authority over private TLS. Bind all nine numeric version receipts into
   the runtime descriptor. Release transient secret copies only after final
   verification and Secret Manager read-back are complete.

The host preparation receipt is not itself proof of secret publication or
bootstrap removal. The two latter operations each have their own receipts.

## Pending and uncertain API outcomes

API operations can be asynchronous. A pending/uncertain result exits **4**, with
no automatic repeated mutation. Use `reconcile-user`, `reconcile-secret` (same
alias/file/receipt arguments), or `reconcile-delete` to perform read-only lookup.
A known operation is polled by its exact recorded name. A secret response lost
in transit can be reconciled only when exactly one enabled version exists and
its bytes and CRC32C match the already-persisted intent and prepared receipt.

A lost user-creation response without an operation name remains uncertain even if
a user with the name appears. It is not adopted automatically. Inspect the cloud
operation record and authentication evidence, then review the recovery; never
create the same user again or reset its password. User deletion is similarly
never replayed after an unknown outcome. API errors expose a reason code and HTTP
status only; provider response bodies and credentials are never printed.

After any nonzero exit, keep protected recovery files and the application closed.
A lack of a completion receipt is not proof that the cloud operation did nothing.

## Verification scope

Isolated tests cover fixed request destinations and body bytes, exact approval,
wrong-instance refusal, per-role credential binding, no provider-key rewrite,
no overwrite of existing secret versions, and lost-response reconciliation.
Read-only preflight can check live identities and empty version preconditions;
it does not establish that future IAM-protected writes or application login work.
Those remain part of the approved live deployment acceptance.
