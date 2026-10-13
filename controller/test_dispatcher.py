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


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestParkedApproval(unittest.TestCase):
    def test_park_survives_hours_and_resumes_on_owner_answer(self):
        clock = FakeClock()
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"), now=clock)
        run_id = disp.enqueue(envelope())
        disp.dispatch(run_id)
        disp.park(run_id, "post to slack?")
        clock.advance(3 * 3600)
        state = disp.db.execute(
            "SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()["state"]
        self.assertEqual(state, "awaiting_approval")
        self.assertTrue(disp.resume(run_id, "yes", "platform-owner", "platform-owner"))
        state = disp.db.execute(
            "SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()["state"]
        self.assertEqual(state, "queued")

    def test_stranger_answer_leaves_run_parked(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        run_id = disp.enqueue(envelope())
        disp.dispatch(run_id)
        disp.park(run_id, "post to slack?")
        self.assertFalse(disp.resume(run_id, "yes", "stranger", "platform-owner"))
        state = disp.db.execute(
            "SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()["state"]
        self.assertEqual(state, "awaiting_approval")

    def test_pending_run_raises_host_wake(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        disp.enqueue(envelope())
        self.assertEqual(len(disp.pending_wake()), 1)
        self.assertEqual(disp.pending_wake(), [])


class TestBudgetKill(unittest.TestCase):
    def test_over_budget_run_refused_before_start(self):
        disp = Dispatcher(
            fresh_db(), registry=registry_of("meeting-test"),
            gateway={"meeting-test": 100.0})
        run_id = disp.enqueue(envelope(budget=30.0))
        self.assertIsNone(disp.dispatch(run_id))
        state = disp.db.execute(
            "SELECT state FROM runs WHERE id = ?", (run_id,)).fetchone()["state"]
        self.assertEqual(state, "queued")

    def test_kill_flag_stops_run_within_one_poll(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        run_id = disp.enqueue(envelope())
        disp.db.execute("UPDATE runs SET kill_loop = 1 WHERE id = ?", (run_id,))
        disp.db.commit()
        self.assertEqual(disp.dispatch(run_id), "killed")

    def test_fleet_flag_blocks_all_loops(self):
        disp = Dispatcher(
            fresh_db(), registry=registry_of("meeting-test", "other-loop"))
        first = disp.enqueue(envelope(loop="meeting-test", key="k1"))
        second = disp.enqueue(envelope(loop="other-loop", key="k2"))
        disp.db.execute("UPDATE runs SET kill_fleet = 1")
        disp.db.commit()
        self.assertEqual(disp.dispatch(first), "killed")
        self.assertEqual(disp.dispatch(second), "killed")

    def test_cost_accumulates_per_run(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting-test"))
        run_id = disp.enqueue(envelope())
        disp.record_cost(run_id, 1.5)
        disp.record_cost(run_id, 2.5)
        cost = disp.db.execute(
            "SELECT cost_usd FROM runs WHERE id = ?", (run_id,)).fetchone()["cost_usd"]
        self.assertAlmostEqual(cost, 4.0)


if __name__ == "__main__":
    unittest.main()
