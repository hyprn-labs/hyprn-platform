#!/usr/bin/env python3
"""Fleet controller dispatcher (Phase 3, CP-02/CP-03/CP-04/CP-05).

Trigger envelopes are untrusted (ADR-0006 rule 3): the idempotency key is
recorded BEFORE any dispatch, and unknown loop names are refused BEFORE
any credential or compute is touched. The reviewed YAML registry is the
only authority for tools, credentials and destinations.

Socket-Mode note: the controller holding ops connections assumes the
accepted ADR-0006 operating model.

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
AWAITING_APPROVAL = "awaiting_approval"
KILLED = "killed"


def log(*parts):
    print("hyprn-dispatcher:", *parts, file=sys.stderr, flush=True)


class Dispatcher:
    """Idempotent, registry-gated queue over a run-state database.

    Seams (constructor-injected fakes in tests, real adapters in prod):
      registry: callable returning {loop_name: loop_doc}
      gateway: spend ledger (dict loop -> spent_usd, or object with spend())
      now: clock callable (fake clock in parked-approval tests)
    """

    def __init__(self, db, registry=None, gateway=None, now=None):
        self.db = db
        self.db.row_factory = sqlite3.Row
        self._registry = registry or (lambda: {})
        self._gateway = gateway if gateway is not None else {}
        self._now = now or time.time
        self._wake_signals = []
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
        self._wake_signals.append(run_id)
        return run_id

    def dispatch(self, run_id):
        """Budget/kill/registry gates for one queued run. Returns new state."""
        row = self.db.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None or row["state"] != QUEUED:
            return None
        if row["loop"] not in self.registry():
            log("refusing unregistered loop at dispatch:", row["loop"])
            return None
        if row["kill_loop"] or row["kill_agent"] or row["kill_fleet"]:
            self._set_state(run_id, KILLED)
            log(run_id, "killed: flag set")
            return KILLED
        if self._spend_for(row["loop"]) + 1 > row["budget_usd"]:
            log(run_id, "refused: over budget")
            return None
        self._set_state(run_id, RUNNING)
        return RUNNING

    def park(self, run_id, question):
        """Park a run awaiting approval. Holds a DB row, never a process."""
        self.db.execute(
            "INSERT INTO approvals(run_id, question, answer) VALUES(?, ?, NULL)",
            (run_id, question),
        )
        self._set_state(run_id, AWAITING_APPROVAL)
        self.db.commit()

    def resume(self, run_id, answer, sender, owner):
        """Resume a parked run only on the loop owner's answer. Else ignore."""
        if sender != owner:
            log(run_id, "ignoring answer from non-owner:", sender)
            return False
        self.db.execute(
            "UPDATE approvals SET answer = ?, decided_at = datetime('now')"
            " WHERE run_id = ? AND answer IS NULL",
            (answer, run_id),
        )
        self._set_state(run_id, QUEUED)
        self.db.commit()
        return True

    def pending_wake(self):
        """Drain host-wake signals raised by newly queued runs."""
        signals, self._wake_signals = self._wake_signals, []
        return signals

    def record_cost(self, run_id, amount_usd):
        self.db.execute(
            "UPDATE runs SET cost_usd = cost_usd + ? WHERE id = ?",
            (float(amount_usd), run_id),
        )
        self.db.commit()

    def _spend_for(self, loop):
        try:
            if isinstance(self._gateway, dict):
                return float(self._gateway.get(loop, 0))
            return float(self._gateway.spend(loop))
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            log("spend lookup failed:", error)
            return 0.0

    def _set_state(self, run_id, state):
        self.db.execute("UPDATE runs SET state = ? WHERE id = ?", (state, run_id))
        self.db.commit()


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
