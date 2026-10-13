#!/usr/bin/env python3
"""Notion meetings poller (Phase 4, LOOP-01/LOOP-02 trigger seam).

Settled seam per 04-CONTEXT.md: the controller polls the Notion meetings
database every 5 minutes; one new meeting page yields exactly one queued
run. The upstream audio-notes-to-Notion leg is a documented assumption,
NOT code here: no third-party meeting-tool credentials, scrapers, or
unofficial APIs anywhere in this file.

Page content is untrusted (ADR-0006 rule 3): the poller forwards only the
loop name plus the page id (inside the idempotency key) plus the budget.
Tools and credentials come from agents/loops/meeting.yaml only. The
reviewed YAML registry is the only authority the Dispatcher trusts.

Cursor plus idempotency backstop: the cursor (last_edited_time) is
persisted AFTER successful enqueue; a restart re-poll creates no second
run because Dispatcher.enqueue dedupes on notion-page-<page-id>.

Dependencies: Python 3 standard library only (urllib, json, sqlite3).
"""
import argparse
import json
import os
import sqlite3
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dispatcher import Dispatcher  # noqa: E402

NOTION_VERSION = "2026-03-11"
POLL_INTERVAL_SECONDS = 300
LOOP_NAME = "meeting"
BUDGET_USD = 30.0


def log(*parts):
    print("hyprn-poll-notion:", *parts, file=sys.stderr, flush=True)


def page_is_usable(page):
    """True when a page carries extractable content. Malformed pages are
    data to skip with a logged reason, never authority to enqueue."""
    if not isinstance(page, dict) or not page.get("id"):
        return False
    title = page.get("title") or (page.get("properties") or {}).get("title")
    body = page.get("body") or (page.get("properties") or {}).get("body")
    return bool(title or body)


def envelope_for(page_id):
    """The ONLY payload the poller forwards: loop, page id inside the
    idempotency key, and budget. No page content crosses into the queue."""
    return {
        "idempotency_key": "notion-page-%s" % page_id,
        "loop": LOOP_NAME,
        "budget_usd": BUDGET_USD,
    }


def already_queued(dispatcher, key):
    """Idempotency backstop probe: True when the key has a run row."""
    try:
        row = dispatcher.db.execute(
            "SELECT id FROM runs WHERE idempotency_key = ?", (key,)).fetchone()
        return row is not None
    except Exception as error:  # exotic fake without a db: fall to enqueue
        log("queue probe failed, enqueueing:", error)
        return False


def poll_once(pages, dispatcher, cursor=None):
    """Enqueue one run per new usable page. Returns (run_ids, new_cursor).

    pages: iterable of page dicts with id + last_edited_time.
    cursor: last last_edited_time already processed; older pages skipped.
    Malformed pages are skipped with a logged reason, never enqueued.
    Already-queued page ids enqueue no second run (idempotency backstop).
    Only newly created run ids are returned.
    """
    run_ids = []
    new_cursor = cursor
    for page in sorted(pages, key=lambda p: str(p.get("last_edited_time", ""))):
        if not isinstance(page, dict) or not page.get("id"):
            log("skipping page without id")
            continue
        edited = str(page.get("last_edited_time", ""))
        if cursor is not None and edited <= str(cursor):
            continue
        if not page_is_usable(page):
            log("skipping malformed page %s: no title or body" % page.get("id"))
            continue
        key = "notion-page-%s" % page["id"]
        if already_queued(dispatcher, key):
            log("page %s already queued, no second run" % page.get("id"))
            if new_cursor is None or edited > str(new_cursor):
                new_cursor = edited
            continue
        run_id = dispatcher.enqueue(envelope_for(page["id"]))
        if run_id is None:
            log("enqueue refused for page %s (unknown loop?)" % page.get("id"))
            continue
        run_ids.append(run_id)
        if new_cursor is None or edited > str(new_cursor):
            new_cursor = edited
    return run_ids, new_cursor


def load_cursor(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip() or None
    except OSError:
        return None


def save_cursor(path, cursor):
    if cursor is None:
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(str(cursor))


def scan_fixture_dir(directory):
    """File-drop/manual-page fallback: read meeting pages from JSON files
    instead of the Notion API. Used by --fixture mode and tests."""
    pages = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as handle:
            pages.append(json.load(handle))
    return pages


def _notion_get(api_base, token, path):
    request = urllib.request.Request(
        "%s%s" % (api_base, path),
        headers={
            "Authorization": "Bearer %s" % token,
            "Notion-Version": NOTION_VERSION,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _notion_post(api_base, token, path, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "%s%s" % (api_base, path),
        data=data,
        headers={
            "Authorization": "Bearer %s" % token,
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def resolve_data_source(api_base, token, database_id):
    """Resolve data_sources for a legacy database id via GET v1/databases."""
    doc = _notion_get(api_base, token, "/v1/databases/%s" % database_id)
    sources = doc.get("data_sources", [])
    return [s.get("id") for s in sources if s.get("id")]


def query_notion(api_base, token, source_id, cursor=None):
    """Query the meetings data source, falling back to a legacy
    databases-query probe when the data-source id is a database id."""
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    try:
        return _notion_post(
            api_base, token, "/v1/data_sources/%s/query" % source_id, payload)
    except OSError as error:
        log("data-source query failed, trying legacy database probe:", error)
    data_source_ids = resolve_data_source(api_base, token, source_id)
    if not data_source_ids:
        raise OSError("no data sources found for %s" % source_id)
    return _notion_post(
        api_base, token, "/v1/data_sources/%s/query" % data_source_ids[0],
        payload)


def open_queue(db_path):
    connection = sqlite3.connect(db_path)
    schema_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, encoding="utf-8") as handle:
        connection.executescript(handle.read())
    return connection


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Poll the Notion meetings database; enqueue one run "
                    "per new meeting page.")
    parser.add_argument("--fixture", metavar="DIR",
                        help="scan a directory of page JSON files, no network")
    parser.add_argument("--db", default="controller/queue.db")
    parser.add_argument("--cursor-file", default="controller/poll_notion.cursor")
    parser.add_argument("--loop", default=LOOP_NAME)
    parser.add_argument("--source", default="",
                        help="Notion data-source (or legacy database) id")
    args = parser.parse_args(argv)

    if args.loop != LOOP_NAME:
        log("refusing unregistered loop:", args.loop)
        return 2

    if args.fixture:
        pages = scan_fixture_dir(args.fixture)
        next_api_cursor = None
    else:
        token = os.environ.get("NOTION_TOKEN", "")
        if not token or not args.source:
            log("NOTION_TOKEN and --source required for live polling")
            return 2
        api_base = os.environ.get("NOTION_API_BASE", "https://api.notion.com")
        doc = query_notion(api_base, token, args.source,
                           load_cursor(args.cursor + ".api"))
        pages = doc.get("results", [])
        next_api_cursor = doc.get("next_cursor")

    cursor = load_cursor(args.cursor_file)
    connection = open_queue(args.db)
    dispatcher = Dispatcher(connection)
    run_ids, new_cursor = poll_once(pages, dispatcher, cursor)
    # Cursor persists AFTER successful enqueue (idempotency backstop).
    save_cursor(args.cursor_file, new_cursor)
    if next_api_cursor:
        save_cursor(args.cursor + ".api", next_api_cursor)
    for run_id in run_ids:
        print(run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
