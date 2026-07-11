import pytest

from rad_device_watch.database import Database
from rad_device_watch.device_manager import DeviceManager
from rad_device_watch.downtime import DowntimeTracker
from rad_device_watch.models import CauseCategory, Device, DowntimeEvent, ImpactLevel


@pytest.fixture
def dev_id(db: Database) -> int:
    dm = DeviceManager(db)
    return dm.add(Device(name="TestDevice"))


@pytest.fixture
def tracker(db: Database) -> DowntimeTracker:
    return DowntimeTracker(db)


def test_log_event(tracker: DowntimeTracker, dev_id: int):
    eid = tracker.log_event(
        DowntimeEvent(
            device_id=dev_id,
            start_time="2026-01-01 08:00:00",
            end_time="2026-01-01 10:00:00",
            cause_category=CauseCategory.hardware,
            impact_level=ImpactLevel.high,
        )
    )
    assert eid > 0


def test_get_event(tracker: DowntimeTracker, dev_id: int):
    eid = tracker.log_event(
        DowntimeEvent(device_id=dev_id, start_time="2026-01-01 12:00:00")
    )
    event = tracker.get_event(eid)
    assert event is not None
    assert event.device_id == dev_id


def test_get_event_not_found(tracker: DowntimeTracker):
    assert tracker.get_event(9999) is None


def test_list_events(tracker: DowntimeTracker, dev_id: int):
    for i in range(3):
        tracker.log_event(
            DowntimeEvent(
                device_id=dev_id,
                start_time=f"2026-01-0{i+1} 08:00:00",
            )
        )
    events = tracker.list_events(device_id=dev_id, limit=10)
    assert len(events) == 3


def test_delete_event(tracker: DowntimeTracker, dev_id: int):
    eid = tracker.log_event(
        DowntimeEvent(device_id=dev_id, start_time="2026-01-01 08:00:00")
    )
    assert tracker.delete_event(eid) is True
    assert tracker.get_event(eid) is None


def test_compute_uptime(tracker: DowntimeTracker, dev_id: int):
    tracker.log_event(
        DowntimeEvent(
            device_id=dev_id,
            start_time="2026-01-01 08:00:00",
            end_time="2026-01-01 10:00:00",
        )
    )
    report = tracker.compute_uptime(dev_id, "2026-01-01 00:00:00", "2026-01-02 00:00:00")
    assert report.device_id == dev_id
    assert report.total_minutes == 1440.0
    assert report.downtime_minutes == 120.0
    assert report.uptime_minutes == 1320.0
    assert report.uptime_pct == pytest.approx(91.67, rel=0.01)


def test_compute_uptime_merges_overlapping_events(tracker: DowntimeTracker, dev_id: int):
    tracker.log_event(
        DowntimeEvent(
            device_id=dev_id,
            start_time="2026-01-01 08:00:00",
            end_time="2026-01-01 10:00:00",
        )
    )
    tracker.log_event(
        DowntimeEvent(
            device_id=dev_id,
            start_time="2026-01-01 09:00:00",
            end_time="2026-01-01 11:00:00",
        )
    )

    report = tracker.compute_uptime(
        dev_id, "2026-01-01 00:00:00", "2026-01-02 00:00:00"
    )

    assert report.downtime_minutes == 180.0


def test_compute_uptime_clips_period_and_counts_open_event(
    tracker: DowntimeTracker, dev_id: int
):
    tracker.log_event(
        DowntimeEvent(
            device_id=dev_id,
            start_time="2025-12-31 23:00:00",
            end_time="2026-01-01 01:00:00",
        )
    )
    tracker.log_event(
        DowntimeEvent(device_id=dev_id, start_time="2026-01-01 12:00:00")
    )

    report = tracker.compute_uptime(
        dev_id, "2026-01-01 00:00:00", "2026-01-02 00:00:00"
    )

    assert report.downtime_minutes == 780.0


def test_compute_uptime_rejects_empty_period(tracker: DowntimeTracker, dev_id: int):
    with pytest.raises(ValueError, match="period_end"):
        tracker.compute_uptime(dev_id, "2026-01-01", "2026-01-01")


def test_log_event_rejects_negative_duration(tracker: DowntimeTracker, dev_id: int):
    with pytest.raises(ValueError, match="end_time"):
        tracker.log_event(
            DowntimeEvent(
                device_id=dev_id,
                start_time="2026-01-01 10:00:00",
                end_time="2026-01-01 09:00:00",
            )
        )


def test_uptime_for_all_devices(tracker: DowntimeTracker, dev_id: int):
    reports = tracker.uptime_for_all_devices("2026-01-01", "2026-01-31")
    assert len(reports) >= 1
