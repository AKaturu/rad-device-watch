# rad-device-watch — Research Summary

## DICOM Device Tags (General Equipment Module)

| Tag | Name | VR | Notes |
|---|---|---|---|
| (0008,0070) | Manufacturer | LO | |
| (0008,0080) | Institution Name | LO | |
| (0008,1010) | Station Name | SH | User-defined machine name |
| (0008,1040) | Institutional Department Name | LO | |
| (0008,1090) | Manufacturer's Model Name | LO | |
| (0018,1000) | Device Serial Number | LO | |
| (0018,1008) | Gantry ID | LO | |
| (0018,1020) | Software Versions | LO | Multi-valued |
| (0018,1200) | Date of Last Calibration | DA | |
| (0018,1201) | Time of Last Calibration | TM | |
| (0018,1204) | Date of Manufacture | DA | |
| (0018,1205) | Date of Installation | DA | |
| (3010,002D) | Device Label | LO | User-defined label |
| (3010,002E) | Device Type Code Sequence | SQ | CID-defined |

Extracted via `pydicom.dcmread(path)` → dataset attributes.

## DICOM MPPS

- **pynetdicom** library supports MPPS N-CREATE, N-SET, N-EVENT-REPORT, N-GET
- Three SOP Classes: `ModalityPerformedProcedureStep` (1.2.840.10008.3.1.2.3.3), `ModalityPerformedProcedureStepRetrieve` (1.2.840.10008.3.1.2.3.4), `ModalityPerformedProcedureStepNotification`
- Key MPPS attributes: PerformedStationName, PerformedStationAETitle, PerformedLocation, PerformedProcedureStepStatus (IN PROGRESS / COMPLETED / DISCONTINUED), PerformedProcedureStepStartDate/Time, PerformedProcedureStepEndDate/Time
- Approach: SCU polling SCP via N-GET on ModalityPerformedProcedureStepRetrieve SOP Class

## HL7 v2 Parsing

### Options
1. **hl7apy** (v1.3.5, 2024) — MIT, full-featured, parse/create/validate, MLLP server, v2.1–2.8.2, Python 3.4–3.12
2. **python-hl7** (v0.4.5, 2022) — BSD, simpler, parse-only, MLLP client

**Recommendation: hl7apy** — broader version support, message creation too, more active maintenance.

### Key HL7 Message Types for Device Tracking
- **ORM^O01** — Order Message → OBR segment has ordering provider, filler details; Z-segments may carry device info
- **ORU^R01** — Result Message → OBX segments carry observations; OBR references performing device via Placer/Filler
- **MDM^T02** — Document → contains dictated report text
- **ADT^A01/A08/A31** — Admit/Update → patient demographics, location
- **SIU^S12/S13** — Scheduling → Schedulied Procedure Step with requested device/station

Approach: Configurable field mapping — user defines which pipe-delimited positions map to device attributes.

## Slack Webhooks

- Use `httpx` directly (already in dependency list) to POST JSON to webhook URL
- No additional library needed; pattern: `httpx.post(url, json={"text": message})`
- For rich formatting: Block Kit JSON payloads

## Email Alerts

- Standard library `smtplib` + `email` modules
- Configurable SMTP server, port, TLS, credentials

## Technology Recommendations

| Component | Choice | Rationale |
|---|---|---|
| Build | setuptools | Project convention |
| CLI | Typer + Rich | Project convention |
| Models | Pydantic v2 | Project convention |
| DICOM read | pydicom | Project convention, mature |
| DICOM network | pynetdicom | Only Python MPPS implementation |
| HL7 parsing | hl7apy | Full-featured, v2.1–2.8.2, MIT |
| Storage | sqlite3 (stdlib) + pandas for query | Zero deps for core DB |
| Alerts: Email | smtplib (stdlib) | Zero deps |
| Alerts: Slack | httpx POST to webhook URL | Already in deps |
| Alerts: Webhook | httpx POST to config URL | Flexible |
| Dashboard | Streamlit | Project convention |
| Testing | pytest + pytest-cov | Project convention |
| Linting | ruff | Project convention |
| Type checking | mypy | Project convention |
