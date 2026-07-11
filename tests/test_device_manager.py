from collections.abc import Generator
from pathlib import Path

import pytest

from rad_device_watch.database import Database
from rad_device_watch.device_manager import DeviceManager
from rad_device_watch.models import Device, DeviceStatus


@pytest.fixture
def db(tmp_path: Path) -> Generator[Database, None, None]:
    d = Database(tmp_path / "test.db")
    d.connect()
    d.init_schema()
    yield d
    d.close()


@pytest.fixture
def dm(db: Database) -> DeviceManager:
    return DeviceManager(db)


def test_add_device(dm: DeviceManager):
    d = Device(name="CT Scanner", manufacturer="Siemens", modality="CT")
    dev_id = dm.add(d)
    assert dev_id > 0


def test_get_device(dm: DeviceManager):
    dev_id = dm.add(Device(name="MRI", serial_number="SN001"))
    fetched = dm.get(dev_id)
    assert fetched is not None
    assert fetched.name == "MRI"
    assert fetched.serial_number == "SN001"


def test_get_device_not_found(dm: DeviceManager):
    assert dm.get(9999) is None


def test_get_by_name(dm: DeviceManager):
    dm.add(Device(name="X-Ray-1"))
    dev = dm.get_by_name("X-Ray-1")
    assert dev is not None
    assert dev.name == "X-Ray-1"


def test_get_by_serial(dm: DeviceManager):
    dm.add(Device(name="CT1", serial_number="SN-CT-001"))
    dev = dm.get_by_serial("SN-CT-001")
    assert dev is not None
    assert dev.name == "CT1"


def test_list_all(dm: DeviceManager):
    dm.add(Device(name="A"))
    dm.add(Device(name="B"))
    all_devs = dm.list_all()
    assert len(all_devs) >= 2


def test_list_by_modality(dm: DeviceManager):
    dm.add(Device(name="CT1", modality="CT"))
    dm.add(Device(name="MRI1", modality="MR"))
    cts = dm.list_by_modality("CT")
    assert all(d.modality == "CT" for d in cts)
    assert len(cts) == 1


def test_list_by_status(dm: DeviceManager):
    dm.add(Device(name="Active1", status=DeviceStatus.active))
    dm.add(Device(name="Inactive1", status=DeviceStatus.inactive))
    active = dm.list_by_status(DeviceStatus.active)
    assert all(d.status == DeviceStatus.active for d in active)


def test_update_device(dm: DeviceManager):
    dev_id = dm.add(Device(name="OldName"))
    updated = Device(id=dev_id, name="NewName")
    result = dm.update(updated)
    assert result is True
    fetched = dm.get(dev_id)
    assert fetched is not None
    assert fetched.name == "NewName"


def test_delete_device(dm: DeviceManager):
    dev_id = dm.add(Device(name="ToDelete"))
    assert dm.delete(dev_id) is True
    assert dm.get(dev_id) is None


def test_delete_nonexistent(dm: DeviceManager):
    assert dm.delete(9999) is False


def test_resolve_id_matches_integration_identifiers(dm: DeviceManager):
    device_id = dm.add(
        Device(name="CT Console", station_name="CT_ROOM_1", serial_number="SN1")
    )

    assert dm.resolve_id("ct_room_1") == device_id
    assert dm.resolve_id("CT CONSOLE") == device_id
    assert dm.resolve_id("sn1") == device_id
    assert dm.resolve_id("unknown") is None


def test_count(dm: DeviceManager):
    dm.add(Device(name="A"))
    dm.add(Device(name="B"))
    assert dm.count() >= 2


def test_modalities(dm: DeviceManager):
    dm.add(Device(name="CT1", modality="CT"))
    dm.add(Device(name="MRI1", modality="MR"))
    mods = dm.modalities()
    assert "CT" in mods
    assert "MR" in mods
