#!/usr/bin/env python3
"""Meeting-loop eval runner (Phase 5, LRN-02/LRN-03).

Grades the seed-labeled eval set deterministically with zero network,
gateway, or token use. Fixture mode is the default offline seam (same
discipline as hyprn-credential-broker --fixture): every case is graded
from the eval file plus canned model outputs, so checks pass anywhere.

Usage:
  run.py --fixture <dir> --eval <jsonl>   # offline grading (checks use this)
  run.py --run <run-id> --eval <jsonl>     # live gateway path (05-02 stub)

Page text is untrusted data (ADR-0006 rule 3): the grader quotes page
lines as evidence and never follows embedded directives. Deterministic
verdicts are the only gate; any gateway-graded quality score stays
advisory-only. Reports print seed and real tallies on separate lines —
seeds are labeled seeds everywhere, never presented as real runs.

Dependencies: Python 3 standard library only (json, argparse).
"""
import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_EVAL = os.path.join(REPO_ROOT, "agents", "loops", "meeting-eval.jsonl")

CONTRACT_KEYS = ("decisions", "actions", "open_questions", "patch")


def log(*parts):
    print("hyprn-eval:", *parts, file=sys.stderr, flush=True)


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


def grade(case, extraction):
    """Grade one extraction against its expectations. Returns (ok, reasons)."""
    reasons = []
    page = case.get("page", {})
    expect = case.get("expect", {})
    if set(extraction.keys()) != set(CONTRACT_KEYS):
        return False, ["contract keys must be exactly %s" % (CONTRACT_KEYS,)]
    haystack = "%s\n%s" % (page.get("title") or "", page.get("body") or "")
    for key in ("decisions", "actions", "open_questions"):
        items = extraction.get(key, [])
        if not isinstance(items, list):
            return False, ["%s must be a list" % key]
        for item in items:
            source = item.get("source") if isinstance(item, dict) else ""
            if not source:
                reasons.append("%s item without quotable source" % key)
            elif source not in haystack:
                reasons.append(
                    "%s source does not quote the page" % key)
    if not isinstance(extraction.get("patch"), dict):
        reasons.append("patch must be an object")
    if len(extraction.get("decisions", [])) < expect.get("min_decisions", 0):
        reasons.append("fewer decisions than expected")
    if len(extraction.get("actions", [])) < expect.get("min_actions", 0):
        reasons.append("fewer actions than expected")
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


def run_fixture(eval_path, fixture_dir):
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
    print("seed: %d/%d pass (seed evals, not real runs)" %
          (seed_pass, seed_total))
    print("real: %d/%d pass (real runs only)" % (real_pass, real_total))
    if failures:
        print("overall: FAIL")
        for case_id, reasons in failures:
            print("  %s: %s" % (case_id, "; ".join(reasons)))
        return 1
    print("overall: PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Grade the meeting eval set offline (fixture mode).")
    parser.add_argument("--eval", default=DEFAULT_EVAL)
    parser.add_argument("--fixture", default="",
                        help="canned-output directory; offline, no network")
    parser.add_argument("--run", default="",
                        help="live gateway path (lands in 05-02)")
    args = parser.parse_args(argv)
    if args.run:
        log("live gateway path is a stub in 05-01; use --fixture offline")
        return 2
    return run_fixture(args.eval, args.fixture)


if __name__ == "__main__":
    sys.exit(main())
