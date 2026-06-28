# rad-device-watch — Architecture

## Overview

A modular CLI + dashboard tool for radiology device monitoring. Follows the same patterns as other projects (Typer CLI, Rich tables, Streamlit dashboard) with SQLite for persistence.

```
CLI ──→ Service Layer ──→ SQLite
                   ↕                   ↕
              Importers          Exporters/Reporters
              (CSV/DICOM/HL7)    (CSV/PDF/Rich)
                   ↕
              Pollers (MPPS/HL7 live)
                   ↕
              Alert Engine → Channels (Email/Slack/Console/Webhook)
```

## Module Structure

```
src/rad_device_watch/
  __init__.py
  models.py                Pydantic models
  database.py              SQLite schema, connection, migrations
  device_manager.py        CRUD for device inventory
  downtime.py              Downtime logging, uptime calculation
  usage.py                 Usage analysis, utilization, trends
  alerts/                  Alert engine
    __init__.py
    engine.py              Rule evaluation, dispatching
    channels.py            Email, Slack, Console, Webhook
  importers/
    __init__.py            Base importer protocol
    csv_importer.py        CSV/Excel → devices/downtime/usage
    dicom_importer.py      DICOM file → device extraction
    hl7_importer.py        HL7 v2 → device/usage extraction
    mpps_poller.py         DICOM MPPS N-GET polling
  exporters/
    __init__.py
    csv_exporter.py        SQLite tables → CSV
  reporter.py              Rich console reports, Jinja2 PDF/HTML
  cli.py                   Typer CLI app
  dashboard.py             Streamlit app
```

## Database Schema (SQLite)

```sql
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    station_name TEXT,
    modality TEXT,
    location TEXT,
    department TEXT,
    software_version TEXT,
    install_date TEXT,
    manufacture_date TEXT,
    status TEXT DEFAULT 'active',   -- active, inactive, retired
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE downtime_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_minutes REAL,
    cause_category TEXT,    -- hardware, software, calibration, network, other
    cause_detail TEXT,
    impact_level TEXT,      -- low, medium, high, critical
    created_by TEXT DEFAULT 'manual',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    procedure_date TEXT NOT NULL,
    procedure_count INTEGER DEFAULT 1,
    modality TEXT,
    department TEXT,
    source TEXT DEFAULT 'manual',  -- dicom, hl7, csv, manual
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE maintenance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    maintenance_type TEXT NOT NULL,  -- preventive, corrective, calibration
    scheduled_date TEXT,
    completed_date TEXT,
    description TEXT,
    vendor TEXT,
    cost REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE alert_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    metric TEXT NOT NULL,         -- downtime_duration, uptime_pct, usage_volume
    condition TEXT NOT NULL,      -- gt, lt, eq
    threshold REAL NOT NULL,
    channel TEXT DEFAULT 'console',  -- console, email, slack, webhook
    channel_config TEXT,          -- JSON with channel-specific config
    enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_rule_id INTEGER REFERENCES alert_rules(id),
    device_id INTEGER REFERENCES devices(id),
    triggered_at TEXT NOT NULL,
    message TEXT NOT NULL,
    channel TEXT,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

## Data Flow

### Import
```
CSV/DICOM files / HL7 messages
  → Importer parses raw data
  → Pydantic model validation
  → SQLite INSERT
  → Rich console confirmation
```

### Query (CLI)
```
CLI command
  → Service function (e.g., get_device, get_uptime)
  → SQL query via sqlite3
  → pandas DataFrame
  → Rich Table output
```

### Live Monitoring
```
MPPS Poller (timer-based)
  → pynetdicom N-GET to retrieve MPPS instances
  → Extract PerformedStationName, status, start/end time
  → Upsert UsageRecords
  → Trigger Alert Engine evaluation
```

### Alert Flow
```
Alert Engine.poll()
  → Load enabled rules from alert_rules
  → Query relevant metric (downtime duration, uptime %, usage volume)
  → Compare against threshold
  → If triggered: dispatch to channel, log to alert_history
```

## Key Interfaces

### Importer Protocol
```python
class Importer(Protocol):
    def import_devices(self, source: str) -> list[Device]: ...
    def import_usage(self, source: str) -> list[UsageRecord]: ...
    def import_downtime(self, source: str) -> list[DowntimeEvent]: ...
```

### Alert Channel Protocol
```python
class AlertChannel(Protocol):
    def send(self, message: str, config: dict | None = None) -> bool: ...
```

## Failure Modes Considered

- **Empty import** → warn + skip, don't crash
- **Duplicate serial numbers** → warn and skip duplicate on import
- **Malformed DICOM files** → pydicom error caught per-file, continue batch
- **MPPS poll failure** → log warning, retry next interval
- **SMTP unavailable** → log error, continue without email
- **HL7 parse error** → log message text + error, continue batch
