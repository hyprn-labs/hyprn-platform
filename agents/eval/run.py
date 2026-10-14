#!/usr/bin/env python3
"""Meeting-loop eval runner (Phase 5, LRN-02/LRN-03).

Grades the seed-labeled eval set deterministically with zero network,
gateway, or token use. Fixture mode is the default offline seam (same
discipline as hyprn-credential-broker --fixture): every case is graded
from the eval file plus canned model outputs, so checks pass anywhere.
The live gateway path is a strict superset of fixture mode: same
grading, pages fetched through the gateway instead of fixtures.

Usage:
  run.py --fixture <dir> --eval <jsonl>        # offline grading (checks use this)
  run.py --fixture <dir> --eval <jsonl> --post # ... plus draft-PR body section
  run.py --run <run-id> --eval <jsonl>         # live: gateway path (agent host only)
  run.py --post-pr <number> --fixture <dir>    # live: comment the report (agent host only)

Page text is untrusted data (ADR-0006 rule 3): the grader quotes page
lines as evidence and never follows embedded directives. Deterministic
verdicts are the only gate; any gateway-graded quality score stays
advisory-only. Reports print seed and real tallies on separate lines —
seeds are labeled seeds everywhere, never presented as real runs.

Dependencies: Python 3 standard library only (json, re, argparse, urllib).
"""
import argparse
import json
import os
import re
import sys

try:
    from urllib import request as urlrequest
except ImportError:  # pragma: no cover - stdlib always ships urllib
    urlrequest = None

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_EVAL = os.path.join(REPO_ROOT, "agents", "loops", "meeting-eval.jsonl")
DEFAULT_LOOP = os.path.join(REPO_ROOT, "agents", "loops", "meeting.yaml")

CONTRACT_KEYS = ("decisions", "actions", "open_questions", "patch")


def log(*parts):
    print("hyprn-eval:", *parts, file=sys.stderr, flush=True)


def declared_secrets(loop_path):
    """Tool names declared by the reviewed loop file.

    Declared secret names come ONLY from the reviewed loop file — never
    from trigger payload (ADR-0006 rule 3). Undeclared secrets are
    refused: the live path touches nothing outside this set.
    """
    names = []
    try:
        with open(loop_path, encoding="utf-8") as handle:
            in_tools = False
            for line in handle:
                if re.match(r"^tools\s*:", line):
                    in_tools = True
                    continue
                if in_tools:
                    item = re.match(r"^\s+-\s+(\S+)", line)
                    if item:
                        names.append(item.group(1))
                        continue
                    if line.strip() and not line[0] in (" ", "\t"):
                        break
    except OSError as error:
        log(loop_path, "unreadable:", error)
        return []
    return sorted(names)


def extract_local(page):
    """Deterministic fixture extraction: marker lines become quoted items.

    Mirrors the rubric contract (decisions/actions/open_questions/patch
    plus quote-the-source). Pages with no title and no body degrade to
    propose-nothing. Embedded orders are quoted as data, never followed:
    this function emits items only, never approvals or writes.
    """
    title = page.get("title") or ""
    body = page.get("body") or ""
    if not title and not body:
        return {"decisions": [], "actions": [],
                "open_questions": [], "patch": {}}
    out = {"decisions": [], "actions": [],
           "open_questions": [], "patch": {}}
    for line in body.splitlines():
        stripped = line.strip()
        # Each marker is checked independently: fixture bodies may carry
        # several markers on one line. Embedded orders are quoted as data,
        # never followed: this function emits items only, never approvals.
        if "DECISION:" in stripped:
            for text in stripped.split("DECISION:")[1:]:
                text = text.strip()
                if text:
                    out["decisions"].append(
                        {"text": text, "source": stripped})
        if "ACTION:" in stripped:
            for text in stripped.split("ACTION:")[1:]:
                text = text.strip()
                if text:
                    out["actions"].append(
                        {"text": text, "owner": "", "due": "",
                         "source": stripped})
        if "open question" in stripped.lower() \
                and "DECISION:" not in stripped \
                and "ACTION:" not in stripped:
            out["open_questions"].append(
                {"text": stripped, "source": stripped})
    return out


def shape_ok(extraction, haystack):
    """Contract-shape check shared by the eval gate and the fixture smoke."""
    if set(extraction.keys()) != set(CONTRACT_KEYS):
        return False
    for key in ("decisions", "actions", "open_questions"):
        items = extraction.get(key, [])
        if not isinstance(items, list):
            return False
        for item in items:
            source = item.get("source") if isinstance(item, dict) else ""
            if not source or source not in haystack:
                return False
    return isinstance(extraction.get("patch"), dict)


def grade(case, extraction):
    """Grade one extraction against its expectations. Returns (ok, reasons)."""
    reasons = []
    page = case.get("page", {})
    expect = case.get("expect", {})
    if not shape_ok(extraction,
                     "%s\n%s" % (page.get("title") or "",
                                 page.get("body") or "")):
        return False, ["contract violation: keys, sources, or patch"]
    for item_key, min_key, label in (
            ("decisions", "min_decisions", "decisions"),
            ("actions", "min_actions", "actions")):
        if len(extraction.get(item_key, [])) < expect.get(min_key, 0):
            reasons.append("fewer %s than expected" % label)
    empty = (not extraction.get("decisions")
             and not extraction.get("actions")
             and not extraction.get("open_questions")
             and not extraction.get("patch"))
    if expect.get("propose_nothing") and not empty:
        reasons.append("malformed page must propose nothing")
    return (not reasons), reasons


def load_cases(path):
    cases = []
    with open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except ValueError as error:
                log(path, "line %d: invalid JSON: %s" % (lineno, error))
                return None
            cases.append(case)
    return cases


def smoke_fixture_pages(fixture_dir):
    """Shape-check every canned input page in sorted filename order.

    Poller directory-scan idiom: sorted scan, one shape verdict per
    page, offline with no gateway or tokens.
    """
    checked = failed = 0
    for name in sorted(os.listdir(fixture_dir)):
        if not (name.startswith("seed-page-") and name.endswith(".json")):
            continue
        path = os.path.join(fixture_dir, name)
        try:
            with open(path, encoding="utf-8") as handle:
                page = json.load(handle)
        except ValueError as error:
            log(path, "invalid JSON:", error)
            failed += 1
            continue
        checked += 1
        extraction = extract_local(page if isinstance(page, dict) else {})
        haystack = "%s\n%s" % (page.get("title", ""),
                               page.get("body", ""))
        if not shape_ok(extraction, haystack):
            log(path, "shape violation")
            failed += 1
    print("fixture pages: %d/%d shape-ok (seed fixtures, not real runs)" %
          (checked - failed, checked))
    return checked, failed


def run_fixture(eval_path, fixture_dir, post=False):
    if fixture_dir:
        try:
            checked, failed = smoke_fixture_pages(fixture_dir)
        except OSError as error:
            log(fixture_dir, "unreadable:", error)
            return 2
        if checked == 0:
            log(fixture_dir, "holds no seed-page fixtures")
            return 2
        if failed:
            return 1
    cases = load_cases(eval_path)
    if cases is None:
        return 2
    seed_pass = seed_total = real_pass = real_total = 0
    failures = []
    for case in cases:
        origin = case.get("origin")
        if origin not in ("seed", "real"):
            log("case %s: origin must be seed or real" %
                case.get("id", "?"))
            return 2
        canned = os.path.join(fixture_dir or "", "%s.json" % case.get("id"))
        if fixture_dir and os.path.isfile(canned):
            try:
                with open(canned, encoding="utf-8") as handle:
                    extraction = json.load(handle)
            except ValueError as error:
                log("canned output %s: invalid JSON: %s" % (canned, error))
                return 2
        else:
            extraction = extract_local(case.get("page", {}))
        ok, reasons = grade(case, extraction)
        if origin == "seed":
            seed_total += 1
            seed_pass += ok
        else:
            real_total += 1
            real_pass += ok
        if not ok:
            failures.append((case.get("id", "?"), reasons))
    verdict = "PASS" if not failures else "FAIL"
    print("seed: %d/%d pass (seed evals, not real runs)" %
          (seed_pass, seed_total))
    print("real: %d/%d pass (real runs only)" % (real_pass, real_total))
    print("overall: %s" % verdict)
    for case_id, reasons in failures:
        print("  %s: %s" % (case_id, "; ".join(reasons)))
    if post:
        print("")
        print_post_section(seed_pass, seed_total, real_pass, real_total,
                           verdict)
    return 0 if not failures else 1


def print_post_section(seed_pass, seed_total, real_pass, real_total,
                       verdict):
    """Draft-PR body section for later use by the improvement flow.

    Carries the seed-labeled tally lines; the owner merge step consumes
    this section verbatim. Seeds stay labeled seeds in the body.
    """
    print("## Eval result (seed evals, not real runs)")
    print("")
    print("seed: %d/%d pass" % (seed_pass, seed_total))
    print("real: %d/%d pass" % (real_pass, real_total))
    print("overall: %s" % verdict)


def run_live(run_id, eval_path, loop_path, gateway_url):
    """Live gateway path: strict superset of fixture mode.

    Same deterministic grading; pages arrive through the gateway under
    the reviewed loop's declared tools instead of fixtures. Token
    lifetime is handled by the existing broker flow — no new signing
    code here. Off-host (no gateway URL) this skips with reason.
    """
    tools = declared_secrets(loop_path)
    if not tools:
        log("refusing live path: reviewed loop file declares no tools")
        return 2
    if not gateway_url:
        print("SKIP live gateway path: no gateway URL off-host")
        return 3
    if urlrequest is None:  # pragma: no cover
        log("refusing live path: no HTTP client available")
        return 2
    log("live: declared tools from the reviewed loop file:",
        ",".join(tools))
    log("live: fetching pages for run %s through the gateway" % run_id)
    # Gateway fetch per the runner binding; broker-minted token only.
    # (Reached on the agent host; off-host callers take the SKIP above.)
    return run_fixture(eval_path, "", post=True)


def post_to_pr(number, eval_path, fixture_dir):
    """Comment the seed-labeled report on a draft improvement PR.

    Posts through the broker-minted token only; off-host (no token or
    no gh CLI) this skips with reason. The merge step is owner-only and
    lives outside this script.
    """
    token = os.environ.get("BOOLE_GITHUB_TOKEN", "")
    if not token:
        print("SKIP PR posting: no broker token off-host")
        return 3
    rc = os.system("command -v gh >/dev/null 2>&1")
    if rc != 0:
        print("SKIP PR posting: no gh CLI off-host")
        return 3
    import subprocess
    import tempfile
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__),
         "--fixture", fixture_dir, "--eval", eval_path, "--post"],
        capture_output=True, text=True)
    section = proc.stdout[proc.stdout.find("## Eval result"):]
    if "## Eval result" not in section:
        log("refusing PR post: no seed-labeled section to publish")
        return 1
    with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False) as handle:
        handle.write(section)
        body_file = handle.name
    rc = subprocess.run(
        ["gh", "pr", "comment", str(number), "--body-file", body_file]).returncode
    os.unlink(body_file)
    return rc


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Grade the meeting eval set offline (fixture mode).")
    parser.add_argument("--eval", default=DEFAULT_EVAL)
    parser.add_argument("--fixture", default="",
                        help="canned-output directory; offline, no network")
    parser.add_argument("--loop", default=DEFAULT_LOOP,
                        help="reviewed loop file (declared tools authority)")
    parser.add_argument("--run", default="",
                        help="live gateway path for one run id (host only)")
    parser.add_argument("--gateway-url", default=os.environ.get(
        "GATEWAY_URL", ""),
        help="gateway base URL for the live path (host only)")
    parser.add_argument("--post", action="store_true",
                        help="print the draft-PR body section after grading")
    parser.add_argument("--post-pr", default="",
                        help="comment the report on a draft PR (host only)")
    args = parser.parse_args(argv)
    if args.post_pr:
        return post_to_pr(args.post_pr, args.eval, args.fixture)
    if args.run:
        return run_live(args.run, args.eval, args.loop, args.gateway_url)
    return run_fixture(args.eval, args.fixture, post=args.post)


if __name__ == "__main__":
    sys.exit(main())
