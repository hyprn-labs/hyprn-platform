#!/usr/bin/env python3
"""Loop registry validator (Phase 3, CP-05 + EGR-03).

Trigger payloads are untrusted (ADR-0006 rule 3): the reviewed YAML in
agents/loops/ is the only authority for a loop's tools, credentials and
destinations. This validator is the static gate the dispatcher trusts.

Dependencies: Python 3 standard library and PyYAML (Debian python3-yaml).
"""
import sys

# Third-party: PyYAML (Debian package python3-yaml).
import yaml


REQUIRED = {"name", "owner", "trigger", "steps", "tools", "autonomy",
            "budget", "egress_allowlist", "runtime", "eval_set",
            "promotion_rule"}

AUTONOMY_LEVELS = {"A0", "A1", "A2", "A3"}


def log(*parts):
    print("hyprn-loops:", *parts, file=sys.stderr, flush=True)


def validate(path):
    """Validate one loop file. Returns True when valid, False otherwise."""
    try:
        with open(path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
    except (ValueError, OSError) as error:
        log(path, "unparseable:", error)
        return False
    try:
        if not isinstance(doc, dict):
            raise ValueError("top-level mapping required")
        missing = REQUIRED - set(doc)
        assert not missing, "missing %s" % sorted(missing)
        assert doc["egress_allowlist"], "EGR-03 forbids empty allowlist"
        assert isinstance(doc["autonomy"], dict), "autonomy must be a mapping"
        for action, level in doc["autonomy"].items():
            assert level in AUTONOMY_LEVELS, "bad level %r for %s" % (level, action)
    except (ValueError, KeyError, AssertionError, AttributeError, TypeError) as error:
        log(path, "invalid:", error)
        return False
    return True


def main():
    if len(sys.argv) < 2:
        log("usage: validate.py <loop.yaml> [...]")
        return 2
    failed = 0
    for path in sys.argv[1:]:
        if not validate(path):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
