# Flush Tote Tracking Requirements

## Problem Statement

Flush totes from production lines need consistent testing, approval, and discharge tracking. Today the workflow is manual and fragmented, creating risk of dumping out-of-range totes and poor visibility into status.

## User Stories

### Lab Technician
- **As a** lab tech, **I want to** record all flush tote data (production line, flush type, line personnel name, pH readings, and any corrective action) in a single form, **so that** I can complete the task in one session without navigating multiple screens.
- **As a** lab tech, **I want to** see clear validation feedback when pH is out of range, **so that** I know when corrective action is required before approval.

### Supervisor / Admin
- **As a** supervisor, **I want to** view and search all flush tote records in a table, **so that** I can audit discharge decisions and verify compliance.
- **As a** supervisor, **I want to** inline-edit historical records if corrections are needed, **so that** data accuracy is maintained.

## Acceptance Criteria

### Core Functionality
- **WHEN** a lab tech submits a flush tote entry, **THEN** the system **SHALL** auto-fill the date/time as now and require production line, flush type, and line personnel name.
- **WHEN** a lab tech records an initial pH, **THEN** the system **SHALL** flag entries outside 5.1–10.9 as "Action Required" and block final approval until action is recorded and a compliant final pH is entered.
- **WHEN** final pH is saved within 5.1–10.9, **THEN** the system **SHALL** mark the tote as approved for discharge.

### Error Handling
- **WHEN** required fields are missing or pH values are non-numeric, **THEN** the system **SHALL** reject the submission with field-level errors.

### User Experience
- **WHEN** a lab tech opens the entry form, **THEN** the form **SHALL** present all fields for single-session completion (production line, flush type, line personnel, initial pH, action if needed, final pH).
- **WHEN** a staff user opens the admin records page, **THEN** the page **SHALL** display a searchable table with inline editing capability.

## Scope

### In Scope
- `DischargeTestingRecord` model with fields: date (auto), production_line, flush_type, initial_pH, action_required (free text), final_pH, approval_status, lab_technician, line_personnel.
- Single-instance entry form for lab technicians at `/flush-tote-entry/`.
- Admin table view with inline editing and search at `/flush-tote-records/` (staff only).
- Validation enforcing pH range 5.1–10.9 for approval.

### Out of Scope
- Mobile-specific UI.
- Historical analytics or trend reports beyond table/list views.
- Automated instrument integration for pH readings.
- Real-time WebSocket updates (standard HTTP refresh is sufficient).

## Dependencies

- Existing Django user group "lab technician" to control entry form access.
- `BlendContainerClassification` model to source `flush_type` options from unique `flush_tote` values.

---

**Status**: Approved (Revised)
