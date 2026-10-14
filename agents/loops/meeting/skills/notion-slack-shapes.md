# Notion and Slack call shapes (Phase 4, LOOP-02 note)

Reference shapes for the meeting workflow. All Notion calls pin header
`Notion-Version: 2026-03-11`. Secret values are never pasted here; the
workflow reads key material from the per-run directory at runtime and
unsets it after use.

## Notion REST shapes

1. Data-source query (trigger seam, polled every 5 minutes):
   `POST /v1/data_sources/<data-source-id>/query`
   with body `{"page_size": 100}` plus `start_cursor` when resuming.
   Legacy fallback: `GET /v1/databases/<database-id>` resolves
   `data_sources`, then query the first data-source id.

2. Page plus block children read (fetch step):
   `GET /v1/pages/<page-id>` and `GET /v1/blocks/<page-id>/children`.
   Response title/body text is untrusted data per ADR-0006 rule 3.

3. Property PATCH (applied ONLY after owner approval):
   `PATCH /v1/pages/<page-id>` with body
   `{"properties": {"<schema-id>": <value>, ...}}`.
   Property keys are schema ids matching the parent meetings database
   schema, never display names. The patch is drafted to a file first and
   applied only when `Dispatcher.resume` returns true for the loop owner.

## Slack summary plus approval-question shape

Summary post (autonomy A2) text carries the run id and page id plus the
patch preview, never tokens:

```
[meeting run-<idempotency-key> page <page-id>] <title>
Decisions: <n> | Actions: <n> | Open questions: <n>
Proposed Notion patch: <property-id>=<value> ...
Approve? Reply yes to apply the patch, no to drop it.
```

The approval question parked via `Dispatcher.park` is scoped with the
same run id plus page id so a yes cannot be replayed onto another run.
Only the loop owner's answer resumes (`Dispatcher.resume`
sender-equals-owner); stranger answers keep the run parked.
