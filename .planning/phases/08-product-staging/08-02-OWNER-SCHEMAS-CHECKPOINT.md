# Stopped owner compatibility checkpoint — 2026-10-21

Commit `68d04d3cede0de81793820b00269329991a335b5` changes only
`host/reconcile.py` and `tests/platform/test_reconcile.py`. Product counterpart:
`63af9f041a321c175387eea1ef79643b631c9e45`.

The prior unconditional replacement refusal is superseded by comparing exact
real owner observations accepted by both pinned products. Integer declarations
must remain unchanged; they are never fabricated from owner migration versions.
Compatibility follows active admission closure/drain/stop, precedes backup and
migration, and refuses missing/foreign/changed schemas with stores untouched.
Incoming inspection uses an explicit protected active binding. Qualify/start
observations must match; the platform does not call stopped-only inspection on
running writers. No API creates cloud resources or opens admission here.

`python3 -B -m unittest discover -s tests/platform -p test_reconcile.py -v`:
39 then 41 passed after the respective implementation/sequencing changes.
`tests/platform/run.sh reconcile` on committed `68d04d3`: **41 passed, 0 failures,
0 errors, 0 skipped, 0.753 seconds, exit 0**. Fault tests explicitly substitute
external product/host boundaries; they are not a whole-host lifecycle proof.

Full product evidence, every intermediate failure, artifact identities and scoped
cleanup are in the sibling product checkpoint
`.planning/phases/06-hosted-staging/06-05-OWNER-SCHEMAS-CHECKPOINT.md`.
It records final real owner probes 9/9 and PostgreSQL lifecycle 21/21. Parent
independently repeated committed acceptance: reconcile 41/41 in 1.321 seconds
(`/private/tmp/hyprn-owner-reconcile-parent.log`), schemas 9/9 in 22.848 seconds
(`/private/tmp/hyprn-owner-schemas-parent.log`), lifecycle 21/21 in 17.421 seconds
(`/private/tmp/hyprn-owner-lifecycle-parent.log`). Parent owns bootstrap integration, Linux amd64 bundled
source, real second activation, recovery, running public behavior and STATE.

Coherent product inspect/check requires stopped writers; do not use it as live
readiness. Nonempty SQLite WAL/journal bytes and legacy unbound modeling markers
remain explicit recovery cases. No hidden checkpointing or adoption occurs.
No Google/provider call, IAM change, VM start or backup creation was performed
by this executor. Platform 08-02 remains incomplete.

## Self-Check: PASSED

Both implementation commits exist; owned test/source files exist and committed
platform tests pass. Unrelated edits and the index were preserved.
