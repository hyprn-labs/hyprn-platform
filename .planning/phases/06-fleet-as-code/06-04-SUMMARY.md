# 06-04 Summary: SC1 consumer migration + legacy deletion

**Status:** done — verifies: byte-parity diffs empty, fleet.sh 34 PASS exit 0,
egress/github/herdr/host-checks outputs identical to baseline, bash -n clean
on all touched scripts, no live applies / SSH / vendor calls / secrets.

## What changed

fleet.yaml is now the only committed agent declaration. Every remaining live
consumer of the committed `agents/host/agents.txt` and `agents/wake/wake.json`
renders the registry at provision/check time instead, and both legacy files
are deleted from git (`git rm`).

- **agents/fleet-render** — default write path emits only the committed
  `infra/agents/fleet.auto.tfvars.json`; `--agents-out/--wake-out/--tfvars-out`
  write byte-identical content to explicit paths, and any `--*-out` flag
  switches to explicit mode (only requested outputs written, repo untouched).
  `--check` asserts the committed tfvars.json regen-clean. Renderer row/JSON
  functions unchanged. Falls back to the shipped tree (no git needed) when
  `--fleet` is given outside a checkout, so it runs on the hosts.
- **agents/host/provision.sh** — apt line gains Debian `python3-yaml`
  (existing trusted renderer dependency); tail is validate-then-render-then-parse
  with the `add_agent` loop body untouched (column order preserved).
- **agents/host/apply.sh**, **agents/wake/apply.sh** — tarballs now ship
  `agents/fleet.yaml`, `agents/fleet-render`, `agents/fleet-validate`.
- **agents/wake/provision.sh** — validates fail-closed before installing
  anything, renders `--wake-out` directly to `/etc/hyprn-agents/wake.json`
  (the path wake.py reads). **wake.py unmodified.**
- **tests/agents/checks/egress.sh, github.sh, herdr.sh,
  tests/agents/host-checks.sh** — `AGENTS` is now a render-to-temp ephemeral
  file (`|| exit 1` fail-closed); all parse loop bodies untouched.
- **tests/agents/checks/fleet.sh** — post-deletion assertions: git-ls-files
  deletion proofs, no-live-readers scan over `agents/` + `tests/agents/checks`
  (comments allowed; fleet.sh proof lines and the renderer definition excluded),
  render-parity (`ada 20001` / `codd 20002` rows, wake agents exactly `[ada]`);
  all existing validator / wake-filter / no-secret-flag / negative-probe /
  dry-run assertions kept. 30 → 34 PASS.
- **agents/host/agents.txt, agents/wake/wake.json** — deleted via `git rm`.

## Deviations (auto-fixed, Rules 2/3)

1. **[Rule 2] `agents/host/files/bin/ada-digest` migrated** — the no-reader gate
   caught this seventh consumer (plan listed six): it read the committed
   agents.txt. Same render-to-temp pattern, loop body untouched, temp removed
   inside `build_digest` (no trap conflict with the post-mode `trap unhold EXIT`).
   Proof: `--dry-run` output byte-identical before/after
   (`diff /tmp/digest-old.txt /tmp/digest-new.txt` empty).
2. **[Rule 3] `tests/agents/host-checks.sh` migrated** — reads agents.txt and ships
   in the apply tarball; left as-is it would iterate zero agents post-apply
   (silent coverage loss). Same render-to-temp pattern using the shipped
   `fleet.yaml` (`--fleet` flag, works without git); output byte-identical to
   baseline. Ordering safe: runs after provision.sh installs python3-yaml.
3. **[Rule 2] `agents/fleet` dry-run diff retargeted** — diffed provisional renders
   against the now-deleted committed files (would print "No such file" noise and
   trip the no-reader gate). Now renders the current registry to temp and diffs
   provisional-vs-current (cleaner: shows exactly the provisional-entry delta).
   All fleet.sh dry-run assertions still pass; tree still untouched.
4. **[Rule 2, comment-only] `agents/fleet.yaml` header updated** — old header said
   all three outputs "are committed" and consumers "keep reading the generated
   files until migrated"; now states tfvars-only committed, txt/json ephemeral.

## Verification evidence

- `diff <(git show HEAD:agents/host/agents.txt) <(render --agents-out)` — empty
- `diff <(git show HEAD:agents/wake/wake.json) <(render --wake-out)` — empty
  (incl. `--fleet <shipped-tree>` simulation path)
- `git ls-files` shows neither legacy file tracked
- `bash -n` passes on all 10 touched shell scripts
- `tests/agents/checks/fleet.sh` — 34 PASS, exit 0, no FAIL
- `tests/agents/run.sh` — per-script PASS/FAIL profile **identical** to the
  pre-change baseline (remaining FAILs are host-gated: host-checks, accounts,
  codd, detect, egress, github, session — all fail off-host by design)
- egress/github/herdr/host-checks stdout **byte-identical** to baseline
  (same agent rows iterated, same host-gated skips/fails)
- Default `fleet-render` (no args) does not resurrect the deleted files
- `wake.py` byte-untouched (`git status` clean for it)
- No `gcloud`/SSH/vendor/secret commands run; suite side-effect records under
  `runbooks/agents/checks-*.md` left unstaged

## Threat disposition (plan T-6-07 / T-6-08 / T-6-SC)

- T-6-07: both provision scripts run `fleet-validate` first and abort on failure
  (fail-closed ordering: validate → render → parse/install); renderer is stdlib
  + Debian python3-yaml only; parse/digest loop bodies byte-untouched.
- T-6-08: wake render is slack-filtered in the renderer; fleet.sh locks wake
  agents to exactly `[ada]` plus the `--wake` validator gate on the render.
- T-6-SC: no package-manager installs; `python3-yaml` is apt-only.
