from collections.abc import Generator
from pathlib import Path

import pytest

from rad_device_watch.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Generator[Database, None, None]:
    d = Database(tmp_path / "test.db")
    d.connect()
    d.init_schema()
    yield d
    d.close()


def test_init_schema_creates_tables(db: Database):
    tables = db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    names = [r["name"] for r in tables]
    assert "devices" in names
    assert "downtime_events" in names
    assert "usage_records" in names
    assert "maintenance_records" in names
    assert "alert_rules" in names
    assert "alert_history" in names


def test_insert_and_query(db: Database):
    db.execute(
        "INSERT INTO devices (name, manufacturer) VALUES (?, ?)",
        ("CT1", "Siemens"),
    )
    db.commit()
    row = db.fetchone("SELECT * FROM devices WHERE name = ?", ("CT1",))
    assert row is not None
    assert row["manufacturer"] == "Siemens"


def test_row_to_dict(db: Database):
    db.execute("INSERT INTO devices (name) VALUES (?)", ("MRI1",))
    db.commit()
    row = db.fetchone("SELECT * FROM devices WHERE name = ?", ("MRI1",))
    assert row is not None
    d = db.row_to_dict(row)
    assert d is not None
    assert d["name"] == "MRI1"


def test_row_to_dict_none(db: Database):
    assert db.row_to_dict_or_none(None) is None


def test_commit(db: Database):
    db.execute("INSERT INTO devices (name) VALUES (?)", ("XRAY1",))
    db.commit()
    row = db.fetchone("SELECT COUNT(*) as cnt FROM devices")
    assert row is not None
    assert row["cnt"] == 1
