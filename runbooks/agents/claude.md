# Runbook: Claude Code organization policy (POL-01)

The Claude Code admin console enforces the organization policy for Ada.
Per D-01 the deny rules below are the interim control on `main` until the
Team-plan ruleset is applied; per D-08 the console apply is an owner-hand
step requested here, never automated.

## Apply the reviewed policy (owner go)

1. Open the Claude Code admin console → Organization settings → Policy.
2. Paste the content of `agents/policy/managed-settings.json` at the
   reviewed file revision verbatim (no edits in the console).
3. Expected end-state: a console export diffed against the file shows no
   differences:
   ```bash
   diff <(console-export) agents/policy/managed-settings.json
   ```
4. Confirm routine worktree work (status, diff, log, builds, tests) runs
   without prompts — roadmap success criterion 2.

## POL-03 marketplace evidence (record all three)

1. Console shows the known-marketplace list matching the file's
   `strictKnownMarketplaces` pin (`hyprn-labs/hyprn-agents` only).
2. On the host, `claude doctor` / `/status` in Ada's session shows the
   managed source active.
3. Negative test: adding a non-listed marketplace in Ada's session is
   refused; the refusal is recorded in the dated check record.

## Record

| Date | File revision | Step | Result |
|---|---|---|---|
| 2026-10-13 | (pending owner apply) | Console apply + prompt-free routine work + marketplace evidence | Awaiting owner go — Team Owner to apply, confirm, and sign |
