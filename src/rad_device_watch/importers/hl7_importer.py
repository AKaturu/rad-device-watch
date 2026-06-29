from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rad_device_watch.models import Device, UsageRecord

logger = logging.getLogger(__name__)


def _get_field(segment: Any, index: int) -> str | None:
    try:
        val = segment[index].value
        if isinstance(val, str) and val.strip():
            return val.strip()
        return None
    except (IndexError, AttributeError, ValueError):
        return None


def _get_component(segment: Any, field_idx: int, comp_idx: int) -> str | None:
    try:
        field = segment[field_idx]
        val = field[comp_idx].value
        if isinstance(val, str) and val.strip():
            return val.strip()
        return None
    except (IndexError, AttributeError, ValueError):
        return None


def _get_date(dt_val: str | None) -> str | None:
    if not dt_val or len(dt_val) < 8:
        return None
    return f"{dt_val[:4]}-{dt_val[4:6]}-{dt_val[6:8]}"


def parse_hl7_message(raw: str) -> dict | None:
    try:
        from hl7apy.parser import parse_message
    except ImportError:
        logger.error(
            "hl7apy is required for HL7 import. Install with: pip install hl7apy"
        )
        return None

    try:
        msg = parse_message(raw)
    except Exception as exc:
        logger.warning("Failed to parse HL7 message: %s", exc)
        return None

    result: dict[str, Any] = {
        "message_type": None,
        "device_name": None,
        "station_name": None,
        "modality": None,
        "patient_id": None,
        "study_date": None,
    }

    msh = msg.msh
    if msh:
        msg_type = _get_field(msh, 8)
        result["message_type"] = msg_type

    for segment in msg.children:
        name = segment.name.upper() if hasattr(segment, "name") else ""

        if name == "OBR":
            result["station_name"] = _get_field(segment, 15)
            result["modality"] = _get_field(segment, 24)
            if not result["device_name"]:
                result["device_name"] = _get_field(segment, 18)

        elif name == "OBX":
            pass

        elif name == "PID":
            result["patient_id"] = _get_field(segment, 2)

        elif name == "ZDS" or "Z" in name:
            result["device_name"] = result["device_name"] or _get_field(segment, 1)

    return result


def extract_device_from_hl7(raw: str) -> Device | None:
    parsed = parse_hl7_message(raw)
    if not parsed:
        return None

    name = parsed.get("device_name") or parsed.get("station_name")
    if not name:
        return None

    return Device(
        name=name,
        station_name=parsed.get("station_name"),
        modality=parsed.get("modality"),
    )


def extract_usage_from_hl7(raw: str) -> UsageRecord | None:
    parsed = parse_hl7_message(raw)
    if not parsed:
        return None

    station = parsed.get("station_name") or parsed.get("device_name")
    if not station:
        return None

    date_str = parsed.get("study_date") or "unknown"
    logger.warning(
        "Device resolution failed for station '%s' — using device_id=0 placeholder. "
        "Implement a lookup from station/device name to a known device ID.",
        station,
    )
    return UsageRecord(
        device_id=0,
        procedure_date=date_str,
        procedure_count=1,
        modality=parsed.get("modality"),
        source="hl7",
    )


def import_hl7_directory(directory: str | Path) -> list[dict]:
    path = Path(directory)
    if not path.is_dir():
        logger.error("Directory not found: %s", directory)
        return []

    results: list[dict] = []
    for fpath in path.glob("*"):
        if not fpath.is_file():
            continue
        try:
            raw = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        parsed = parse_hl7_message(raw)
        if parsed:
            parsed["_file"] = str(fpath)
            results.append(parsed)

    logger.info("Processed %d HL7 files from %s", len(results), directory)
    return results
