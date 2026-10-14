#!/usr/bin/env python3
"""Promotion-rule check template (Phase 5, LRN-04).

Evaluates the meeting loop's promotion rule from the reviewed registry
file: pass rate over the last N real runs at least min_pass_rate AND
corrections per run below max_corrections_per_run. Seeds are excluded
from every count; fewer real runs than required prints INSUFFICIENT
DATA (never a false PASS) with a non-zero exit.

This ships as a reviewed-change template per D-promotion-template: even
a PASS verdict only prints the template text — it never flips autonomy
in the loop file. Executed promotion with ten real runs stays deferred
to the trial, merged by the owner.

Usage:
  promotion.py <loop.yaml> [--eval <jsonl>] [--runs <ledger.json>]

The corrections ledger is a JSON object mapping run id to correction
count. Absent entries count as zero with a note; the trial replaces
this with the run ledger. Exit codes: 0 template-PASS, 1 HOLD,
2 usage/error, 3 INSUFFICIENT DATA.

Dependencies: Python 3 standard library, PyYAML (Debian python3-yaml),
and run.py in this directory for deterministic grading.
"""
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run  # noqa: E402


def log(*parts):
    print("hyprn-promotion:", *parts, file=sys.stderr, flush=True)


def load_thresholds(loop_path):
    """Read the promotion rule from the reviewed loop file at check time."""
    try:
        with open(loop_path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        rule = doc.get("promotion_rule", {})
        return (float(rule["min_pass_rate"]), int(rule["last_runs"]),
                float(rule["max_corrections_per_run"]))
    except (OSError, ValueError, KeyError, TypeError,
            AttributeError) as error:
        log(loop_path, "promotion rule unreadable:", error)
        return None


def real_verdicts(eval_path):
    """Grade real-origin eval cases deterministically. Seeds excluded."""
    cases = run.load_cases(eval_path)
    if cases is None:
        return None
    seed_total = 0
    verdicts = []
    for case in cases:
        if case.get("origin") != "real":
            seed_total += 1
            continue
        ok, _ = run.grade(case, run.extract_local(case.get("page", {})))
        verdicts.append((case.get("id", "?"), ok))
    return seed_total, verdicts


def load_corrections(path):
    if not path:
        return {}, False
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return {str(key): int(value) for key, value in data.items()}, True
    except (OSError, ValueError, TypeError, AttributeError) as error:
        log(path, "corrections ledger unreadable:", error)
        return None, False


def check(loop_path, eval_path, corrections_path=""):
    thresholds = load_thresholds(loop_path)
    if thresholds is None:
        return 2
    min_rate, last_runs, max_corr = thresholds
    graded = real_verdicts(eval_path)
    if graded is None:
        return 2
    seed_total, verdicts = graded
    corrections, ledger_present = load_corrections(corrections_path)
    if corrections is None:
        return 2
    print("seed: %d cases excluded (seed evals, not real runs)" % seed_total)
    print("real: %d runs considered" % len(verdicts))
    if len(verdicts) < last_runs:
        print("INSUFFICIENT DATA (seeds excluded): %d real runs, need %d" %
              (len(verdicts), last_runs))
        return 3
    window = verdicts[-last_runs:]
    passes = sum(1 for _, ok in window if ok)
    rate = passes / len(window)
    if not ledger_present:
        log("note: corrections ledger absent; counting zero corrections")
    total_corr = sum(corrections.get(case_id, 0) for case_id, _ in window)
    corr_per_run = total_corr / len(window)
    print("pass rate over last %d real runs: %.2f" % (len(window), rate))
    print("corrections per real run: %.2f" % corr_per_run)
    if rate >= min_rate and corr_per_run < max_corr:
        print("TEMPLATE PASS: rule met; promotion ships only as a reviewed"
              " change merged by the owner (autonomy untouched by this"
              " script)")
        return 0
    print("HOLD: rule unmet; no promotion proposed")
    return 1


def main(argv=None):
    args = (argv if argv is not None else sys.argv[1:])
    if not args or args[0] in ("-h", "--help"):
        print("usage: promotion.py <loop.yaml> [--eval <jsonl>]"
              " [--runs <ledger.json>]")
        return 2
    loop_path = args[0]
    eval_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "loops", "meeting-eval.jsonl")
    corrections_path = ""
    rest = args[1:]
    index = 0
    while index < len(rest):
        if rest[index] == "--eval" and index + 1 < len(rest):
            eval_path = rest[index + 1]
            index += 2
        elif rest[index] == "--runs" and index + 1 < len(rest):
            corrections_path = rest[index + 1]
            index += 2
        else:
            log("unknown argument:", rest[index])
            return 2
    return check(loop_path, eval_path, corrections_path)


if __name__ == "__main__":
    sys.exit(main())
