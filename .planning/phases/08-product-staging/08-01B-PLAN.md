---
phase: 08-product-staging
plan: "01B"
type: execute
autonomous: true
requirements: [PST-01]
files_modified: [host/contract.py, contracts/v1/deployment.schema.json, contracts/v1/fixtures.json, contracts/v1/README.md, tests/platform/test_contract.py]
---
<objective>Expose the two bounded background database roles and a separate trusted dispatcher template in the offline deployment preview.</objective>
<tasks>
<task type="auto" tdd="true">
<name>Separate application dispatcher credentials and bridge authority</name>
<files>host/contract.py, contracts/v1/deployment.schema.json, contracts/v1/fixtures.json, contracts/v1/README.md, tests/platform/test_contract.py</files>
<behavior>CLI previews are deterministic and exactly pinned. App receives assistant background role; dispatcher receives only request, dispatcher discovery and modeling credentials. Native host and worker receive none. Unknown roles, aliases and service authority fail closed.</behavior>
<action>Declare the dispatcher as an application-image template with fixed host-owned stdio bridge, scoped artifact access, TLS and restricted database/modeling egress. Coordinate launch shape with the parent. Preserve all source/artifact pins and refresh synthetic fixture hashes. Lifecycle implementation and boot acceptance remain product 06-05.</action>
<verify><automated>tests/platform/run.sh contracts</automated></verify>
<done>Committed contract tests pass; checkpoint records exact hashes and consumer matrix, with no cloud mutation or boot claim.</done>
</task>
</tasks>
<threat_model>Mitigate credential bleed and arbitrary process/network authority through fixed consumers, closed input roles and effective-render validation. No provider credential/egress, Docker socket or public port for dispatcher.</threat_model>
<output>08-01B-CHECKPOINT.md and 08-01B-SUMMARY.md. Parent owns global STATE/ROADMAP/REQUIREMENTS integration; their unrelated edits are preserved.</output>
