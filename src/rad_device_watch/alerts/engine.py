from __future__ import annotations

import contextlib
import json
import logging
from datetime import datetime, timedelta

from rad_device_watch.alerts.channels import get_channel
from rad_device_watch.database import Database
from rad_device_watch.models import AlertHistory, AlertMetric, AlertRule

logger = logging.getLogger(__name__)


class AlertEngine:
    def __init__(self, db: Database):
        self.db = db

    def add_rule(self, rule: AlertRule) -> int:
        cur = self.db.execute(
            """INSERT INTO alert_rules (name, metric, condition, threshold, channel, channel_config, enabled)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                rule.name,
                rule.metric.value,
                rule.condition.value,
                rule.threshold,
                rule.channel.value,
                rule.channel_config,
                1 if rule.enabled else 0,
            ),
        )
        self.db.commit()
        return cur.lastrowid

    def list_rules(self, enabled_only: bool = False) -> list[AlertRule]:
        if enabled_only:
            rows = self.db.fetchall(
                "SELECT * FROM alert_rules WHERE enabled = 1 ORDER BY name"
            )
        else:
            rows = self.db.fetchall("SELECT * FROM alert_rules ORDER BY name")
        return [AlertRule(**self.db.row_to_dict(r)) for r in rows]

    def get_rule(self, rule_id: int) -> AlertRule | None:
        d = self.db.row_to_dict_or_none(
            self.db.fetchone(
                "SELECT * FROM alert_rules WHERE id = ?", (rule_id,)
            )
        )
        return AlertRule(**d) if d else None

    def delete_rule(self, rule_id: int) -> bool:
        cur = self.db.execute(
            "DELETE FROM alert_rules WHERE id = ?", (rule_id,)
        )
        self.db.commit()
        return cur.rowcount > 0

    def _get_metric_value(
        self, metric: AlertMetric, device_id: int
    ) -> float:
        now = datetime.now()
        if metric == AlertMetric.downtime_duration:
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            row = self.db.fetchone(
                """SELECT COALESCE(SUM(duration_minutes), 0) as val
                   FROM downtime_events
                   WHERE device_id = ? AND start_time >= ?""",
                (device_id, week_ago),
            )
            return row["val"] if row else 0.0

        elif metric == AlertMetric.uptime_pct:
            from rad_device_watch.downtime import DowntimeTracker

            tracker = DowntimeTracker(self.db)
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            report = tracker.compute_uptime(device_id, week_ago, now_str)
            return report.uptime_pct

        elif metric == AlertMetric.usage_volume:
            week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            today = now.strftime("%Y-%m-%d")
            row = self.db.fetchone(
                """SELECT COALESCE(SUM(procedure_count), 0) as val
                   FROM usage_records
                   WHERE device_id = ? AND procedure_date >= ? AND procedure_date <= ?""",
                (device_id, week_ago, today),
            )
            return row["val"] if row else 0.0

        return 0.0

    def _evaluate(self, value: float, condition: str, threshold: float) -> bool:
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return abs(value - threshold) < 0.001
        return False

    def poll(self) -> list[AlertHistory]:
        rules = self.list_rules(enabled_only=True)
        devices = self.db.fetchall("SELECT id, name FROM devices")
        triggered: list[AlertHistory] = []

        for rule in rules:
            channel_config = None
            if rule.channel_config:
                with contextlib.suppress(json.JSONDecodeError):
                    channel_config = json.loads(rule.channel_config)

            channel = get_channel(rule.channel.value)

            for dev in devices:
                metric = AlertMetric(rule.metric.value)
                value = self._get_metric_value(metric, dev["id"])

                if self._evaluate(
                    value, rule.condition.value, rule.threshold
                ):
                    message = (
                        f"[{rule.name}] Device '{dev['name']}' triggered: "
                        f"{rule.metric.value} = {value} "
                        f"({rule.condition.value} {rule.threshold})"
                    )

                    channel.send(message, config=channel_config)

                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cur = self.db.execute(
                        """INSERT INTO alert_history (alert_rule_id, device_id,
                           triggered_at, message, channel)
                           VALUES (?, ?, ?, ?, ?)""",
                        (rule.id, dev["id"], now_str, message, rule.channel.value),
                    )
                    ah = AlertHistory(
                        id=cur.lastrowid,
                        alert_rule_id=rule.id,
                        device_id=dev["id"],
                        triggered_at=now_str,
                        message=message,
                        channel=rule.channel.value,
                    )
                    triggered.append(ah)

            if triggered:
                self.db.commit()

        return triggered

    def get_history(
        self, limit: int = 50, device_id: int | None = None
    ) -> list[AlertHistory]:
        if device_id:
            rows = self.db.fetchall(
                "SELECT * FROM alert_history WHERE device_id = ? ORDER BY triggered_at DESC LIMIT ?",
                (device_id, limit),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM alert_history ORDER BY triggered_at DESC LIMIT ?",
                (limit,),
            )
        return [AlertHistory(**self.db.row_to_dict(r)) for r in rows]
