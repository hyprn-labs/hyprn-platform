# 06-01 Summary: Fleet registry tracer

**Status:** done
**Plan:** 06-fleet-as-code / 01 (tracer, wave 1)

## What was built

- `agents/fleet.yaml`: single declaration of ada (uid 20001, claude, slack true,
  workspace group as transient pre-move state) and codd (uid 20002, opencode,
  slack false, workspace none, repos hyprn-platform + hyprn-mvp).
- `agents/fleet-render`: stdlib + PyYAML renderer emitting `agents/host/agents.txt`
  (load-bearing column order, GENERATED header), `agents/wake/wake.json`
  (slack:true filter, byte-identical), `infra/agents/fleet.auto.tfvars.json`
  (stable sorted agents + slack_agents). Supports `--fleet FILE` and `--check`.
- `agents/fleet-validate`: schema gate (REQUIRED keys, kind/harness/workspace
  enums, UID 20000-20999 + uniqueness, name regex + `agent-` prefix rejection,
  github app/id checks, secret-name assertion), plus `--wake` equality gate so a
  Slack-less agent can never be wake-listed.
- `tests/agents/checks/fleet.sh`: 15 assertions in the loops.sh harness shape,
  auto-discovered by `tests/agents/run.sh` (no harness change).

## Verifies

- `python3 agents/fleet-validate agents/fleet.yaml` → exit 0 (plus `--wake` → 0).
- `python3 agents/fleet-render --check` → exit 0; agents.txt rows byte-identical
  to committed rows; wake.json byte-identical.
- `bash tests/agents/checks/fleet.sh` → 15 PASS, exit 0; `fleet` listed in
  checks discovery.
- Negative probes each exit non-zero: bad harness, duplicate UID, `agent-` legacy
  name, Slack-less wake entry.

## Deviations

- JSON generated files (`wake.json`, `fleet.auto.tfvars.json`) carry no GENERATED
  header comment: `wake.py` uses strict `json.load` and Terraform consumes
  `.tfvars.json` strictly, so a comment would break consumers. Provenance lives in
  the agents.txt header plus the regen-clean gate. [Rule 2 - correctness]

## Blocked

None.
