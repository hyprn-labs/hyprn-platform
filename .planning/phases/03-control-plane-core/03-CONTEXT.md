# Phase 3: Control plane core - Context

**Gathered:** 2026-10-13
**Status:** Ready for planning
**Mode:** Auto-discussed (user directed autonomous run without stops; all answers at agent discretion)

<domain>
## Phase Boundary

Autonomous runs get a safe, metered path end to end: gateway, controller (queue + dispatcher + run state), loop registry, credential broker, run runner, approvals that wait, budgets, kill switch — plus Boole's runtime identities. Provider keys and budget (Fireworks, Anthropic, OpenAI, Boole Slack app, COST-01) arrive later, so everything cloud/key-gated is delivered as reviewed code and deferred applies, never as live infrastructure. Depends on Phases 1–2 (live proofs deferred-human).

</domain>

<decisions>
## Implementation Decisions

### Code-without-keys shape (auto-accepted at agent discretion)

- Deliver the loop registry schema (`agents/loops/<name>.yaml`: trigger, steps, agent steps, tools, autonomy per action, budget, eval set, promotion rule, owner), dispatcher/queue/run-state logic, credential-broker interface, and run runner as code with unit-testable seams (fake queue, fake gateway, fake broker).
- A test loop definition exists and passes static validation; its live run waits for keys and is an explicit owner-go checkpoint, not attempted here.

### Cloud resources reviewed-not-applied (auto-accepted at agent discretion)

- Gateway (LiteLLM on Cloud Run, internal ingress, Cloud SQL for keys/budgets/spend) and controller wiring ship as reviewed Terraform + config, apply deferred to owner go when keys arrive. Kill switch and budget enforcement live in code paths testable with fakes.
- No `terraform apply`, no key creation, no Secret Manager writes in this phase's execution.

### Boole identities declared-not-created (auto-accepted at agent discretion)

- Declare Boole's runtime identities (Linux user, Terraform blocks, Slack app manifest, gateway key placeholder) without creating vendor-side objects. Vendor steps are owner checklists in the runbook.
- ADR-0006 acceptance stays a Phase 3 dependency — plans must flag any build that assumes its acceptance.

### Run isolation from the first run (auto-accepted at agent discretion)

- EGR-03: loop definitions carry the destination allowlist; the runner enforces it from the first run. Prove the enforcement shape with a local container dry-run where possible (rootless, no creds); otherwise static assertion on the runner code + schema validation.

### Agent's Discretion

All Phase 3 answers taken at agent discretion under the autonomous-run direction. Planner must keep every key/cloud-gated step an explicit owner-go checkpoint.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `agents/wake/wake.py`: polling + start-host pattern the controller's scheduler/poller extends.
- `infra/agents/`: network, NAT, IAM, secrets patterns for gateway/controller Terraform.
- `agents/host/files/hyprn-agent-github-token@.service`: short-lived token minting pattern the credential broker follows.
- `tests/agents/run.sh` + `checks/`: every new check joins the one-command run (ACC-08 continuity).

### Established Patterns

- One-command proof; dated records in `runbooks/agents/`; owner-go checklists never automated.
- Least privilege per agent/loop; trigger payloads untrusted (ADR-0006 rule 3).

### Integration Points

- `agents/loops/` (greenfield): registry the dispatcher reads.
- Gateway between host/controller and providers (keys later).
- Run state database on the gateway's Cloud SQL (schema now, instance with apply).

</code>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Standing direction: owner go per infra/vendor step; keys and budget arrive later.

</specifics>

<deferred>
## Deferred Ideas

- Live test-loop run on Fireworks (needs keys + owner go).
- Boole vendor objects (Slack app install, Workspace user is Phase 4).
- Webhook receiver (WEB-01, needs own ADR).

</deferred>

---

*Phase: 3-Control plane core*
*Context gathered: 2026-10-13*
