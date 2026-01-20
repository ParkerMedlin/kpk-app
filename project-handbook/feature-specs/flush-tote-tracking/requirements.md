# Flush Tote Tracking Requirements

## Problem Statement

Flush totes from production lines need consistent testing, approval, and discharge tracking. Today the workflow is manual and fragmented, creating risk of dumping out-of-range totes and poor visibility into status between line personnel and lab technicians.

## User Stories

### Line Personnel
- **As a** line operator, **I want to** create a flush tote entry when I bring it to the lab, **so that** the lab can record test results against the correct tote.
- **As a** line operator, **I want to** see when a tote is approved for dumping in real time, **so that** I can dispose of it without waiting for verbal confirmation.

### Lab Technician
- **As a** lab tech, **I want to** record initial and final pH readings for a flush tote, **so that** the plant has traceability for the discharge decision.
- **As a** lab tech, **I want to** flag totes that require corrective action and record the action taken, **so that** supervisors can review interventions.

### Supervisor (secondary)
- **As a** supervisor, **I want to** verify that out-of-range totes have documented actions before approval, **so that** compliance and safety policies are met.

## Acceptance Criteria

### Core Functionality
- **WHEN** line personnel create a flush tote entry, **THEN** the system **SHALL** auto-fill the date/time as now and require production line and flush tote type.
- **WHEN** a lab tech records an initial pH, **THEN** the system **SHALL** flag entries outside 5.1–10.9 as “Action Required” and block final approval until action is recorded and a compliant final pH is entered.
- **WHEN** final pH is saved within 5.1–10.9, **THEN** the system **SHALL** mark the tote as approved for discharge and notify connected clients via WebSocket.
- **IF** the approval status changes (e.g., Approved, Pending, Needs Action), **THEN** all users viewing the page **SHALL** see the update in real time via WebSocket.

### Error Handling
- **WHEN** required fields are missing or pH values are non-numeric, **THEN** the system **SHALL** reject the submission with field-level errors.
- **WHEN** Redis/WebSocket connectivity fails, **THEN** the system **SHALL** allow save via HTTP and queue a reconnect notice in the UI.

### User Experience
- **WHEN** a user edits a tote, **THEN** the form **SHALL** show who last updated each pH field and when.
- **WHEN** a tote is pending action, **THEN** the UI **SHALL** display the recorded action description prominently for both roles.

## Scope

### In Scope
- New `FlushToteReading` model with fields: date (auto), production_line, flush_type, initial_pH, action_required (free text), final_pH, approval_status, lab_technician, line_personnel.
- Web UI for line personnel and lab technicians to create/update entries with role-based field enablement.
- WebSocket updates so multiple viewers see live state changes.
- Validation enforcing pH range 5.1–10.9 for approval.

### Out of Scope
- Mobile-specific UI.
- Historical analytics or trend reports beyond table/list views.
- Automated instrument integration for pH readings.

## Dependencies

- Existing Django user groups for “lab technician” and “line personnel” to control permissions.
- `BlendContainerClassification` model to source `flush_type` options from unique `flush_tote` values.
- Django Channels + Redis stack already used for real-time features.

---

**Status**: Approved
