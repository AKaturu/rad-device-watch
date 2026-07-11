import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import rad_device_watch.alerts.engine as engine_module
from rad_device_watch.alerts.channels import (
    ConsoleChannel,
    get_channel,
)
from rad_device_watch.alerts.engine import AlertEngine
from rad_device_watch.database import Database
from rad_device_watch.device_manager import DeviceManager
from rad_device_watch.models import (
    AlertChannel,
    AlertCondition,
    AlertMetric,
    AlertRule,
    Device,
)


@pytest.fixture
def db(tmp_path: Path) -> Generator[Database, None, None]:
    d = Database(tmp_path / "test.db")
    d.connect()
    d.init_schema()
    yield d
    d.close()


@pytest.fixture
def engine(db: Database) -> AlertEngine:
    return AlertEngine(db)


def test_add_rule(engine: AlertEngine):
    rid = engine.add_rule(
        AlertRule(
            name="High Downtime",
            metric=AlertMetric.downtime_duration,
            condition=AlertCondition.gt,
            threshold=120.0,
            channel=AlertChannel.console,
        )
    )
    assert rid > 0


def test_list_rules(engine: AlertEngine):
    engine.add_rule(
        AlertRule(
            name="Rule1",
            metric=AlertMetric.uptime_pct,
            condition=AlertCondition.lt,
            threshold=95.0,
        )
    )
    engine.add_rule(
        AlertRule(
            name="Rule2",
            metric=AlertMetric.usage_volume,
            condition=AlertCondition.gt,
            threshold=100.0,
            enabled=False,
        )
    )
    all_rules = engine.list_rules()
    assert len(all_rules) == 2
    enabled = engine.list_rules(enabled_only=True)
    assert len(enabled) == 1


def test_get_rule(engine: AlertEngine):
    rid = engine.add_rule(
        AlertRule(
            name="Test",
            metric=AlertMetric.downtime_duration,
            condition=AlertCondition.gt,
            threshold=60.0,
        )
    )
    rule = engine.get_rule(rid)
    assert rule is not None
    assert rule.name == "Test"
    assert rule.threshold == 60.0


def test_get_rule_not_found(engine: AlertEngine):
    assert engine.get_rule(9999) is None


def test_delete_rule(engine: AlertEngine):
    rid = engine.add_rule(
        AlertRule(
            name="DeleteMe",
            metric=AlertMetric.downtime_duration,
            condition=AlertCondition.gt,
            threshold=60.0,
        )
    )
    assert engine.delete_rule(rid) is True
    assert engine.get_rule(rid) is None


def test_console_channel():
    ch = ConsoleChannel()
    assert ch.send("test message") is True


def test_get_channel_console():
    ch = get_channel("console")
    assert isinstance(ch, ConsoleChannel)


def test_get_channel_unknown():
    ch = get_channel("nonexistent")
    assert isinstance(ch, ConsoleChannel)


def test_poll_no_rules(engine: AlertEngine, db: Database):
    dm = DeviceManager(db)
    dm.add(Device(name="TestDev"))
    triggered = engine.poll()
    assert triggered == []


def test_poll_with_rules(engine: AlertEngine, db: Database):
    from datetime import datetime, timedelta

    dm = DeviceManager(db)
    dev_id = dm.add(Device(name="CT1"))
    engine.add_rule(
        AlertRule(
            name="High Downtime",
            metric=AlertMetric.downtime_duration,
            condition=AlertCondition.gt,
            threshold=0.0,
        )
    )
    from rad_device_watch.downtime import DowntimeTracker
    from rad_device_watch.models import DowntimeEvent

    now = datetime.now()
    start = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")

    dt = DowntimeTracker(db)
    dt.log_event(
        DowntimeEvent(
            device_id=dev_id,
            start_time=start,
            end_time=end,
        )
    )
    triggered = engine.poll()
    assert len(triggered) >= 1
    assert triggered[0].alert_rule_id is not None


def test_add_rule_rejects_plaintext_smtp_password(engine: AlertEngine):
    with pytest.raises(ValueError, match="password_env"):
        engine.add_rule(
            AlertRule(
                name="Email",
                metric=AlertMetric.usage_volume,
                condition=AlertCondition.gt,
                threshold=1,
                channel=AlertChannel.email,
                channel_config=json.dumps({"password": "do-not-store"}),
            )
        )


def test_poll_commits_once_for_multiple_alerts(
    engine: AlertEngine, db: Database, monkeypatch
):
    DeviceManager(db).add(Device(name="CT1"))
    for name in ("Rule 1", "Rule 2"):
        engine.add_rule(
            AlertRule(
                name=name,
                metric=AlertMetric.usage_volume,
                condition=AlertCondition.gt,
                threshold=-1,
            )
        )
    channel = MagicMock()
    channel.send.return_value = True
    monkeypatch.setattr(engine_module, "get_channel", lambda _name: channel)
    commit = MagicMock(wraps=db.commit)
    monkeypatch.setattr(db, "commit", commit)

    triggered = engine.poll()

    assert len(triggered) == 2
    commit.assert_called_once_with()


def test_poll_rolls_back_all_history_when_delivery_raises(
    engine: AlertEngine, db: Database, monkeypatch
):
    manager = DeviceManager(db)
    manager.add(Device(name="CT1"))
    manager.add(Device(name="CT2"))
    engine.add_rule(
        AlertRule(
            name="Always",
            metric=AlertMetric.usage_volume,
            condition=AlertCondition.gt,
            threshold=-1,
        )
    )
    channel = MagicMock()
    channel.send.side_effect = [True, RuntimeError("delivery failed")]
    monkeypatch.setattr(engine_module, "get_channel", lambda _name: channel)

    with pytest.raises(RuntimeError, match="delivery failed"):
        engine.poll()

    row = db.fetchone("SELECT COUNT(*) AS count FROM alert_history")
    assert row is not None
    assert row["count"] == 0


def test_acknowledge_alert_history(engine: AlertEngine, db: Database):
    cursor = db.execute(
        """INSERT INTO alert_history (triggered_at, message, channel)
           VALUES (?, ?, ?)""",
        ("2026-01-01 12:00:00", "Review device", "console"),
    )
    db.commit()

    assert engine.acknowledge(cursor.lastrowid, "2026-01-01 13:00:00") is True
    history = engine.get_history()
    assert history[0].acknowledged is True
    assert history[0].acknowledged_at == "2026-01-01 13:00:00"
    assert engine.acknowledge(9999) is False
