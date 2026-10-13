# Control plane go-checklist (Phase 3, owner-go only)

Automation is forbidden to perform any step below. Each step runs only
after the platform owner's explicit go for that exact step. Record each
completion with a dated entry in the slots provided.

Depends on accepted ADR-0006. Secret values live in the password manager
(master) and Secret Manager (runtime) — never pasted into chat, never
committed. The agent checks shapes only.

## Step 1 — Provider keys, revised budget, Boole vendor objects

- [ ] Create the Fireworks key (owner-created account → API keys).
      Verify: secret `FIREWORKS_AI_API_KEY` exists with an active version (metadata only).
- [ ] Link the Anthropic Console organization to the Team plan (API
      credits) and create its key.
      Verify: secret `ANTHROPIC_API_KEY` exists with an active version (metadata only).
- [ ] Create the OpenAI key.
      Verify: secret `OPENAI_API_KEY` exists with an active version (metadata only).
- [ ] Store the LiteLLM master key (`sk-` prefix shape) and the gateway
      database URL in Secret Manager from the password manager.
      Verify: secrets `gateway-master-key`, `gateway-db-url` exist (metadata only).
- [ ] Create and install Boole's Slack app (`Boole (AI agent)`) from the
      reviewed manifest; store the app/bot token pair in Secret Manager.
      Verify: secrets `boole-agent-slack-app-token`, `boole-agent-slack-bot-token`
      exist; app install visible to the workspace admin.
- [ ] Set the revised hyprn-agents monthly budget (COST-01).
      Verify: budget figure recorded here.

_Dated record (step 1):_ <!-- YYYY-MM-DD: keys-and-vendor-done, budget figure -->

## Step 2 — Exact-plan Terraform apply, nothing more

- [ ] Run validate plus plan on `infra/agents/gateway.tf`,
      `controller.tf`, `boole.tf`; review against the 03-04 assertions
      (internal ingress, database wiring, least-privilege identities,
      named-account accessors, no public invoker).
      Verify: `tests/agents/checks/gateway.sh` green against the applied shape.
- [ ] Apply exactly that plan. Removals or surprises get their own go.
      Verify: gateway endpoint reachable read-only from inside the VPC boundary.

_Dated record (step 2):_ <!-- YYYY-MM-DD: apply-done, applied plan summary -->

## Step 3 — First live test-loop run

- [ ] Approve running the meeting-test loop once end to end — Fireworks
      binding, fresh container under the boole user, allowlist enforced,
      cost logged.
      Verify: run log shows the completed run with its cost_usd entry;
      container reached only allowlisted destinations (refused + logged
      otherwise); `tests/agents/run.sh` fully green with the dated record kept.
- [ ] Approve the binding-only switch proof to Claude.
      Verify: same loop on the Claude binding differs in binding value only.

_Dated record (step 3):_ <!-- YYYY-MM-DD: live-run-done -->
