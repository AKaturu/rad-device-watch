from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from rad_device_watch.cli import app
from rad_device_watch.database import Database

runner = CliRunner()


def _invoke(db_path: Path, *args: str):
    return runner.invoke(app, [*args, "--db", str(db_path)])


def test_device_update_and_downtime_delete_commands(tmp_path: Path) -> None:
    db_path = tmp_path / "watch.db"
    added = _invoke(db_path, "device-add", "CT1", "--station", "CT_ROOM_1")
    updated = _invoke(
        db_path,
        "device-update",
        "1",
        "--name",
        "CT Updated",
        "--status",
        "inactive",
    )
    logged = _invoke(
        db_path,
        "downtime-log",
        "1",
        "--start",
        "2026-01-01 08:00:00",
        "--end",
        "2026-01-01 09:00:00",
    )
    deleted = _invoke(db_path, "downtime-delete", "1")

    assert added.exit_code == 0, added.output
    assert updated.exit_code == 0, updated.output
    assert logged.exit_code == 0, logged.output
    assert deleted.exit_code == 0, deleted.output
    with Database(db_path) as db:
        device = db.fetchone("SELECT name, status FROM devices WHERE id = 1")
        assert device is not None
        assert device["name"] == "CT Updated"
        assert device["status"] == "inactive"
        assert db.fetchone("SELECT id FROM downtime_events WHERE id = 1") is None


def test_maintenance_commands_cover_full_lifecycle(tmp_path: Path) -> None:
    db_path = tmp_path / "watch.db"
    assert _invoke(db_path, "device-add", "MR1").exit_code == 0

    added = _invoke(
        db_path,
        "maintenance-add",
        "1",
        "--type",
        "preventive",
        "--scheduled",
        "2026-02-01",
        "--vendor",
        "Service Co",
    )
    listed = _invoke(db_path, "maintenance-list", "--pending")
    completed = _invoke(
        db_path, "maintenance-complete", "1", "--date", "2026-02-02"
    )
    deleted = _invoke(db_path, "maintenance-delete", "1")

    assert added.exit_code == 0, added.output
    assert listed.exit_code == 0, listed.output
    assert "preventive" in listed.output
    assert completed.exit_code == 0, completed.output
    assert deleted.exit_code == 0, deleted.output


def test_alert_acknowledge_and_delete_commands(tmp_path: Path) -> None:
    db_path = tmp_path / "watch.db"
    rule = _invoke(
        db_path,
        "alert-add",
        "Usage spike",
        "--metric",
        "usage_volume",
        "--condition",
        "gt",
        "--threshold",
        "10",
    )
    assert rule.exit_code == 0, rule.output

    with Database(db_path) as db:
        db.init_schema()
        cursor = db.execute(
            """INSERT INTO alert_history
               (alert_rule_id, triggered_at, message, channel)
               VALUES (?, ?, ?, ?)""",
            (1, "2026-01-01 12:00:00", "Review device", "console"),
        )
        db.commit()
        history_id = cursor.lastrowid

    acknowledged = _invoke(db_path, "alert-acknowledge", str(history_id))
    deleted = _invoke(db_path, "alert-delete", "1")

    assert acknowledged.exit_code == 0, acknowledged.output
    assert deleted.exit_code == 0, deleted.output
    with Database(db_path) as db:
        history = db.fetchone(
            "SELECT acknowledged, acknowledged_at FROM alert_history WHERE id = ?",
            (history_id,),
        )
        assert history is not None
        assert history["acknowledged"] == 1
        assert history["acknowledged_at"]
        assert db.fetchone("SELECT id FROM alert_rules WHERE id = 1") is None
        retained = db.fetchone("SELECT alert_rule_id FROM alert_history WHERE id = ?", (history_id,))
        assert retained is not None
        assert retained["alert_rule_id"] is None


def test_alert_add_rejects_plaintext_password_config(tmp_path: Path) -> None:
    result = _invoke(
        tmp_path / "watch.db",
        "alert-add",
        "Email",
        "--metric",
        "usage_volume",
        "--condition",
        "gt",
        "--threshold",
        "10",
        "--channel",
        "email",
        "--config",
        '{"password":"secret"}',
    )

    assert result.exit_code == 1
    assert "password_env" in result.output
