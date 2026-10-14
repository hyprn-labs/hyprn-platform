-- Run-state schema (Phase 3, CP-02/CP-03/CP-04).
-- Portable to SQLite now and Cloud SQL (Postgres) at apply: only
-- TEXT, REAL and INTEGER columns with datetime('now') defaults.
CREATE TABLE IF NOT EXISTS runs(
  id TEXT PRIMARY KEY,
  loop TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'queued',
  idempotency_key TEXT NOT NULL UNIQUE,
  budget_usd REAL NOT NULL,
  cost_usd REAL NOT NULL DEFAULT 0,
  kill_loop INTEGER NOT NULL DEFAULT 0,
  kill_agent INTEGER NOT NULL DEFAULT 0,
  kill_fleet INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS approvals(
  run_id TEXT NOT NULL REFERENCES runs(id),
  question TEXT NOT NULL,
  answer TEXT,
  decided_at TEXT
);
-- Owner-feedback store (Phase 5, LRN-01): reactions, replies and approval
-- answers filed beside their run. Portable types only (TEXT/INTEGER plus
-- datetime('now')), matching the runs/approvals idiom above. Duplicate
-- Socket-Mode deliveries dedupe on the caller-supplied dedupe_key.
CREATE TABLE IF NOT EXISTS feedback(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL REFERENCES runs(id),
  kind TEXT NOT NULL,
  payload TEXT NOT NULL,
  sender TEXT NOT NULL DEFAULT '',
  dedupe_key TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
