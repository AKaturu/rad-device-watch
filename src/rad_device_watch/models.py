from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class DeviceStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    retired = "retired"


class ImpactLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CauseCategory(StrEnum):
    hardware = "hardware"
    software = "software"
    calibration = "calibration"
    network = "network"
    power = "power"
    environmental = "environmental"
    other = "other"


class MaintenanceType(StrEnum):
    preventive = "preventive"
    corrective = "corrective"
    calibration = "calibration"


class AlertMetric(StrEnum):
    downtime_duration = "downtime_duration"
    uptime_pct = "uptime_pct"
    usage_volume = "usage_volume"


class AlertCondition(StrEnum):
    gt = "gt"
    lt = "lt"
    eq = "eq"


class AlertChannel(StrEnum):
    console = "console"
    email = "email"
    slack = "slack"
    webhook = "webhook"


class Device(BaseModel):
    id: int | None = None
    name: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    station_name: str | None = None
    modality: str | None = None
    location: str | None = None
    department: str | None = None
    software_version: str | None = None
    install_date: str | None = None
    manufacture_date: str | None = None
    status: DeviceStatus = DeviceStatus.active
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DowntimeEvent(BaseModel):
    id: int | None = None
    device_id: int
    start_time: str
    end_time: str | None = None
    duration_minutes: float | None = None
    cause_category: CauseCategory | None = None
    cause_detail: str | None = None
    impact_level: ImpactLevel | None = None
    created_by: str = "manual"
    created_at: str | None = None


class UsageRecord(BaseModel):
    id: int | None = None
    device_id: int
    procedure_date: str
    procedure_count: int = 1
    modality: str | None = None
    department: str | None = None
    source: str = "manual"
    created_at: str | None = None


class MaintenanceRecord(BaseModel):
    id: int | None = None
    device_id: int
    maintenance_type: MaintenanceType
    scheduled_date: str | None = None
    completed_date: str | None = None
    description: str | None = None
    vendor: str | None = None
    cost: float | None = None
    created_at: str | None = None


class AlertRule(BaseModel):
    id: int | None = None
    name: str
    metric: AlertMetric
    condition: AlertCondition
    threshold: float
    channel: AlertChannel = AlertChannel.console
    channel_config: str | None = None
    enabled: bool = True
    created_at: str | None = None


class AlertHistory(BaseModel):
    id: int | None = None
    alert_rule_id: int | None = None
    device_id: int | None = None
    triggered_at: str
    message: str
    channel: str | None = None
    acknowledged: bool = False
    acknowledged_at: str | None = None
    created_at: str | None = None


class UptimeReport(BaseModel):
    device_id: int
    device_name: str
    period_start: str
    period_end: str
    total_minutes: float
    downtime_minutes: float
    uptime_minutes: float
    uptime_pct: float


class UsageSummary(BaseModel):
    device_id: int
    device_name: str
    modality: str | None = None
    procedure_count: int
    unique_days: int
    avg_daily_volume: float
    peak_daily_volume: int
    trend_direction: str | None = None
