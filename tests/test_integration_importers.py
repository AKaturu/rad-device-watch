from __future__ import annotations

from types import SimpleNamespace

from rad_device_watch.importers import hl7_importer
from rad_device_watch.importers.mpps_poller import MppsPoller


def _parsed_hl7() -> dict[str, str | None]:
    return {
        "station_name": "CT_ROOM_1",
        "device_name": None,
        "modality": "CT",
        "study_date": "2026-01-02",
    }


def test_hl7_usage_requires_resolved_device(monkeypatch) -> None:
    monkeypatch.setattr(hl7_importer, "parse_hl7_message", lambda _raw: _parsed_hl7())

    assert hl7_importer.extract_usage_from_hl7("message") is None
    assert (
        hl7_importer.extract_usage_from_hl7("message", resolve_device_id=lambda _station: None)
        is None
    )


def test_hl7_usage_uses_resolved_device_id(monkeypatch) -> None:
    monkeypatch.setattr(hl7_importer, "parse_hl7_message", lambda _raw: _parsed_hl7())

    record = hl7_importer.extract_usage_from_hl7(
        "message", resolve_device_id=lambda station: 17 if station == "CT_ROOM_1" else None
    )

    assert record is not None
    assert record.device_id == 17
    assert record.procedure_date == "2026-01-02"


def _mpps_dataset() -> SimpleNamespace:
    return SimpleNamespace(
        PerformedStationName="MR_ROOM_2",
        PerformedProcedureStepStatus="COMPLETED",
        PerformedProcedureStepStartDate="20260103",
        Modality="MR",
    )


def test_mpps_usage_requires_resolved_device() -> None:
    assert MppsPoller()._usage_record(_mpps_dataset()) is None
    assert MppsPoller(device_resolver=lambda _station: None)._usage_record(_mpps_dataset()) is None


def test_mpps_usage_uses_resolved_device_id() -> None:
    poller = MppsPoller(device_resolver=lambda station: 23 if station == "MR_ROOM_2" else None)

    record = poller._usage_record(_mpps_dataset())

    assert record is not None
    assert record.device_id == 23
    assert record.procedure_date == "2026-01-03"
