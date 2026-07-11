from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from rad_device_watch.database import Database
from rad_device_watch.device_manager import DeviceManager
from rad_device_watch.maintenance import MaintenanceManager
from rad_device_watch.models import Device, MaintenanceRecord, MaintenanceType


@pytest.fixture
def db(tmp_path: Path) -> Generator[Database, None, None]:
    database = Database(tmp_path / "test.db")
    database.connect()
    database.init_schema()
    yield database
    database.close()


def test_maintenance_lifecycle(db: Database) -> None:
    device_id = DeviceManager(db).add(Device(name="CT1"))
    manager = MaintenanceManager(db)

    record_id = manager.add(
        MaintenanceRecord(
            device_id=device_id,
            maintenance_type=MaintenanceType.preventive,
            scheduled_date="2026-02-01",
            description="Annual preventive maintenance",
        )
    )

    assert manager.get(record_id) is not None
    assert [record.id for record in manager.list_records(pending_only=True)] == [record_id]
    assert manager.complete(record_id, "2026-02-02") is True
    assert manager.list_records(pending_only=True) == []
    assert manager.delete(record_id) is True
    assert manager.get(record_id) is None


def test_maintenance_rejects_unknown_device(db: Database) -> None:
    with pytest.raises(ValueError, match="not found"):
        MaintenanceManager(db).add(
            MaintenanceRecord(
                device_id=999,
                maintenance_type=MaintenanceType.corrective,
            )
        )
