#!/usr/bin/env python3
"""Fleet controller dispatcher (Phase 3, CP-02/CP-05 tracer slice).

Trigger envelopes are untrusted (ADR-0006 rule 3): the idempotency key is
recorded BEFORE any dispatch, and unknown loop names are refused BEFORE
any credential or compute is touched. The reviewed YAML registry is the
only authority for tools, credentials and destinations.

Dependencies: Python 3 standard library only (sqlite3).
"""
import sqlite3
import sys
import time


POLL_SECONDS = 15

SCHEMA_PATH = "controller/schema.sql"

QUEUED = "queued"
RUNNING = "running"


def log(*parts):
    print("hyprn-dispatcher:", *parts, file=sys.stderr, flush=True)


class Dispatcher:
    """Idempotent, registry-gated queue over a run-state database.

    Seams (constructor-injected fakes in tests, real adapters in prod):
      registry: callable returning {loop_name: loop_doc}
    """

    def __init__(self, db, registry=None):
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._registry = registry or (lambda: {})

    def registry(self):
        try:
            return self._registry()
        except (OSError, ValueError, KeyError) as error:
            log("registry load failed:", error)
            return {}

    def enqueue(self, envelope):
        """Insert one run for an envelope. Duplicate keys enqueue once."""
        try:
            key = envelope["idempotency_key"]
            loop = envelope["loop"]
        except (KeyError, TypeError) as error:
            log("bad envelope:", error)
            return None
        if loop not in self.registry():
            log("refusing unknown loop:", loop)
            return None
        run_id = "run-%s" % key
        try:
            self.db.execute(
                "INSERT INTO runs(id, loop, state, idempotency_key, budget_usd)"
                " VALUES(?, ?, 'queued', ?, ?)",
                (run_id, loop, key, float(envelope.get("budget_usd", 0))),
            )
            self.db.commit()
        except sqlite3.IntegrityError:
            return run_id  # duplicate envelope: already queued
        except (sqlite3.Error, ValueError) as error:
            log("enqueue failed:", error)
            return None
        return run_id

    def dispatch(self, run_id):
        """Gate one queued run on the registry. Returns the new state."""
        row = self.db.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None or row["state"] != QUEUED:
            return None
        if row["loop"] not in self.registry():
            log("refusing unregistered loop at dispatch:", row["loop"])
            return None
        self.db.execute("UPDATE runs SET state = ? WHERE id = ?", (RUNNING, run_id))
        self.db.commit()
        return RUNNING


def open_db(path=":memory:"):
    connection = sqlite3.connect(path)
    with open(SCHEMA_PATH, encoding="utf-8") as handle:
        connection.executescript(handle.read())
    return connection


def main():
    log("dispatcher module; queue driven by scheduler/CLI, not main()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
