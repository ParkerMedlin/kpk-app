# Discharge Testing – Change Orders

## Overview

Change orders for the flush tote tracking feature, now being renamed to **Discharge Testing** to capture all discharged materials (not just flush totes).

**Parent**: See `tasks.md` for completed Phase 1–7 work.

---

## Phase 8: Model & Rename

_All model changes (rename + field changes) followed by comprehensive rename across services, selectors, views, URLs, templates, JS, and navigation._

- [x] **8.1** Rename model class
  - **Do**: Rename `DischargeTestingRecord` → `DischargeTestingRecord` in `app/core/models.py`; update Meta class, related_name references.
  - **Deliverable**: Model class renamed.

- [x] **8.2** Add `final_disposition` field
  - **Do**: Add `final_disposition` TextField (required) to `DischargeTestingRecord` model; purpose is to record what happens to container after testing.
  - **Deliverable**: Field added to model.

- [x] **8.3** Rename `production_line` → `discharge_source`
  - **Do**: Rename field `production_line` to `discharge_source` in `DischargeTestingRecord` model; update any related_name or verbose_name.
  - **Deliverable**: Field renamed in model.

- [x] **8.4** Remove `approval_status` field
  - **Do**: Remove `approval_status` field from `DischargeTestingRecord` model; remove any related choices/constants.
  - **Deliverable**: Field removed from model.

- [x] **8.5** Apply migrations (delegate to user)
  - **Do**: Prompt user to run migrations and delete old table if needed.
  - **Verify**: `python manage.py makemigrations` succeeds; migrations apply cleanly.

- [ ] **8.6** Rename selectors
  - **Do**: Rename `flush_tote_selectors.py` → `discharge_testing_selectors.py`; rename functions `list_flush_totes` → `list_discharge_tests`, `get_flush_tote` → `get_discharge_test`, `get_flush_type_options` → `get_discharge_type_options`; update `__init__.py` exports.
  - **Deliverable**: Selector module with new names.
  - **Verify**: Imports resolve in shell.

- [ ] **8.7** Rename services
  - **Do**: Rename `flush_tote_services.py` → `discharge_testing_services.py`; rename all functions (`create_flush_tote_reading` → `create_discharge_test`, etc.); update `__init__.py` exports.
  - **Deliverable**: Service module with new names.
  - **Verify**: Imports resolve; functions callable in shell.

- [ ] **8.8** Rename API views
  - **Do**: In `app/core/views/api.py`, rename `flush_tote_list_api` → `discharge_testing_list_api`, `flush_tote_detail_api` → `discharge_testing_detail_api`; update imports to use renamed services/selectors.
  - **Deliverable**: API views with new names.

- [ ] **8.9** Rename web views
  - **Do**: In `app/core/views/web.py`, rename `flush_tote_entry_view` → `discharge_testing_entry_view`, `flush_totes_view` → `discharge_testing_records_view`; update template paths and context.
  - **Deliverable**: Web views with new names.

- [ ] **8.10** Rename URL routes
  - **Do**: In `app/core/urls.py`, change paths: `/flush-tote-entry/` → `/discharge-testing/`, `/flush-tote-records/` → `/discharge-testing-records/`; update API paths: `/api/flush-totes/` → `/api/discharge-testing/`.
  - **Deliverable**: New URL structure active.
  - **Verify**: `python manage.py show_urls` shows new paths.

- [ ] **8.11** Rename templates
  - **Do**: Rename `flush_tote_entry.html` → `discharge_testing_entry.html`, `flush_totes.html` → `discharge_testing_records.html`; update internal references, page titles, headings.
  - **Deliverable**: Templates with new names and content.

- [ ] **8.12** Rename JS modules
  - **Do**: Rename `FlushToteEntry.js` → `DischargeTestingEntry.js`, `FlushTotes.js` → `DischargeTestingRecords.js`; update internal function names, API endpoint URLs, module registration.
  - **Deliverable**: JS modules with new names.
  - **Verify**: Page loads without JS errors.

- [ ] **8.13** Update navigation links
  - **Do**: In all navbar templates, update link URLs and labels from "Flush Tote" to "Discharge Testing".
  - **Deliverable**: Nav links use new URLs/labels.

---

## Phase 9: Selector & Service Updates for Field Changes

- [ ] **9.1** Update selectors for field changes
  - **Do**: In `discharge_testing_selectors.py`, update any references to `production_line` → `discharge_source`; remove any `approval_status` filtering/sorting.
  - **Deliverable**: Selectors use new field names.

- [ ] **9.2** Update services for field changes
  - **Do**: In `discharge_testing_services.py`, update `create_discharge_test` to accept `discharge_source` (not `production_line`) and `final_disposition`; remove any `approval_status` logic.
  - **Deliverable**: Services use new field names; handle new required field.

---

## Phase 10: Form & Interface Updates

- [ ] **10.1** Update entry form for discharge_source rename
  - **Do**: In `discharge_testing_entry.html`, rename `production_line` field/label to `discharge_source`; update any associated help text.
  - **Deliverable**: Entry form uses new field name.

- [ ] **10.2** Update records interface for discharge_source rename
  - **Do**: In `discharge_testing_records.html`, rename column header and field references from `production_line` to `discharge_source`.
  - **Deliverable**: Records table uses new field name.

- [ ] **10.3** Update JS modules for discharge_source rename
  - **Do**: In `DischargeTestingEntry.js` and `DischargeTestingRecords.js`, update field references from `production_line` to `discharge_source`.
  - **Deliverable**: JS uses new field name.

- [ ] **10.4** Remove approval_status from entry form
  - **Do**: In `discharge_testing_entry.html`, remove any approval_status field, badge, or related UI elements.
  - **Deliverable**: No approval_status on entry form.

- [ ] **10.5** Remove approval_status from records interface
  - **Do**: In `discharge_testing_records.html`, remove approval_status column, badges, and any filter/sort options.
  - **Deliverable**: No approval_status in records view.

- [ ] **10.6** Remove approval_status from JS modules
  - **Do**: In `DischargeTestingEntry.js` and `DischargeTestingRecords.js`, remove any approval_status handling, validation, or display logic.
  - **Deliverable**: JS has no approval_status references.

- [ ] **10.7** Add lab personnel field to entry form
  - **Do**: Add `lab_technician` display field to entry form; autopopulate with current user; make readonly.
  - **Deliverable**: Lab tech sees their name on form.
  - **Requirement**: Visual confirmation of who is recording.

- [ ] **10.8** Add final_disposition field to forms
  - **Do**: Add `final_disposition` textarea to entry form and records edit interface; mark as required.
  - **Deliverable**: Field appears on both forms.
  - **Verify**: Form validation requires field.

- [ ] **10.9** Show action_required by default
  - **Do**: In `DischargeTestingEntry.js`, remove JS that conditionally hides `action_required` field; display field at all times.
  - **Deliverable**: Action required field always visible.
  - **Verify**: Field shows on page load without interaction.

---

## Phase 11: Navigation Reorganization

- [ ] **11.1** Move nav item to Blending dropdown
  - **Do**: In `admin-navbar-items.html` and any other navbar templates, move Discharge Testing link from standalone item into Blending dropdown menu.
  - **Deliverable**: Nav item nested under Blending.
  - **Verify**: Link appears in Blending dropdown for appropriate users.

- [ ] **11.2** Remove standalone nav entries
  - **Do**: Remove any remaining standalone "Flush Tote" or "Discharge Testing" nav items outside Blending dropdown.
  - **Deliverable**: Clean nav structure.

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 8. Model & Rename | In Progress | 3/13 |
| 9. Selector & Service Updates | Pending | 0/2 |
| 10. Form & Interface | Pending | 0/9 |
| 11. Navigation | Pending | 0/2 |

**Overall**: 3/26 tasks (12%)

---

**Status**: In Progress
