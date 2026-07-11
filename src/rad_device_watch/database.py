from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    station_name TEXT,
    modality TEXT,
    location TEXT,
    department TEXT,
    software_version TEXT,
    install_date TEXT,
    manufacture_date TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS downtime_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_minutes REAL,
    cause_category TEXT,
    cause_detail TEXT,
    impact_level TEXT,
    created_by TEXT DEFAULT 'manual',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    procedure_date TEXT NOT NULL,
    procedure_count INTEGER DEFAULT 1,
    modality TEXT,
    department TEXT,
    source TEXT DEFAULT 'manual',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS maintenance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    maintenance_type TEXT NOT NULL,
    scheduled_date TEXT,
    completed_date TEXT,
    description TEXT,
    vendor TEXT,
    cost REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    metric TEXT NOT NULL,
    condition TEXT NOT NULL,
    threshold REAL NOT NULL,
    channel TEXT DEFAULT 'console',
    channel_config TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_rule_id INTEGER REFERENCES alert_rules(id),
    device_id INTEGER REFERENCES devices(id),
    triggered_at TEXT NOT NULL,
    message TEXT NOT NULL,
    channel TEXT,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

logger = logging.getLogger(__name__)
_SMTP_PASSWORD_ENV = "RAD_DEVICE_WATCH_SMTP_PASSWORD"


class Database:
    def __init__(self, path: str | Path = "rad_device_watch.db"):
        self._path = Path(path)
        self._conn: sqlite3.Connection | None = None

    @property
    def path(self) -> Path:
        return self._path

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def init_schema(self) -> None:
        conn = self.connect()
        conn.executescript(_SCHEMA_SQL)
        _redact_plaintext_smtp_passwords(conn)
        conn.commit()

    def execute(self, sql: str, params=()):
        return self.connect().execute(sql, params)

    def executemany(self, sql: str, seq):
        return self.connect().executemany(sql, seq)

    def commit(self) -> None:
        if self._conn is not None:
            self._conn.commit()

    def rollback(self) -> None:
        if self._conn is not None:
            self._conn.rollback()

    def fetchone(self, sql: str, params=()) -> sqlite3.Row | None:
        return self.connect().execute(sql, params).fetchone()

    def fetchall(self, sql: str, params=()) -> list[sqlite3.Row]:
        return self.connect().execute(sql, params).fetchall()

    def row_to_dict(self, row: sqlite3.Row) -> dict:
        return dict(row)

    def row_to_dict_or_none(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return dict(row)

    def rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in rows]

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


def _redact_plaintext_smtp_passwords(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """SELECT id, channel_config FROM alert_rules
           WHERE channel = 'email' AND channel_config IS NOT NULL"""
    ).fetchall()
    for row in rows:
        try:
            config = json.loads(row["channel_config"])
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(config, dict) or "password" not in config:
            continue
        config.pop("password", None)
        config.setdefault("password_env", _SMTP_PASSWORD_ENV)
        conn.execute(
            "UPDATE alert_rules SET channel_config = ? WHERE id = ?",
            (json.dumps(config, sort_keys=True), row["id"]),
        )
        logger.warning(
            "Removed a plaintext SMTP password from alert rule %s; configure %s instead",
            row["id"],
            config["password_env"],
        )
