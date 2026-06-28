from collections.abc import Generator
from pathlib import Path

import pytest

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
