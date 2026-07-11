from __future__ import annotations

import numpy as np

from rad_device_watch.database import Database
from rad_device_watch.models import UsageRecord, UsageSummary


class UsageAnalyzer:
    def __init__(self, db: Database):
        self.db = db

    def add_record(self, record: UsageRecord) -> int:
        cur = self.db.execute(
            """INSERT INTO usage_records (device_id, procedure_date, procedure_count,
               modality, department, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                record.device_id,
                record.procedure_date,
                record.procedure_count,
                record.modality,
                record.department,
                record.source,
            ),
        )
        self.db.commit()
        return cur.lastrowid

    def add_records(self, records: list[UsageRecord]) -> int:
        data = [
            (
                r.device_id,
                r.procedure_date,
                r.procedure_count,
                r.modality,
                r.department,
                r.source,
            )
            for r in records
        ]
        self.db.executemany(
            """INSERT INTO usage_records (device_id, procedure_date, procedure_count,
               modality, department, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            data,
        )
        self.db.commit()
        return len(records)

    def list_records(self, device_id: int | None = None, limit: int = 100) -> list[UsageRecord]:
        if device_id:
            rows = self.db.fetchall(
                "SELECT * FROM usage_records WHERE device_id = ? ORDER BY procedure_date DESC LIMIT ?",
                (device_id, limit),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM usage_records ORDER BY procedure_date DESC LIMIT ?",
                (limit,),
            )
        return [UsageRecord(**self.db.row_to_dict(r)) for r in rows]

    def summarize_device(
        self, device_id: int, start_date: str, end_date: str
    ) -> UsageSummary | None:
        dev = self.db.fetchone("SELECT * FROM devices WHERE id = ?", (device_id,))
        if not dev:
            return None

        rows = self.db.fetchall(
            """SELECT procedure_date, SUM(procedure_count) as total
               FROM usage_records
               WHERE device_id = ? AND procedure_date >= ? AND procedure_date <= ?
               GROUP BY procedure_date
               ORDER BY procedure_date""",
            (device_id, start_date, end_date),
        )

        if not rows:
            return UsageSummary(
                device_id=device_id,
                device_name=dev["name"],
                modality=dev["modality"],
                procedure_count=0,
                unique_days=0,
                avg_daily_volume=0.0,
                peak_daily_volume=0,
            )

        counts = [r["total"] for r in rows]
        total = sum(counts)
        unique_days = len(rows)

        summary = UsageSummary(
            device_id=device_id,
            device_name=dev["name"],
            modality=dev["modality"],
            procedure_count=total,
            unique_days=unique_days,
            avg_daily_volume=round(total / unique_days, 1),
            peak_daily_volume=max(counts),
        )

        if len(counts) >= 4:
            half = len(counts) // 2
            first_half = np.mean(counts[:half])
            second_half = np.mean(counts[half:])
            if second_half > first_half * 1.1:
                summary.trend_direction = "increasing"
            elif second_half < first_half * 0.9:
                summary.trend_direction = "decreasing"
            else:
                summary.trend_direction = "stable"

        return summary

    def summarize_all(self, start_date: str, end_date: str) -> list[UsageSummary]:
        dev_rows = self.db.fetchall("SELECT id FROM devices ORDER BY name")
        summaries = []
        for dr in dev_rows:
            s = self.summarize_device(dr["id"], start_date, end_date)
            if s:
                summaries.append(s)
        return summaries

    def total_procedures(self, start_date: str, end_date: str) -> int:
        row = self.db.fetchone(
            """SELECT COALESCE(SUM(procedure_count), 0) as total
               FROM usage_records
               WHERE procedure_date >= ? AND procedure_date <= ?""",
            (start_date, end_date),
        )
        return row["total"] if row else 0
