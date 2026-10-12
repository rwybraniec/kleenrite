"""SQLite persistence: run history, per-record errors and per-flow state (watermarks)."""

import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, flow TEXT NOT NULL, started TEXT NOT NULL, finished TEXT,
  status TEXT NOT NULL, read INTEGER DEFAULT 0, written INTEGER DEFAULT 0, failed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS errors (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, flow TEXT NOT NULL,
  stage TEXT NOT NULL, message TEXT NOT NULL, record TEXT);
CREATE TABLE IF NOT EXISTS state (flow TEXT PRIMARY KEY, data TEXT NOT NULL);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = "integrator.db"):
        self.path = path
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self):
        return closing_conn(self.path)

    def start_run(self, flow: str) -> int:
        with self._conn() as c:
            return c.execute("INSERT INTO runs(flow, started, status) VALUES (?,?,'running')",
                             (flow, _now())).lastrowid

    def finish_run(self, run_id, status, read, written, failed):
        with self._conn() as c:
            c.execute("UPDATE runs SET finished=?, status=?, read=?, written=?, failed=? WHERE id=?",
                      (_now(), status, read, written, failed, run_id))

    def add_error(self, run_id, flow, stage, message, record=None):
        with self._conn() as c:
            c.execute("INSERT INTO errors(run_id, flow, stage, message, record) VALUES (?,?,?,?,?)",
                      (run_id, flow, stage, message, json.dumps(record, default=str) if record is not None else None))

    def get_state(self, flow: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT data FROM state WHERE flow=?", (flow,)).fetchone()
        return json.loads(row[0]) if row else {}

    def set_state(self, flow: str, data: dict):
        with self._conn() as c:
            c.execute("INSERT INTO state(flow, data) VALUES (?,?) "
                      "ON CONFLICT(flow) DO UPDATE SET data=excluded.data", (flow, json.dumps(data)))

    def runs(self, flow=None, limit=20):
        sql, args = "SELECT id, flow, started, status, read, written, failed FROM runs", []
        if flow:
            sql, args = sql + " WHERE flow=?", [flow]
        with self._conn() as c:
            return c.execute(sql + " ORDER BY id DESC LIMIT ?", args + [limit]).fetchall()

    def errors(self, flow=None, limit=50):
        sql, args = "SELECT run_id, flow, stage, message, record FROM errors", []
        if flow:
            sql, args = sql + " WHERE flow=?", [flow]
        with self._conn() as c:
            return c.execute(sql + " ORDER BY id DESC LIMIT ?", args + [limit]).fetchall()


class closing_conn:
    """Context manager: commit on success, always close (sqlite3's own `with` never closes)."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, *_):
        (self.conn.rollback if exc_type else self.conn.commit)()
        self.conn.close()
