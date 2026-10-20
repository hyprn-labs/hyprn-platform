---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-10-20T19:25:41.358Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 08 | stub | environments/staging/access.json |  | Access review template needs actual account, tunnel, IdP and allowlist inputs before08-04/05 settings operation. | open |  | 2026-10-20T19:25:41.358Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "08",
    "file": "environments/staging/access.json",
    "line": null,
    "description": "Access review template needs actual account, tunnel, IdP and allowlist inputs before08-04/05 settings operation.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-10-20T19:25:41.358Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
