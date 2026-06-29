# rad-device-watch — Project Status

## Current Release

**v0.1.0** — Initial release providing a radiology device monitoring toolkit for inventory management, uptime/downtime tracking, usage auditing, import/export workflows, dashboard review, and configurable alerting.

## Implemented Features

- Device inventory CRUD with manufacturer, model, serial, station, modality, location, department, and status fields
- Downtime logging and uptime calculation over configurable periods
- Usage-record entry and procedure-volume summary reports
- Alert rules for downtime, uptime, and usage thresholds (channels: console, email, slack, webhook)
- CSV/Excel, DICOM, HL7 v2, and MPPS-oriented importers
- CSV export for devices, downtime events, and usage records
- Rich console tables, plain-text summaries
- Streamlit dashboard with Plotly charts
- Reproducible demo media generation

## Quality Gates

- Test suite covering database, models, inventory, downtime, usage, alerts, importers, and exporters
- No ruff violations
- No mypy errors

## Known Issues

- DICOM/HL7 importers require institution-approved synthetic fixtures for full validation
- Native release packaging not yet implemented
