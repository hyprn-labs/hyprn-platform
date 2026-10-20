---
phase: 08-product-staging
plan: 02A
type: execute
wave: 1
depends_on: [08-01C]
autonomous: true
requirements: []
files_modified: [host/secrets.py, tests/platform/test_secrets.py, tests/platform/run.sh, runbooks/runtime-secrets.md]
---

<objective>Implement the secret delivery prerequisite requested by the orchestrator. Runtime metadata fixes aliases, numeric versions and consumer ownership; a separate transfer command prepares the approved existing-key-to-Secret-Manager operation. No live cloud operation is authorized by this slice.</objective>

<context>
@AGENTS.md
@contracts/v1/README.md
@contracts/v1/deployment.schema.json
@host/contract.py
@.planning/phases/08-product-staging/08-02-PLAN.md
</context>

<tasks>
<task type="auto">
<name>Scoped secret delivery and single-attempt provider transfer</name>
<files>host/secrets.py, tests/platform/test_secrets.py, tests/platform/run.sh, runbooks/runtime-secrets.md</files>
<action>Use existing Python and audited gcloud without installing dependencies. Validate runtime aliases and numeric versions. Deliver private per-consumer files through tmpfs, fixed UID ownership, strict paths and atomic publication. Reject links/unexpected content. Clean only known files. Implement separate explicit-target transfer from existing private key file using stdin, preflight identity and a durable metadata-only receipt that blocks retry after uncertain mutation. Test real command and filesystem with synthetic cloud stub; preserve shared work.</action>
<verify><automated>tests/platform/run.sh secrets</automated></verify>
<done>CLI and negative boundary checks pass locally with accurately recorded Linux/cloud limitations. Parent owns integrated rerun and state reconciliation; full 08-02 remains open.</done>
</task>
</tasks>

<threat_model>
T-08-04 mitigations in host/secrets.py: consumer isolation, numeric pins, restrictive file access, no secret logging, fail-closed paths. Transfer additionally holds an uncertain cloud write behind a durable single-attempt receipt.
</threat_model>

<output>08-02A-CHECKPOINT.md and 08-02A-SUMMARY.md. Do not mark broader requirements complete.</output>
