# PROJECT_STATE

## Project Overview

### Project Name
rad-device-watch

### Goal
A comprehensive radiology device monitoring tool — inventory management, uptime/downtime tracking, usage auditing, and proactive alerting. Data sources: CSV/Excel, DICOM files, HL7 v2 messages, DICOM MPPS polling.

### Current Status
Phase 1 (Requirements) — complete. Moving to Phase 2 (Research).

---

## Completed Features

*None yet — project initialization*

---

## Current Work

### Active Feature
Project scaffolding and requirements

### Progress
- Requirements documented in REQUIREMENTS.md
- Storage: SQLite + CSV export
- Alert channels: console, dashboard, email, slack webhook, CLI-runner
- Data sources: CSV, DICOM, HL7 v2 (ORM/ORU/MDM/ADT/configurable), MPPS polling
- MVP: full scope (all modules built)

### Remaining Work
1. Research phase — investigate DICOM device tags, HL7 device parsing, MPPS standard
2. Architecture design — module boundaries, data model, service layer
3. Implementation
4. Testing
5. Validation
6. Handoff

---

## Next Actions

1. Read workflows/research.md and begin research phase

---

## Risks

### Open Questions
- None — requirements clear

### Known Issues
- None yet

### Technical Concerns
- HL7 v2 is a broad standard; will implement configurable field mapping rather than hard-coding every message type
- DICOM MPPS polling design needs care to avoid excessive load on PACS

---

## Resume Instructions

Start: read REQUIREMENTS.md, then run the research workflow.
Root: D:\Codex\rad-device-watch
First command to verify: `git init && git add -A && git commit -m "Initial commit: requirements"` (after project init)
