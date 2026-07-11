from __future__ import annotations

from rad_device_watch.database import Database
from rad_device_watch.models import MaintenanceRecord


class MaintenanceManager:
    def __init__(self, db: Database):
        self.db = db

    def add(self, record: MaintenanceRecord) -> int:
        if self.db.fetchone("SELECT 1 FROM devices WHERE id = ?", (record.device_id,)) is None:
            raise ValueError(f"Device {record.device_id} not found")
        cursor = self.db.execute(
            """INSERT INTO maintenance_records
               (device_id, maintenance_type, scheduled_date, completed_date,
                description, vendor, cost)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                record.device_id,
                record.maintenance_type.value,
                record.scheduled_date,
                record.completed_date,
                record.description,
                record.vendor,
                record.cost,
            ),
        )
        self.db.commit()
        return cursor.lastrowid

    def get(self, record_id: int) -> MaintenanceRecord | None:
        row = self.db.row_to_dict_or_none(
            self.db.fetchone("SELECT * FROM maintenance_records WHERE id = ?", (record_id,))
        )
        return MaintenanceRecord(**row) if row else None

    def list_records(
        self,
        *,
        device_id: int | None = None,
        pending_only: bool = False,
        limit: int = 100,
    ) -> list[MaintenanceRecord]:
        clauses: list[str] = []
        params: list[object] = []
        if device_id is not None:
            clauses.append("device_id = ?")
            params.append(device_id)
        if pending_only:
            clauses.append("completed_date IS NULL")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = self.db.fetchall(
            f"SELECT * FROM maintenance_records{where} ORDER BY scheduled_date DESC, id DESC LIMIT ?",
            tuple(params),
        )
        return [MaintenanceRecord(**self.db.row_to_dict(row)) for row in rows]

    def complete(self, record_id: int, completed_date: str) -> bool:
        cursor = self.db.execute(
            "UPDATE maintenance_records SET completed_date = ? WHERE id = ?",
            (completed_date, record_id),
        )
        self.db.commit()
        return cursor.rowcount > 0

    def delete(self, record_id: int) -> bool:
        cursor = self.db.execute("DELETE FROM maintenance_records WHERE id = ?", (record_id,))
        self.db.commit()
        return cursor.rowcount > 0
