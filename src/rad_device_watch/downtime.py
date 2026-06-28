from __future__ import annotations

from datetime import datetime

from rad_device_watch.database import Database
from rad_device_watch.models import (
    DowntimeEvent,
    UptimeReport,
)


def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {s}")


class DowntimeTracker:
    def __init__(self, db: Database):
        self.db = db

    def log_event(self, event: DowntimeEvent) -> int:
        if event.start_time and event.end_time:
            start = _parse_dt(event.start_time)
            end = _parse_dt(event.end_time)
            event.duration_minutes = (end - start).total_seconds() / 60.0
        cur = self.db.execute(
            """INSERT INTO downtime_events (device_id, start_time, end_time,
               duration_minutes, cause_category, cause_detail, impact_level, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.device_id,
                event.start_time,
                event.end_time,
                event.duration_minutes,
                event.cause_category.value if event.cause_category else None,
                event.cause_detail,
                event.impact_level.value if event.impact_level else None,
                event.created_by,
            ),
        )
        self.db.commit()
        return cur.lastrowid

    def get_event(self, event_id: int) -> DowntimeEvent | None:
        d = self.db.row_to_dict_or_none(
            self.db.fetchone(
                "SELECT * FROM downtime_events WHERE id = ?", (event_id,)
            )
        )
        return DowntimeEvent(**d) if d else None

    def list_events(
        self,
        device_id: int | None = None,
        limit: int = 100,
    ) -> list[DowntimeEvent]:
        if device_id:
            rows = self.db.fetchall(
                "SELECT * FROM downtime_events WHERE device_id = ? ORDER BY start_time DESC LIMIT ?",
                (device_id, limit),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM downtime_events ORDER BY start_time DESC LIMIT ?",
                (limit,),
            )
        return [DowntimeEvent(**self.db.row_to_dict(r)) for r in rows]



    def delete_event(self, event_id: int) -> bool:
        cur = self.db.execute(
            "DELETE FROM downtime_events WHERE id = ?", (event_id,)
        )
        self.db.commit()
        return cur.rowcount > 0

    def compute_uptime(
        self,
        device_id: int,
        period_start: str,
        period_end: str,
    ) -> UptimeReport:
        start_dt = _parse_dt(period_start)
        end_dt = _parse_dt(period_end)
        total_minutes = (end_dt - start_dt).total_seconds() / 60.0

        row = self.db.fetchone(
            """SELECT COALESCE(SUM(duration_minutes), 0) as total_downtime
               FROM downtime_events
               WHERE device_id = ?
                 AND start_time >= ?
                 AND (end_time <= ? OR end_time IS NULL)""",
            (device_id, period_start, period_end),
        )
        downtime_minutes = row["total_downtime"] if row else 0.0
        uptime_minutes = max(total_minutes - downtime_minutes, 0)
        uptime_pct = (uptime_minutes / total_minutes * 100) if total_minutes > 0 else 100.0

        dev_row = self.db.fetchone(
            "SELECT name FROM devices WHERE id = ?", (device_id,)
        )
        device_name = dev_row["name"] if dev_row else "Unknown"

        return UptimeReport(
            device_id=device_id,
            device_name=device_name,
            period_start=period_start,
            period_end=period_end,
            total_minutes=total_minutes,
            downtime_minutes=downtime_minutes,
            uptime_minutes=uptime_minutes,
            uptime_pct=round(uptime_pct, 2),
        )

    def uptime_for_all_devices(
        self,
        period_start: str,
        period_end: str,
    ) -> list[UptimeReport]:
        dev_rows = self.db.fetchall("SELECT id, name FROM devices ORDER BY name")
        reports = []
        for dr in dev_rows:
            report = self.compute_uptime(dr["id"], period_start, period_end)
            reports.append(report)
        return reports
