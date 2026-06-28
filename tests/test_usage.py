from pathlib import Path

import pytest

from rad_device_watch.database import Database
from rad_device_watch.device_manager import DeviceManager
from rad_device_watch.models import Device, UsageRecord
from rad_device_watch.usage import UsageAnalyzer


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.connect()
    d.init_schema()
    yield d
    d.close()


@pytest.fixture
def dev_id(db: Database) -> int:
    dm = DeviceManager(db)
    return dm.add(Device(name="UsageDevice", modality="CT"))


@pytest.fixture
def analyzer(db: Database) -> UsageAnalyzer:
    return UsageAnalyzer(db)


def test_add_record(analyzer: UsageAnalyzer, dev_id: int):
    rid = analyzer.add_record(
        UsageRecord(device_id=dev_id, procedure_date="2026-01-15", procedure_count=10)
    )
    assert rid > 0


def test_add_records(analyzer: UsageAnalyzer, dev_id: int):
    records = [
        UsageRecord(device_id=dev_id, procedure_date="2026-01-01", procedure_count=5),
        UsageRecord(device_id=dev_id, procedure_date="2026-01-02", procedure_count=8),
    ]
    count = analyzer.add_records(records)
    assert count == 2


def test_list_records(analyzer: UsageAnalyzer, dev_id: int):
    analyzer.add_record(
        UsageRecord(device_id=dev_id, procedure_date="2026-01-01")
    )
    analyzer.add_record(
        UsageRecord(device_id=dev_id, procedure_date="2026-01-02")
    )
    records = analyzer.list_records(device_id=dev_id)
    assert len(records) == 2


def test_summarize_device(analyzer: UsageAnalyzer, dev_id: int):
    for day in range(1, 11):
        analyzer.add_record(
            UsageRecord(
                device_id=dev_id,
                procedure_date=f"2026-01-{day:02d}",
                procedure_count=day * 5,
            )
        )
    summary = analyzer.summarize_device(dev_id, "2026-01-01", "2026-01-31")
    assert summary is not None
    assert summary.device_id == dev_id
    assert summary.procedure_count == 275
    assert summary.unique_days == 10
    assert summary.avg_daily_volume == 27.5
    assert summary.peak_daily_volume == 50


def test_summarize_device_no_records(analyzer: UsageAnalyzer, dev_id: int):
    summary = analyzer.summarize_device(dev_id, "2026-01-01", "2026-01-31")
    assert summary is not None
    assert summary.procedure_count == 0


def test_summarize_device_not_found(analyzer: UsageAnalyzer):
    assert analyzer.summarize_device(9999, "2026-01-01", "2026-01-31") is None


def test_total_procedures(analyzer: UsageAnalyzer, dev_id: int):
    analyzer.add_record(
        UsageRecord(device_id=dev_id, procedure_date="2026-01-01", procedure_count=10)
    )
    analyzer.add_record(
        UsageRecord(device_id=dev_id, procedure_date="2026-01-02", procedure_count=20)
    )
    assert analyzer.total_procedures("2026-01-01", "2026-01-31") == 30
