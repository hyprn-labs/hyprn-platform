# Finding: FLT-05 Claude setup-token sign-in probe (channel behavior)

**Date:** 2026-10-14
**Probe:** FLT-05 — does `claude setup-token` yield a `CLAUDE_CODE_OAUTH_TOKEN`
that a test agent session can use such that the channel server connects and
answers (Slack steering working under token auth)?
**Time-box:** ~2h, static evidence only (no live vendor access from this environment).

## Verdict: MANUAL STEP

Standing verdict: manual step. Interactive `/login` (runbooks/agents/host.md B4
precedent: owner signs the agent in with an email code) stays the standing
sign-in step until a live token-authed session is proven to join channels.

## Evidence

- Documented semantics: `claude setup-token` prints a long-lived token without
  saving it; `CLAUDE_CODE_OAUTH_TOKEN` takes precedence over keychain
  credentials — the token path exists for CLI/SDK auth.
- Known risk: interactive onboarding (theme/auth picker) can still block a
  headless start; the community `hasCompletedOnboarding` workaround is
  [ASSUMED] (issue reports, not official docs) and unverified here.
- Whether the channel server connects and answers under token auth (the FLT-05
  question) needs a live session on a test agent: load the token into Secret
  Manager by shape, start the session, verify the channel answers. This
  environment has no Claude vendor access, so the probe is recorded as
  blocked, not as a negative result.
- A "doesn't work with channels" result would be complete: it locks
  interactive `/login` as the standing step.

## Standing procedure

1. Owner signs the agent in with `/login` (email code, agent's browser
   profile); credentials file owned by the agent, mode 600.
2. Re-run `agents/host/apply.sh`: host checks pass and the session starts with
   `--channels`.
3. Token values, if ever used, travel in owner hands straight to Secret
   Manager paths; scripts take paths/handles only.

## Secrets

None handled: no tokens created, printed, or stored.
