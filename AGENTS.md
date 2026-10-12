# hyprn-platform — agent instructions

This repository is HYPRN's cloud platform: the Google Cloud organization and its guardrails, Terraform roots, environments and identities, the deployment contract, the host reconciler, the agent fleet and its runbooks. Products live in their own repositories; HYPRN MVP is `hyprn-mvp`. Decisions spanning product and platform are ADRs in `hyprn-mvp/docs/adr/`, linked from `docs/adr/README.md`.

This is the only agent instruction file in the repository.

## Read first

| Need | Read |
|---|---|
| What is here and where | `README.md`, then the folder's README |
| Platform design, MUST requirements, open questions | `docs/specs/cloud-platform.md` |
| Decisions | `docs/adr/` (MADR; an accepted record is superseded by a new one, never edited) |
| Current work, requirements, state, inventory, operational notes | the hidden planning directory at the repository root: `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `milestones/` |
| Operating a component, and what was done | `runbooks/` |

## Boundaries

- Product code never enters this repository; platform infrastructure never enters a product repository.
- `hyprn-agents` is engineering tooling, not an environment: no product workload, data or deployment authority, and no access to staging or prod.
- The specification authorizes nothing by itself: no cloud account, deployment, publication or pilot opening.

## Authority

- Read-only inspection needs no approval.
- Every step that creates, changes or deletes cloud resources, IAM, organization policy, billing, or GitHub, Slack or Claude organization settings runs only after the platform owner's explicit go for that exact step or reviewed plan. Removals get their own go.
- Terraform: plan, review, apply exactly the reviewed plan. Staging and prod have separate state and authority.
- Record what was done in the relevant runbook.

## Secrets and identities

- Never commit credentials, Terraform state or plan files, tfvars with secret values, service-account keys or session data. Secret values live in the company password manager (master copy) and Secret Manager (runtime copy).
- Never print a secret value; check tokens by shape (prefix, length) only.
- Run `gcloud`, Terraform and `gh` with the configurations dedicated to HYPRN (`CLOUDSDK_CONFIG`, `GOOGLE_APPLICATION_CREDENTIALS`, `GH_CONFIG_DIR`); without them a command runs as the wrong identity.
- Repository content names roles, groups and agent identities, never people or their personal accounts.

## Writing

Documentation states what things are and what they do. Boundaries, process, history and gotchas belong in this file and the planning directory, not in READMEs.
