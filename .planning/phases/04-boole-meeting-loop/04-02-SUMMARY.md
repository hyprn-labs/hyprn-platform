# 04-02 Summary: Meeting-loop run path (extract, propose, park, approved write)

**Status:** done
**Date:** 2026-10-13

## What was built

- `agents/loops/meeting/prompts.md` — extraction rubric: fixed JSON
  contract (decisions/actions with text+owner+due/open_questions/patch),
  quote-the-source rule, instruction-injection guard (page text is data
  per ADR-0006 rule 3), malformed degrade to propose-nothing.
- `agents/loops/meeting/skills/notion-slack-shapes.md` — Notion REST
  shapes (data-source query, page+blocks read, PATCH by schema id,
  Notion-Version 2026-03-11) and Slack summary + approval-question shape
  scoped with run id + page id.
- `agents/host/files/hyprn-meeting-workflow` — pinned bash run path:
  fetch, extract, draft patch (never applied yet), Slack summary at A2,
  `Dispatcher.park` + immediate exit, PATCH only when `Dispatcher.resume`
  returns true for the loop owner, then `Dispatcher.record_cost`.
  Secrets only from the reviewed loop file; key material unset after use.
- `tests/agents/checks/meeting.sh` — 19 assertions, all static or
  fake-backed, auto-discovered by `tests/agents/run.sh`.

## Verifies

- `bash tests/agents/checks/meeting.sh` — 19/19 PASS.
- `python3 -m unittest discover -s controller` — 19/19 OK.
- `bash -n agents/host/files/hyprn-meeting-workflow` — syntax OK.
- Live-shape smoke on fakes (single shell): new run parks as
  awaiting_approval with 1 decision/1 action/1 question extracted;
  stranger `yes` leaves it parked; owner `yes` applies patch
  (applied.json) and records cost 0.05.
- Grep: no secret values, no upstream meeting-tool integration strings,
  no SDK imports in new files.

## Deviations

- Extractor matches DECISION:/ACTION:/QUESTION: markers anywhere in a
  line (fixtures carry them mid-line), quoting the full source line.
- Tokens reach inline-python helpers via environment (never argv), unset
  after use; `REPO_ROOT` derived from the script path so the workflow
  runs from any cwd.
- The "no upstream-tool" grep pattern is built via `printf` so the check
  file never matches its own line under the plan's grep gate.

## Blocked

None — no owner-go checkpoints in this plan. Live trial (10 meetings in
two weeks within $30) stays behind the 04-03 owner-go checkpoint.
