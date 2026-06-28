# PROJECT_STATE

## Project Overview

### Project Name
rad-device-watch

### Goal
Provide a radiology device monitoring toolkit for inventory management, uptime/downtime tracking, usage auditing, import/export workflows, dashboard review, and configurable alerting.

### Current Status
Phase 1 MVP complete. Core CLI, SQLite storage, inventory, downtime, uptime, usage auditing, alert rules, CSV export, importers, Streamlit dashboard, tests, and README demo media tooling are implemented.

### 2026-06-28 Demo Media Update
- Added reproducible demo media generation from real `rad-device-watch` CLI commands.
- Added README demo GIF and demo-media documentation.
- Added `media` optional dependencies for Pillow/ImageIO rendering.
- Updated `.gitignore` for generated output and temp folders.
- Verified the GitHub repository description already exists: "Radiology device monitoring - inventory, uptime/downtime, usage auditing, and alerting."

## Completed Features

- Device inventory CRUD with manufacturer, model, serial, station, modality, location, department, and status fields.
- Downtime logging and uptime calculation over a requested period.
- Usage-record entry and procedure-volume summary reports.
- Alert rules for downtime, uptime, and usage thresholds.
- CSV export for devices, downtime events, and usage records.
- CSV/Excel, DICOM, HL7, and MPPS-oriented importer modules.
- Streamlit dashboard entrypoint.
- Test suite covering database, models, inventory, downtime, usage, alerts, importers, and exporters.
- Reproducible README media generator.

## Validation

- Pending after this update: install media extras, regenerate demo assets, run lint/tests, commit, and push.

## Remaining Work

- Add native release packaging if this project should have downloadable desktop/CLI artifacts like the other repos.
- Add a richer dashboard screenshot/video once UI workflows are polished.
- Validate DICOM/HL7 importers against institution-approved synthetic fixtures.
