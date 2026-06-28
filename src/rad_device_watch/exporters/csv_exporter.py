from __future__ import annotations

import csv
from pathlib import Path


def export_to_csv(data: list[dict], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if not data:
        p.write_text("", encoding="utf-8")
        return p

    fieldnames = list(data[0].keys())
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    return p


def export_devices(db_rows: list[dict], path: str | Path) -> Path:
    fields = [
        "id",
        "name",
        "manufacturer",
        "model",
        "serial_number",
        "station_name",
        "modality",
        "location",
        "department",
        "software_version",
        "install_date",
        "manufacture_date",
        "status",
        "created_at",
        "updated_at",
    ]
    data = [{k: r.get(k, "") for k in fields} for r in db_rows]
    return export_to_csv(data, path)


def export_downtime(db_rows: list[dict], path: str | Path) -> Path:
    fields = [
        "id",
        "device_id",
        "start_time",
        "end_time",
        "duration_minutes",
        "cause_category",
        "cause_detail",
        "impact_level",
        "created_at",
    ]
    data = [{k: r.get(k, "") for k in fields} for r in db_rows]
    return export_to_csv(data, path)


def export_usage(db_rows: list[dict], path: str | Path) -> Path:
    fields = [
        "id",
        "device_id",
        "procedure_date",
        "procedure_count",
        "modality",
        "source",
        "created_at",
    ]
    data = [{k: r.get(k, "") for k in fields} for r in db_rows]
    return export_to_csv(data, path)
