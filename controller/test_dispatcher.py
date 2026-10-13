#!/usr/bin/env python3
"""Dispatcher unit tests (Phase 3, tracer slice). Stdlib unittest, fakes
only: no network, no cloud, no keys. Run: python3 -m unittest discover -s controller."""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Dispatcher  # noqa: E402

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def fresh_db():
    connection = sqlite3.connect(":memory:")
    with open(SCHEMA, encoding="utf-8") as handle:
        connection.executescript(handle.read())
    return connection


def registry_of(*names):
    return lambda: {name: {"name": name} for name in names}


def envelope(loop="meeting-test", key="env-1", budget=30.0):
    return {"idempotency_key": key, "loop": loop, "budget_usd": budget}


class TestIdempotentEnqueue(unittest.TestCase):
    def test_same_envelope_twice_enqueues_once(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        first = disp.enqueue(envelope())
        second = disp.enqueue(envelope())
        self.assertEqual(first, second)
        rows = disp.db.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
        self.assertEqual(rows, 1)

    def test_distinct_envelopes_enqueue_distinct_runs(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        first = disp.enqueue(envelope(key="env-1"))
        second = disp.enqueue(envelope(key="env-2"))
        self.assertNotEqual(first, second)


class TestRegistryGate(unittest.TestCase):
    def test_unknown_loop_refused_before_compute(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        self.assertIsNone(disp.enqueue(envelope(loop="no-such-loop")))
        rows = disp.db.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
        self.assertEqual(rows, 0)

    def test_known_loop_dispatches(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        run_id = disp.enqueue(envelope())
        self.assertEqual(disp.dispatch(run_id), "running")

    def test_bad_envelope_rejected(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        self.assertIsNone(disp.enqueue({"loop": "meeting-test"}))
        self.assertIsNone(disp.enqueue(None))


if __name__ == "__main__":
    unittest.main()
