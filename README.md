# rad-device-watch

[![CI](https://github.com/AKaturu/rad-device-watch/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AKaturu/rad-device-watch/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

**Radiology device monitoring — inventory management, uptime/downtime tracking, usage auditing, and proactive alerting.**

`rad-device-watch` is a comprehensive tool for radiology departments to track their imaging devices, monitor availability, audit procedure volumes, and receive alerts when metrics cross configurable thresholds. Supports manual entry, CSV/Excel import, DICOM file extraction, HL7 v2 message parsing, and DICOM MPPS polling.

## Quick Start

```bash
pip install rad-device-watch
rad-device-watch init
rad-device-watch device-add --name "CT1" --manufacturer Siemens --modality CT
rad-device-watch uptime --device-id 1 --start 2026-01-01 --end 2026-06-30
```

## What It Does

- **Device Inventory** — track name, manufacturer, model, serial number, modality, location, software version, and status
- **Uptime / Downtime** — log downtime events with cause and impact level; compute uptime percentage for any period
- **Usage Auditing** — record procedure volumes per device; trend analysis (increasing/stable/decreasing) with outlier detection
- **Alerting** — configurable rules on downtime duration, uptime percentage, or usage volume; dispatch via console, email, Slack webhook, or generic webhook
- **Data Sources** — manual entry, CSV/Excel import, DICOM file device module extraction, HL7 v2 messages (ORM/ORU/MDM/ADT), DICOM MPPS polling
- **Reporting** — rich console tables, plain-text summaries, and CSV export
- **Dashboard** — interactive Streamlit web UI for monitoring and management

## CLI Commands

| Command | Description |
|---|---|
| `rad-device-watch init` | Initialize the database schema |
| `rad-device-watch device-add` | Register a new device |
| `rad-device-watch device-list` | List all devices |
| `rad-device-watch device-get <id>` | Show device details |
| `rad-device-watch device-delete <id>` | Remove a device |
| `rad-device-watch import-csv <file>` | Import devices/downtime/usage from CSV or Excel |
| `rad-device-watch import-dicom <path>` | Extract device info from DICOM files |
| `rad-device-watch downtime-log` | Log a downtime event |
| `rad-device-watch downtime-list` | List downtime events |
| `rad-device-watch uptime` | Compute uptime percentage for a device |
| `rad-device-watch usage-add` | Record a usage entry |
| `rad-device-watch usage-report` | Generate a usage summary report |
| `rad-device-watch alert-add` | Create an alert rule |
| `rad-device-watch alert-check` | Evaluate all alert rules |
| `rad-device-watch alert-history` | View triggered alerts |
| `rad-device-watch export` | Export data to CSV |
| `rad-device-watch serve` | Launch the Streamlit dashboard |

## Alert Rules

Rules are evaluated periodically and can trigger on any combination of device and metric:

| Metric | Condition | Description |
|---|---|---|
| `downtime_duration` | gt, lt, eq | Total downtime (minutes) in the last 7 days |
| `uptime_pct` | gt, lt, eq | Uptime percentage in the last 7 days |
| `usage_volume` | gt, lt, eq | Total procedure count in the last 7 days |

Supported alert channels: `console`, `email` (SMTP with TLS), `slack` (webhook), `webhook` (generic HTTP).

## Import Formats

### CSV / Excel

```csv
name,manufacturer,model,serial_number,modality,location
CT1,Siemens,SOMATOM Go.Up,SN12345,CT,Room 101
MR1,GE,SIGNA Architect,SN67890,MR,Room 202
```

### DICOM

Extracts device module tags (manufacturer, station name, model, serial number, software version, install date) and usage study-level data from single files or directories.

### HL7 v2

Parses ORM, ORU, MDM, and ADT messages using hl7apy, extracting device information and procedure data from OBR, OBX, PID, and Z-segments.

## License

MIT — see [LICENSE](LICENSE).
