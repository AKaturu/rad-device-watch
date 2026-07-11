# Changelog

## Unreleased

- Removed password-related configuration values from alert and migration log messages.
- Pinned every GitHub Action dependency to an immutable commit SHA.
- Logged unreadable HL7 inputs and MPPS attribute failures instead of silently discarding them.
- Merge overlapping downtime intervals and clip events to the requested uptime period
- Require persisted device resolution for HL7 and MPPS usage records
- Commit alert history atomically and roll back failed polling transactions
- Render webhook payload templates structurally and source SMTP passwords from environment variables
- Add device update, downtime deletion, alert acknowledgement/deletion, and maintenance CLI workflows
- Pass dashboard database selection through an explicit environment contract and add AppTest coverage
- Centralize SQLite test fixtures and publish PEP 561 typing metadata
- Add Python 3.13 CI coverage and modern SPDX package metadata

## v0.1.0 (2026-06-28)

- Initial release with device inventory CRUD
- Downtime logging and uptime calculation
- Usage auditing and procedure-volume summaries
- Configurable alert rules with multiple channels
- CSV/Excel, DICOM, HL7 v2, and MPPS importers
- CSV export for devices, downtime, and usage records
- Streamlit dashboard with Plotly charts
- Reproducible demo media generation
