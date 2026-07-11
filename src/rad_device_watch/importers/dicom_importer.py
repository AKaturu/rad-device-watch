from __future__ import annotations

import logging
from pathlib import Path

from rad_device_watch.models import Device

logger = logging.getLogger(__name__)

DICOM_DEVICE_TAGS = {
    "manufacturer": (0x0008, 0x0070),
    "station_name": (0x0008, 0x1010),
    "model": (0x0008, 0x1090),
    "device_serial_number": (0x0018, 0x1000),
    "software_version": (0x0018, 0x1020),
    "institution_name": (0x0008, 0x0080),
    "department": (0x0008, 0x1040),
    "modality": (0x0008, 0x0060),
    "install_date": (0x0018, 0x1205),
    "manufacture_date": (0x0018, 0x1204),
}


def extract_device_from_dicom(filepath: str | Path) -> Device | None:
    try:
        import pydicom
    except ImportError:
        logger.error("pydicom is required for DICOM import. Install with: pip install pydicom")
        return None

    try:
        ds = pydicom.dcmread(str(filepath), stop_before_pixels=True)
    except Exception as exc:
        logger.warning("Failed to read DICOM file %s: %s", filepath, exc)
        return None

    manufacturer = _get_tag(ds, 0x0008, 0x0070)
    model = _get_tag(ds, 0x0008, 0x1090)
    serial = _get_tag(ds, 0x0018, 0x1000)
    station = _get_tag(ds, 0x0008, 0x1010)
    modality = _get_tag(ds, 0x0008, 0x0060)
    sw_version = _get_tag(ds, 0x0018, 0x1020)
    institution = _get_tag(ds, 0x0008, 0x0080)
    department = _get_tag(ds, 0x0008, 0x1040)
    install_date = _get_tag(ds, 0x0018, 0x1205)
    mfg_date = _get_tag(ds, 0x0018, 0x1204)

    if not station and not serial and not manufacturer:
        return None

    device_name = station or f"{manufacturer or 'Unknown'} {model or ''}".strip()

    return Device(
        name=device_name,
        manufacturer=manufacturer,
        model=model,
        serial_number=serial,
        station_name=station,
        modality=modality,
        location=institution,
        department=department,
        software_version=sw_version,
        install_date=install_date,
        manufacture_date=mfg_date,
    )


def extract_devices_from_directory(
    directory: str | Path,
    recursive: bool = True,
) -> list[Device]:
    path = Path(directory)
    if not path.is_dir():
        logger.error("Directory not found: %s", directory)
        return []

    pattern = "**/*" if recursive else "*"
    seen: set[str] = set()
    devices: list[Device] = []
    files_processed = 0

    for fpath in path.glob(pattern):
        if not fpath.is_file():
            continue
        ext = fpath.suffix.lower()
        if ext not in (".dcm", ".dicom", ""):
            continue

        device = extract_device_from_dicom(fpath)
        files_processed += 1
        if device is None:
            continue

        key = device.serial_number or device.station_name or device.name
        if key and key not in seen:
            seen.add(key)
            devices.append(device)

    logger.info(
        "Processed %d DICOM files, extracted %d unique devices",
        files_processed,
        len(devices),
    )
    return devices


def extract_usage_from_dicom(
    filepath: str | Path,
) -> dict | None:
    try:
        import pydicom
    except ImportError:
        logger.error("pydicom is required")
        return None

    try:
        ds = pydicom.dcmread(str(filepath), stop_before_pixels=True)
    except Exception:
        return None

    station = _get_tag(ds, 0x0008, 0x1010)
    modality = _get_tag(ds, 0x0008, 0x0060)
    study_date = _get_tag(ds, 0x0008, 0x0020)

    if not station:
        return None

    return {
        "station_name": station,
        "modality": modality,
        "study_date": study_date or "unknown",
    }


def _get_tag(ds, group: int, elem: int) -> str | None:
    try:
        val = ds[group, elem].value
        if isinstance(val, bytes):
            val = val.decode("utf-8", errors="replace")
        if isinstance(val, (list, tuple)):
            return "\\".join(str(v) for v in val)
        return str(val).strip() if val else None
    except (KeyError, AttributeError, ValueError):
        return None
