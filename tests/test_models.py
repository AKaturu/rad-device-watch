from rad_device_watch.models import (
    AlertRule,
    Device,
    DeviceStatus,
    DowntimeEvent,
    UsageRecord,
)


def test_device_defaults():
    d = Device(name="Test")
    assert d.name == "Test"
    assert d.status == DeviceStatus.active
    assert d.id is None


def test_device_with_all_fields():
    d = Device(
        id=1,
        name="CT1",
        manufacturer="Siemens",
        model="SOMATOM Drive",
        serial_number="12345",
        station_name="CT-ROOM-1",
        modality="CT",
        location="Building A",
        department="Radiology",
        software_version="VA60A",
        install_date="2025-01-15",
        manufacture_date="2024-11-01",
        status=DeviceStatus.active,
        notes="Primary CT scanner",
    )
    assert d.manufacturer == "Siemens"
    assert d.modality == "CT"


def test_downtime_event():
    e = DowntimeEvent(device_id=1, start_time="2026-01-01 08:00:00")
    assert e.device_id == 1
    assert e.created_by == "manual"


def test_downtime_event_with_duration():
    e = DowntimeEvent(
        device_id=1,
        start_time="2026-01-01 08:00:00",
        end_time="2026-01-01 10:00:00",
        duration_minutes=120.0,
    )
    assert e.duration_minutes == 120.0


def test_usage_record():
    u = UsageRecord(device_id=1, procedure_date="2026-01-15", procedure_count=5)
    assert u.device_id == 1
    assert u.procedure_count == 5
    assert u.source == "manual"


def test_alert_rule():
    r = AlertRule(
        name="High Downtime",
        metric="downtime_duration",
        condition="gt",
        threshold=120.0,
    )
    assert r.enabled is True
    assert r.channel.value == "console"


def test_enum_values():
    assert DeviceStatus.active.value == "active"
    assert DeviceStatus.inactive.value == "inactive"
    assert DeviceStatus.retired.value == "retired"
