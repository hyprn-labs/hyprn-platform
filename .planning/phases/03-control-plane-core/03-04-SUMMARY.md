# Phase 3 Plan 04: Reviewed-not-applied cloud shape — Summary

**Status:** done
**Date:** 2026-10-13

## What was built (reviewed only — zero applies, keys, secret writes)

- `infra/agents/gateway.tf` — Cloud Run LiteLLM (internal-only ingress),
  managed Postgres spend-state, per-loop key/budget locals, reference-only
  secret wiring, no public invoker binding.
- `infra/agents/controller.tf` — least-privilege controller identity
  (log/metrics writer + Cloud SQL client, custom queue-reader role),
  Cloud Scheduler poll transport (SQLite loop interim).
- `agents/gateway/litellm-config.yaml` — Fireworks default + Claude +
  OpenAI bindings (binding-only switch), env-reference secrets.
- `infra/agents/boole.tf` — Boole secret containers (Slack pair, gateway
  key, GitHub App key), host-only named-account accessors, COST-01
  budget placeholder (commented, owner-set at go).
- `runbooks/agents/control-plane-go.md` — owner-go checklist: keys +
  budget + vendor, exact-plan apply, live test-loop run; each with a
  verification line and dated-record slot.
- `tests/agents/checks/gateway.sh` — 20 static assertions + terraform
  SKIP note, auto-discovered by run.sh.

## Verifies

- gateway config parses → gateway-config-ok; secret_key_ref count 2
- `tests/agents/checks/gateway.sh` → 20 PASS + 1 SKIP, exit 0
- Full quick verify: unittest 12 OK, loops/controller/runner checks green

## Blocked

- `terraform validate/plan/apply` — terraform binary absent here by
  design; runs at the owner-go apply step (03-05 checkpoint 2).
- Provider keys, budget figure, Boole Slack app — owner-go (03-05
  checkpoint 1). LiteLLM image digest pinned at apply review
  (version tag now, noted in gateway.tf + go-runbook).

## Deviations

- Auto-fix: no-public-invoker grep matched its own explanatory comment;
  filtered to non-comment lines.
- Image uses a version tag with a digest-pinning note instead of a
  fabricated digest — a placeholder digest would fail apply review.
