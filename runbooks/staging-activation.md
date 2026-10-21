# Staging qualification access

`host/activation.py` opens a reviewed, finite qualification window for the exact
installed release. A root-owned policy names the protected product binding,
desired digest, deployment journal, disk policy, pinned service-network policy
and UTC Unix `not_before` / `not_after` times. Windows are at most 24 hours.
The deployment plan must include the actual times and policy digest for approval.

The timer renews a 240-second admission lease after fresh observations. It takes
the existing deployment lock, verifies the live Google host and desired object,
checks the network enforcer, compares running containers with the renderer,
verifies the installed native payload and current worker attestation, and probes
the actual ingress with missing and malformed assertions. It never starts a
container, changes attestation, launches a model or sends a provider message.
A failure closes admission; a killed renewer loses admission at expiry. Existing
accepted native work is not canceled. Renewal never changes the shared allowance.
The same lock prevents reopening during deployment or backup.

The probe requires an application response only after its startup has completed.
Hosted startup already reads the pinned Claude agent/environment definitions,
enumerates all credential-visible sessions and reconciles actual usage against
the retained ledger. A missing session or uncertain cost refuses startup. An
origin 401 proves that unauthenticated ingress is rejected; it does not prove a
successful login, two-user isolation, a scientific answer or human acceptance.

## Before first startup

1. Verify the approved provider definition pins match the product release being
   installed. A changed release playbook/tool definition needs a matching reviewed
   provider resource version; existing provider identifiers are not a substitute.
2. Fence the previous local Assistant delivery owner. Identify its exact process,
   startup registration and credential configuration; stop only that installation
   and disable its delivery restart. Preserve its study records and ledger. Include
   those exact operations in the deployment plan, rather than stopping unrelated
   development sessions. A stopped process alone is not a durable fence.
3. Read all provider sessions and current settled costs after the fence. Every
   session must be idle or terminated and classified once. Carry prior spending
   exactly once; do not add the local prior allowance twice or reset usage.
4. Bind `hyprn-assistant-continuity/v1` to installation, release/configuration and
   managed-Assistant configuration digests. Record the reviewed inventory digest.
   Preserve the previously approved shared total and its recorded conversion;
   account top-ups do not raise that total. Do not introduce a per-study cap.
5. Install the closed application through bootstrap, qualify the restricted worker
   on this host, then install the reviewed activation policy and generated timer.
   Units, scripts and policy remain host-owned. The app can read admission only.

## Real first-use verification

Use the approved staging hostname through Cloudflare Access. There is no hosted
HYPRN password: the verified issuer and subject resolve the account identity.
The browser obtains a product session with `POST /api/1/session/external`, with
secure HTTP-only cookie and CSRF protection. Neither an invented identity nor a
locally signed fixture assertion establishes a production login.

- **Login:** first approved human signs in and refreshes the UI. Confirm the
  profile and study list. An unauthenticated external request must be challenged;
  missing/malformed origin assertions remain 401. Log out and confirm the product
  session cannot be reused. Do not save cookies, JWTs or CSRF tokens in evidence.
- **Isolation:** two approved humans use separate browser contexts. Each creates
  a private study with a distinct harmless title. Both cross-study GETs must fail
  and neither private study appears in the other's list. Repeat for conversation
  and a saved model/configuration/run if authored. The second human authenticates
  personally; absent participation leaves this check explicitly unverified.
- **Execution and Assistant:** send one command through the study's actual chat,
  using a stable `command_id`; if delivery is uncertain, inspect the same command
  instead of resending a new identifier. Ask it to create the simple study below
  using platform tools, real samples and independently validated estimates. Let
  the existing shared budget owner enforce the approved remaining allowance.
  Record provider conversation identity, actual tool outcomes, run receipts and
  final settled incremental cost. These are integration evidence, not a claim of
  scientific validity for a real cooling design.
- **Exploration:** record completed native run count, move at least two inputs
  jointly (including an exact saved point and an unsampled interior combination),
  verify calculated/estimated labels and numerical values, then confirm run count
  did not increase. Refresh and repeat one joint selection. All accuracy and
  prediction-domain checks remain in force; do not loosen tolerances to pass.
- **Recovery:** stop the renewal timer and verify refusal after lease expiry,
  then restart it within the same approved window. It must restore access only
  after fresh observations. Keep accepted native work and stored answers intact.

A bounded integration study brief:

> Create an illustrative sensible-heat study, with heat load 12 kW, mass flow
> 0.30 kg/s and specific heat 4.2 kJ/(kg K). Compute temperature rise and capacity
> margin against an explicit allowable rise of 10 K. Include the simultaneous
> point 15 kW, 0.25 kg/s, 3.8 kJ/(kg K). Prepare joint exploration over load
> 12–15 kW and flow 0.25–0.30 kg/s, with specific heat fixed at 4.2 kJ/(kg K).
> Use the platform's real sampled analysis, independent surrogate validation and
> pre-publication coverage checks; publish only when those pass. No reference
> document is supplied: label these illustrative inputs and state the ideal
> steady sensible-heat assumptions. Distinguish this thermal screen from qualified
> cooling-system design. Keep the answer concise.

Independent arithmetic expectations: nominal rise is 9.5238095 K and margin
0.6 kW; the simultaneous adverse point is 15.7894737 K and margin −5.5 kW.
The fixed-specific-heat exploration does not silently include the adverse
specific heat: that comparison is its own explicit configuration/analysis.

Record tested release/configuration, actual paths and statuses, output values,
validation tolerances and observed errors, provider cost and cleanup. Keep
credentials out of records. Automated checks and human acceptance are separate.
Disable the qualification timer after verification. Persistent staging admission
requires an explicitly reviewed ongoing policy; extending a timestamp silently
is not approval.
