---
phase: 08-product-staging
plan: "01C"
type: execute
autonomous: true
requirements: [PST-01]
files_modified: [host/contract.py, contracts/v1/deployment.schema.json, contracts/v1/fixtures.json, contracts/v1/README.md, tests/platform/test_contract.py]
---
<objective>Pin the reviewed Claude Managed Agent resources and explicit shared spending policy in the offline deployment contract and application environment.</objective>
<tasks>
<task type="auto" tdd="true">
<name>Bind release definitions, reviewed resources and carried shared allowance</name>
<files>host/contract.py, contracts/v1/deployment.schema.json, contracts/v1/fixtures.json, contracts/v1/README.md, tests/platform/test_contract.py</files>
<behavior>Real CLI previews deterministically emit exact application settings, matching release content pins and a mandatory shared USD allowance with explicit prior spending. Missing, ambiguous and arbitrary provider/budget authority fails closed. Only the app receives the existing numeric-version assistant-provider secret as a file.</behavior>
<action>Use product managed setup outputs and Settings names. Require carry-forward/reconciliation policy with no per-study budget. Preserve exact schema/renderer/release pins. State provider readback, durable accounting and cloud startup obligations without implementing host lifecycle.</action>
<verify><automated>tests/platform/run.sh contracts</automated></verify>
<done>Committed contract tests pass and checkpoint reports pins, actual guarantees and remaining consumers. No cloud or provider mutation.</done>
</task>
</tasks>
<threat_model>Mitigate credential bleed, unpinned provider resources, arbitrary endpoint/tool authority and implicit budget reset through closed inputs, release equality checks, fixed file consumer and explicit accounting prerequisites. Stateless preview cannot enforce historical continuity.</threat_model>
<output>08-01C-CHECKPOINT.md and 08-01C-SUMMARY.md. Parent owns global STATE/ROADMAP/REQUIREMENTS integration.</output>
