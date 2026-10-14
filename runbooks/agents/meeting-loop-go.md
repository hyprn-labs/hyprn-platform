# Meeting-loop go-checklist (Phase 4, owner-go only)

Automation is forbidden to perform any step below. Each step runs only
after the platform owner's explicit go for that exact step. Record each
completion with a dated entry in the slots provided.

Depends on accepted ADR-0006 and the Phase 4 fakes-green run path
(poll seam plus A1 workflow proven in `tests/agents/checks/meeting.sh`).
Secret values live in the password manager (master) and Secret Manager
(runtime) — never pasted into chat, never committed. The agent checks
shapes only.

## Step 1 — Settle LOOP-01 (the upstream leg choice)

- [ ] Record the chosen audio-notes-to-Notion path (which integration
      populates the meetings database).
      Verify: the chosen path is written in the dated record below; no
      scraper or unofficial API is in scope.
- [ ] Confirm the meetings database receiving pages is the ORIGINAL
      database, not a linked view.
      Verify: the database id matches the one the poller is configured
      with (`--source`).

_Dated record (step 1):_ <!-- YYYY-MM-DD: loop-01-settled, chosen path -->

## Step 2 — Workspace user plus Notion integration share

- [ ] Create the Workspace user for Boole (hand-created; automation
      deferred to FLT-02).
      Verify: user exists per the admin console; name recorded below
      (role identity, never a personal account).
- [ ] Share the original meetings database with Boole's Notion
      integration with Insert Content capability (read plus write for
      the approved-PATCH step, nothing wider).
      Verify: share visible on the original database; capability is
      Insert Content, not full workspace access.

_Dated record (step 2):_ <!-- YYYY-MM-DD: user-and-share-done -->

## Step 3 — Token into Secret Manager (shape check only)

- [ ] Store Boole's Notion token in Secret Manager from the password
      manager under `boole-agent-notion-token` (declared in
      `infra/agents/boole-notion.tf`, reviewed-not-applied until step 4).
      Verify: secret `boole-agent-notion-token` exists with an active
      version (metadata only — the agent checks shapes only).

_Dated record (step 3):_ <!-- YYYY-MM-DD: token-stored -->

## Step 4 — Exact-plan Terraform apply, nothing more

- [ ] Run validate plus plan on `infra/agents/boole-notion.tf`; review
      against the meeting.sh assertions (declared-not-created
      containers, host-only secretAccessor, no values, no vendor-side
      resources).
      Verify: `tests/agents/checks/meeting.sh` green against the plan.
- [ ] Apply exactly that plan. Removals or surprises get their own go.
      Verify: secret container `boole-agent-notion-token` exists
      (metadata only).

_Dated record (step 4):_ <!-- YYYY-MM-DD: apply-done -->

## Step 5 — Approve the 10-meeting live trial within budget

- [ ] Approve running ten meetings over two weeks within 30 USD through
      the metered path (per-run cost visible via `Dispatcher.record_cost`).
      Verify: run logs show ten completed runs with cost_usd entries
      totaling under 30 USD; over-budget runs refused before compute;
      `tests/agents/run.sh` fully green with the dated record kept.
- [ ] Approve Notion-write approvals in Slack via Boole's bot
      (owner yes applies the PATCH; stranger answers keep runs parked).
      Verify: at least one approved PATCH and one stranger-ignored
      park in the trial logs.

_Dated record (step 5):_ <!-- YYYY-MM-DD: trial-done, total cost -->
