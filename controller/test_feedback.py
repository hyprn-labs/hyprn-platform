#!/usr/bin/env python3
"""Feedback-store unit tests (Phase 5, LRN-01). Stdlib unittest, fakes
only: no network, no cloud, no keys. Run: python3 -m unittest discover -s controller."""
import json
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


def envelope(loop="meeting", key="env-1", budget=30.0):
    return {"idempotency_key": key, "loop": loop, "budget_usd": budget}


def queued_run(disp, key="feedback-run-1"):
    run_id = disp.enqueue(envelope(key=key))
    assert run_id is not None
    return run_id


class TestClosedKinds(unittest.TestCase):
    def test_unknown_kind_refused_with_no_row(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        run_id = queued_run(disp)
        self.assertIsNone(disp.record_feedback(
            run_id, "emoji-blast", json.dumps({"emoji": "eyes"}),
            sender="platform-owner", dedupe_key="fb-kind-1"))
        rows = disp.db.execute(
            "SELECT COUNT(*) AS n FROM feedback").fetchone()["n"]
        self.assertEqual(rows, 0)

    def test_each_closed_kind_stores(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        run_id = queued_run(disp)
        for index, kind in enumerate(("reaction", "reply", "approval")):
            row_id = disp.record_feedback(
                run_id, kind, json.dumps({"text": "seed"}),
                sender="platform-owner",
                dedupe_key="fb-kind-ok-%d" % index)
            self.assertIsNotNone(row_id)
        rows = disp.db.execute(
            "SELECT COUNT(*) AS n FROM feedback").fetchone()["n"]
        self.assertEqual(rows, 3)

    def test_feedback_without_dedupe_key_refused(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        run_id = queued_run(disp)
        self.assertIsNone(disp.record_feedback(
            run_id, "reaction", json.dumps({"emoji": "eyes"}),
            sender="platform-owner", dedupe_key=""))


class TestDedupeIdempotency(unittest.TestCase):
    def test_repeated_dedupe_key_stores_once(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        run_id = queued_run(disp)
        first = disp.record_feedback(
            run_id, "reaction", json.dumps({"emoji": "eyes"}),
            sender="platform-owner", dedupe_key="fb-socket-retry-1")
        second = disp.record_feedback(
            run_id, "reaction", json.dumps({"emoji": "eyes"}),
            sender="platform-owner", dedupe_key="fb-socket-retry-1")
        self.assertIsNotNone(first)
        self.assertEqual(first, second)
        rows = disp.db.execute(
            "SELECT COUNT(*) AS n FROM feedback").fetchone()["n"]
        self.assertEqual(rows, 1)


class TestUnknownRun(unittest.TestCase):
    def test_feedback_for_unknown_run_refused(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        self.assertIsNone(disp.record_feedback(
            "run-no-such-run", "reply", json.dumps({"text": "yes"}),
            sender="platform-owner", dedupe_key="fb-unknown-1"))
        rows = disp.db.execute(
            "SELECT COUNT(*) AS n FROM feedback").fetchone()["n"]
        self.assertEqual(rows, 0)


class TestApprovalPairing(unittest.TestCase):
    def test_owner_answer_records_approval_feedback(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        run_id = queued_run(disp)
        disp.dispatch(run_id)
        disp.park(run_id, "post to slack?")
        self.assertTrue(
            disp.resume(run_id, "yes", "platform-owner", "platform-owner"))
        row = disp.db.execute(
            "SELECT kind, payload, sender FROM feedback"
            " WHERE run_id = ?", (run_id,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["kind"], "approval")
        self.assertEqual(row["sender"], "platform-owner")
        self.assertEqual(json.loads(row["payload"])["answer"], "yes")

    def test_stranger_answer_stores_nothing(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        run_id = queued_run(disp)
        disp.dispatch(run_id)
        disp.park(run_id, "post to slack?")
        self.assertFalse(
            disp.resume(run_id, "yes", "stranger", "platform-owner"))
        rows = disp.db.execute(
            "SELECT COUNT(*) AS n FROM feedback").fetchone()["n"]
        self.assertEqual(rows, 0)


if __name__ == "__main__":
    unittest.main()
