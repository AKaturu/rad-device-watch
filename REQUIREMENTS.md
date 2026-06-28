# rad-device-watch — Requirements

## Goal
A comprehensive radiology device monitoring tool: inventory management, uptime/downtime tracking, usage auditing, and proactive alerting.

## Functional Requirements

### FR1 — Device Inventory
- Store devices with: name, manufacturer, model, serial number, station name, modality, location, installation date, software version, status (active/inactive/retired)
- Import inventory from CSV/Excel, DICOM files (device module tags), and HL7 v2 messages
- Track maintenance schedules and history
- CRUD operations via CLI and dashboard

### FR2 — Uptime/Downtime Monitoring
- Log downtime events: device, start/end time, duration, cause category, description, impact level
- Calculate uptime percentage configurable by period (daily, monthly, quarterly, yearly)
- Downtime trend analysis and reporting
- Support both batch (historical log import) and live (DICOM MPPS / HL7 polling) modes
- Detect and flag recurring downtime patterns

### FR3 — Usage Auditing
- Track procedure volumes per device over time
- Calculate utilization rate (e.g., scans per hour vs. capacity)
- Identify idle periods and underutilized devices
- Trend analysis: MoM/QoQ volume changes, outlier detection (statistical)
- Import usage data from CSV/HL7/DICOM

### FR4 — Alerting
- Configurable alert rules: device down > threshold, maintenance due, utilization anomalies
- Delivery channels: console, dashboard badge, email (SMTP), webhook/Slack, CLI-runner
- Alert history and acknowledgement tracking

### FR5 — Reporting & Export
- Export inventory, downtime, usage reports to CSV
- Generate summary PDF/HTML reports via Jinja2
- Audit trail of all changes

### FR6 — Dashboard (Optional)
- Streamlit-based interactive dashboard
- Inventory overview, downtime timeline, usage charts, alert management
- Adjudication/editing of device records

## Non-Functional Requirements
- **Python >=3.11**, setuptools build, `src/` layout
- **Storage**: SQLite for persistence (auto-created), CSV for interchange
- **CLI**: Typer-based with Rich tables and progress bars
- **Models**: Pydantic v2 for data validation
- **Testing**: pytest + pytest-cov, all new features tested
- **Linting**: ruff (line-length=100), **Type-checking**: mypy
- **Logging**: structured logging to file and console
- **Extensible**: plugin-style alert channel architecture, configurable HL7 field mappings

## Scope Boundaries
### In Scope
- Single-site device monitoring (multi-site via separate DB instances or site field)
- DICOM MPPS polling for live mode
- HL7 v2 parsing for ORM, ORU, MDM, ADT (configurable field maps)
- Statistical outlier detection (z-score / IQR based)
- Email (SMTP) and Slack webhook alert channels

### Out of Scope (v1)
- Multi-tenant / user authentication
- Real-time DICOM MWL/MPPS listener (use periodic polling instead)
- FHIR integration
- PACS/DICOM query/retrieve — user provides files or paths
- Direct device SNMP polling

## Acceptance Criteria
1. `rad-device-watch init` creates a SQLite DB and schema
2. `rad-device-watch import inventory --from-csv file.csv` loads devices
3. `rad-device-watch import dicom --dir ./dicom-files` extracts device info from DICOM tags
4. `rad-device-watch import hl7 --dir ./hl7-files` parses device-related HL7 messages
5. `rad-device-watch downtime log --device "CT1" --start "2026-01-01 08:00" --end "2026-01-01 10:00" --cause "Hardware failure"` creates a downtime event
6. `rad-device-watch uptime --period monthly` reports uptime % per device
7. `rad-device-watch usage report` shows volumes and utilization rates
8. `rad-device-watch alert check` evaluates alert rules and dispatches notifications
9. `rad-device-watch serve` launches the Streamlit dashboard
10. All workflows survive a round-trip: import → query → export → re-import
11. 100% of core logic covered by unit tests
