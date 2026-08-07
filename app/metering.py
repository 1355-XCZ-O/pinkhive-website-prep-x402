"""Tiny SQLite audit meter. Payment settlement remains the channel's job."""
import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import closing

_LOCK = threading.Lock()


def configured_api_keys() -> set[str]:
    raw = os.environ.get("API_KEYS_JSON", "[]")
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return {str(value) for value in parsed.values()}
    if isinstance(parsed, list):
        return {str(value) for value in parsed}
    raise ValueError("API_KEYS_JSON must be an array or object")


def key_fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


class Meter:
    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("METER_DB", "usage.sqlite3")
        self._ensure()

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def _ensure(self):
        with closing(self._connect()) as db:
            with db:
                db.execute("CREATE TABLE IF NOT EXISTS usage (request_id TEXT PRIMARY KEY, created_at INTEGER, key_fp TEXT, route TEXT, status INTEGER, units INTEGER, input_chars INTEGER, elapsed_ms REAL, idempotency_key TEXT)")
                columns = {row[1] for row in db.execute("PRAGMA table_info(usage)")}
                if "idempotency_key" not in columns:
                    db.execute("ALTER TABLE usage ADD COLUMN idempotency_key TEXT")
                db.execute("CREATE UNIQUE INDEX IF NOT EXISTS usage_idempotency ON usage(key_fp, route, idempotency_key) WHERE idempotency_key IS NOT NULL")

    def record(self, key: str, route: str, status: int, units: int, input_chars: int, elapsed_ms: float, idempotency_key: str | None = None) -> str:
        request_id = str(uuid.uuid4())
        with _LOCK, closing(self._connect()) as db:
            with db:
                if idempotency_key:
                    row = db.execute("SELECT request_id FROM usage WHERE key_fp=? AND route=? AND idempotency_key=?", (key_fingerprint(key), route, idempotency_key)).fetchone()
                    if row:
                        return row[0]
                db.execute("INSERT INTO usage (request_id, created_at, key_fp, route, status, units, input_chars, elapsed_ms, idempotency_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (request_id, int(time.time()), key_fingerprint(key), route, status, units, input_chars, elapsed_ms, idempotency_key or None))
        return request_id

    def summary(self, key: str) -> dict:
        with closing(self._connect()) as db:
            row = db.execute("SELECT COUNT(*), COALESCE(SUM(units),0), COALESCE(SUM(input_chars),0), COALESCE(AVG(elapsed_ms),0) FROM usage WHERE key_fp=? AND status=200", (key_fingerprint(key),)).fetchone()
        return {"successful_requests": row[0], "units": row[1], "input_chars": row[2], "average_elapsed_ms": round(row[3], 3)}
