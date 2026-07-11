from __future__ import annotations

from rad_device_watch.database import Database
from rad_device_watch.models import Device, DeviceStatus


class DeviceManager:
    def __init__(self, db: Database):
        self.db = db

    def add(self, device: Device) -> int:
        cur = self.db.execute(
            """INSERT INTO devices (name, manufacturer, model, serial_number,
               station_name, modality, location, department, software_version,
               install_date, manufacture_date, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                device.name,
                device.manufacturer,
                device.model,
                device.serial_number,
                device.station_name,
                device.modality,
                device.location,
                device.department,
                device.software_version,
                device.install_date,
                device.manufacture_date,
                device.status.value,
                device.notes,
            ),
        )
        self.db.commit()
        return cur.lastrowid

    def get(self, device_id: int) -> Device | None:
        d = self.db.row_to_dict_or_none(
            self.db.fetchone("SELECT * FROM devices WHERE id = ?", (device_id,))
        )
        return Device(**d) if d else None

    def get_by_name(self, name: str) -> Device | None:
        d = self.db.row_to_dict_or_none(
            self.db.fetchone("SELECT * FROM devices WHERE name = ?", (name,))
        )
        return Device(**d) if d else None

    def get_by_serial(self, serial: str) -> Device | None:
        d = self.db.row_to_dict_or_none(
            self.db.fetchone(
                "SELECT * FROM devices WHERE serial_number = ?", (serial,)
            )
        )
        return Device(**d) if d else None

    def resolve_id(self, identifier: str) -> int | None:
        """Resolve a station, device name, or serial number to a device ID."""
        value = identifier.strip()
        if not value:
            return None
        row = self.db.fetchone(
            """SELECT id FROM devices
               WHERE lower(coalesce(station_name, '')) = lower(?)
                  OR lower(name) = lower(?)
                  OR lower(coalesce(serial_number, '')) = lower(?)
               ORDER BY CASE
                   WHEN lower(coalesce(station_name, '')) = lower(?) THEN 0
                   WHEN lower(name) = lower(?) THEN 1
                   ELSE 2
               END, id
               LIMIT 1""",
            (value, value, value, value, value),
        )
        return int(row["id"]) if row else None

    def list_all(self) -> list[Device]:
        rows = self.db.fetchall("SELECT * FROM devices ORDER BY name")
        return [Device(**self.db.row_to_dict(r)) for r in rows]

    def list_by_modality(self, modality: str) -> list[Device]:
        rows = self.db.fetchall(
            "SELECT * FROM devices WHERE modality = ? ORDER BY name", (modality,)
        )
        return [Device(**self.db.row_to_dict(r)) for r in rows]

    def list_by_status(self, status: DeviceStatus) -> list[Device]:
        rows = self.db.fetchall(
            "SELECT * FROM devices WHERE status = ? ORDER BY name", (status.value,)
        )
        return [Device(**self.db.row_to_dict(r)) for r in rows]

    def update(self, device: Device) -> bool:
        cur = self.db.execute(
            """UPDATE devices SET name=?, manufacturer=?, model=?, serial_number=?,
               station_name=?, modality=?, location=?, department=?,
               software_version=?, install_date=?, manufacture_date=?,
               status=?, notes=?, updated_at=datetime('now')
               WHERE id=?""",
            (
                device.name,
                device.manufacturer,
                device.model,
                device.serial_number,
                device.station_name,
                device.modality,
                device.location,
                device.department,
                device.software_version,
                device.install_date,
                device.manufacture_date,
                device.status.value,
                device.notes,
                device.id,
            ),
        )
        self.db.commit()
        return cur.rowcount > 0

    def delete(self, device_id: int) -> bool:
        cur = self.db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        self.db.commit()
        return cur.rowcount > 0

    def count(self) -> int:
        row = self.db.fetchone("SELECT COUNT(*) as cnt FROM devices")
        return row["cnt"] if row else 0

    def modalities(self) -> list[str]:
        rows = self.db.fetchall(
            "SELECT DISTINCT modality FROM devices WHERE modality IS NOT NULL ORDER BY modality"
        )
        return [r["modality"] for r in rows]
