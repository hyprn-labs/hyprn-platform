#!/usr/bin/env python3
"""Notion poller unit tests (Phase 4, LOOP-01 trigger seam). Stdlib
unittest, fakes only: no network, no cloud, no keys. Run:
python3 -m unittest discover -s controller -p "test_poll*"."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Dispatcher  # noqa: E402
import poll_notion
from poll_notion import envelope_for, page_is_usable, poll_once  # noqa: E402

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "agents", "loops", "testdata", "meeting-pages")


def fresh_db():
    connection = sqlite3.connect(":memory:")
    with open(SCHEMA, encoding="utf-8") as handle:
        connection.executescript(handle.read())
    return connection


def registry_of(*names):
    return lambda: {name: {"name": name} for name in names}


def load_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return json.load(handle)


class TestPollSeam(unittest.TestCase):
    def test_one_fixture_page_yields_one_run(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        run_ids, _ = poll_once([load_fixture("new.json")], disp)
        self.assertEqual(run_ids, ["run-notion-page-page-abc123"])

    def test_same_page_twice_enqueues_once(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        first, cursor = poll_once([load_fixture("new.json")], disp)
        second, _ = poll_once([load_fixture("new.json"),
                               load_fixture("updated.json")], disp,
                              cursor=cursor)
        # updated.json carries the same page id: idempotency backstop plus
        # cursor advance mean no second run.
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        rows = disp.db.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
        self.assertEqual(rows, 1)

    def test_updated_page_does_not_create_second_run(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        _, cursor = poll_once([load_fixture("new.json")], disp)
        run_ids, _ = poll_once([load_fixture("updated.json")], disp,
                               cursor=cursor)
        self.assertEqual(run_ids, [])

    def test_malformed_page_skipped_never_enqueued(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        self.assertFalse(page_is_usable(load_fixture("malformed.json")))
        run_ids, _ = poll_once([load_fixture("malformed.json")], disp)
        self.assertEqual(run_ids, [])
        rows = disp.db.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
        self.assertEqual(rows, 0)

    def test_unknown_loop_refused(self):
        disp = Dispatcher(fresh_db(), registry=registry_of("meeting"))
        self.assertIsNone(disp.enqueue(
            {"idempotency_key": "notion-page-x", "loop": "no-such-loop"}))
        rows = disp.db.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
        self.assertEqual(rows, 0)

    def test_cursor_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_file = os.path.join(tmp, "queue.db")
            cursor_file = os.path.join(tmp, "cursor")
            # First poll through one Dispatcher instance.
            disp1 = Dispatcher(poll_notion.open_queue(db_file),
                               registry=registry_of("meeting"))
            first, cursor = poll_once([load_fixture("new.json")], disp1)
            self.assertEqual(len(first), 1)
            poll_notion.save_cursor(cursor_file, cursor)
            # Simulate restart: a NEW Dispatcher over the SAME database
            # file, cursor reloaded from disk.
            disp2 = Dispatcher(poll_notion.open_queue(db_file),
                               registry=registry_of("meeting"))
            reloaded = poll_notion.load_cursor(cursor_file)
            self.assertEqual(reloaded, cursor)
            run_ids, _ = poll_once(
                [load_fixture("new.json"), load_fixture("updated.json")],
                disp2, cursor=reloaded)
            self.assertEqual(run_ids, [])
            rows = disp2.db.execute(
                "SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
            self.assertEqual(rows, 1)

    def test_envelope_carries_only_loop_page_id_budget(self):
        envelope = envelope_for("page-abc123")
        self.assertEqual(set(envelope),
                         {"idempotency_key", "loop", "budget_usd"})
        self.assertEqual(envelope["idempotency_key"],
                         "notion-page-page-abc123")
        self.assertNotIn("body", envelope)
        self.assertNotIn("title", envelope)


if __name__ == "__main__":
    unittest.main()
