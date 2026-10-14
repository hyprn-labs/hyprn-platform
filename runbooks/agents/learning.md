# Runbook: meeting-loop learning (evals, feedback, improvement, promotion)

Phase 5 learning half of the meeting loop. Seeds are labeled seeds
everywhere (filenames, JSONL `origin`, runner reports, PR bodies) —
seed output is never presented as a real run.

## Seed-label rule

- Eval cases carry REQUIRED `origin: seed|real`; the in-phase set is
  all seeds (`agents/loops/meeting-eval.jsonl`).
- Runner reports print `seed:` and `real:` tallies on separate lines.
- Canned fixtures live under `agents/loops/testdata/eval-fixtures/`
  with a `SEED-README.md` header; no real meeting text there.

## Feedback to real cases

Owner feedback (reactions, replies, approval answers) is stored with
its run via `Dispatcher.record_feedback` (closed kinds, dedupe key,
unknown runs refused; approval answers only through the owner-gated
`resume` path). As the trial produces runs, feedback rows become
`origin: real` eval cases that replace seeds; the runner accepts both.
Live channel-server wiring waits for the Boole bot (owner vendor step).

## Improvement gate

Improvement runs propose prompt/skill diffs only (never loop YAML or
autonomy fields) as draft PRs on `agent/boole/<slug>`, authored by
`boole-agent-hyprn[bot]`, body carrying `## What changed`,
`## How verified`, and the seed-labeled `## Eval result` section from
`agents/eval/run.py --post`. The eval gate verdict is recorded on the
PR: PASS reaches the owner review queue, FAIL stays in draft and is
never shown. Only the owner merges.

## Promotion template

`agents/eval/promotion.py` reads the rule (`min_pass_rate`,
`last_runs`, `max_corrections_per_run`) from
`agents/loops/meeting.yaml` at check time, counts only real-origin
runs, and prints `INSUFFICIENT DATA (seeds excluded)` below ten real
runs. A PASS verdict is a template: promotion ships as a reviewed
change merged by the owner, never as a scripted autonomy flip.

## Boole GitHub App declaration (declared, not created)

- App: `boole-agent-hyprn`. Install scope: `hyprn-platform` ONLY
  (never all repositories). Repository permissions: Contents and
  Pull requests **read and write** (Metadata read is automatic).
  Webhook **inactive**.
- Tokens: one-hour installation tokens through the existing broker
  flow, reading the `boole-agent-github-app-key` secret container
  (declared in `infra/agents/boole.tf`). No new signing code.
- Creation and key loading are owner checklist items (no App creation,
  no key material in-phase):
  1. Organization Settings → Developer settings → GitHub Apps → New
     GitHub App with the settings above; note the App ID.
  2. Install the App on `hyprn-platform` only; record the
     installation and bot IDs.
  3. Generate a private key; store the `.pem` in the company password
     manager; load it (owner only):
     `gcloud secrets versions add boole-agent-github-app-key --project=hyprn-agents --data-file=<key.pem>`
     then delete the downloaded `.pem` and run `agents/host/apply.sh`.

## Record

| Date | Step | Result |
|---|---|---|
| 2026-10-14 | Phase 5 learning slice | Feedback store + writer with unit tests, 20-case seed eval set with canned fixtures, offline runner with live/post superset, fixture improvement-PR gate proof, promotion-check template, Boole App declared-not-created. Owner merges; trial feeds real runs. |
