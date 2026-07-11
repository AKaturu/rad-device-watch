from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from rad_device_watch.models import (
    CauseCategory,
    Device,
    DeviceStatus,
    DowntimeEvent,
    ImpactLevel,
    UsageRecord,
)

logger = logging.getLogger(__name__)


def _read_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    ext = p.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(p)
    elif ext in (".xls", ".xlsx"):
        return pd.read_excel(p)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _safe_str(val: Any) -> str | None:
    if pd.isna(val):
        return None
    return str(val).strip()


def _required_str(val: Any, label: str = "value") -> str:
    if pd.isna(val):
        raise ValueError(f"Required field '{label}' is missing or NaN")
    return str(val).strip()


def import_devices(path: str | Path) -> list[Device]:
    df = _read_csv(path)
    required = {"name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    devices: list[Device] = []
    for _, row in df.iterrows():
        status_str = _safe_str(row.get("status")) or "active"
        try:
            status = DeviceStatus(status_str)
        except ValueError:
            status = DeviceStatus.active

        devices.append(
            Device(
                name=_required_str(row["name"], "name"),
                manufacturer=_safe_str(row.get("manufacturer")),
                model=_safe_str(row.get("model")),
                serial_number=_safe_str(row.get("serial_number")),
                station_name=_safe_str(row.get("station_name")),
                modality=_safe_str(row.get("modality")),
                location=_safe_str(row.get("location")),
                department=_safe_str(row.get("department")),
                software_version=_safe_str(row.get("software_version")),
                install_date=_safe_str(row.get("install_date")),
                manufacture_date=_safe_str(row.get("manufacture_date")),
                status=status,
                notes=_safe_str(row.get("notes")),
            )
        )

    return devices


def import_downtime(path: str | Path) -> list[DowntimeEvent]:
    df = _read_csv(path)
    required = {"device_id", "start_time"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    events: list[DowntimeEvent] = []
    for _, row in df.iterrows():
        cause_category_raw = _safe_str(row.get("cause_category"))
        impact_level_raw = _safe_str(row.get("impact_level"))
        events.append(
            DowntimeEvent(
                device_id=int(row["device_id"]),
                start_time=_required_str(row["start_time"], "start_time"),
                end_time=_safe_str(row.get("end_time")),
                duration_minutes=(
                    float(row["duration_minutes"])
                    if "duration_minutes" in df.columns and not pd.isna(row.get("duration_minutes"))
                    else None
                ),
                cause_category=(CauseCategory(cause_category_raw) if cause_category_raw else None),
                cause_detail=_safe_str(row.get("cause_detail")),
                impact_level=(ImpactLevel(impact_level_raw) if impact_level_raw else None),
                created_by=_safe_str(row.get("created_by")) or "csv_import",
            )
        )
    return events


def import_usage(path: str | Path) -> list[UsageRecord]:
    df = _read_csv(path)
    required = {"device_id", "procedure_date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    records: list[UsageRecord] = []
    for _, row in df.iterrows():
        records.append(
            UsageRecord(
                device_id=int(row["device_id"]),
                procedure_date=_required_str(row["procedure_date"], "procedure_date"),
                procedure_count=(
                    int(row["procedure_count"])
                    if "procedure_count" in df.columns and not pd.isna(row.get("procedure_count"))
                    else 1
                ),
                modality=_safe_str(row.get("modality")),
                department=_safe_str(row.get("department")),
                source=_safe_str(row.get("source")) or "csv_import",
            )
        )
    return records
