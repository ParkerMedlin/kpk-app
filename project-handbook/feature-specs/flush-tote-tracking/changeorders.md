# Discharge Testing – Change Orders

## Overview

Change orders for the flush tote tracking feature, now being renamed to **Discharge Testing** to capture all discharged materials (not just flush totes).

**Parent**: See `tasks.md` for completed Phase 1–7 work.

---

## Phase 8: Rename to Discharge Testing

_Comprehensive rename across model, services, selectors, views, URLs, templates, JS, and navigation._

- [x] **8.1** Rename model
  - **Do**: Rename `FlushToteReading` → `DischargeTestingRecord` in `app/core/models.py`; update Meta class, related_name references.
  - **Deliverable**: Model renamed; user will delete old table manually.

- [ ] **8.2** Rename selectors
  - **Do**: Rename `flush_tote_selectors.py` → `discharge_testing_selectors.py`; rename functions `list_flush_totes` → `list_discharge_tests`, `get_flush_tote` → `get_discharge_test`, `get_flush_type_options` → `get_discharge_type_options`; update `__init__.py` exports.
  - **Deliverable**: Selector module with new names.
  - **Verify**: Imports resolve in shell.

- [ ] **8.3** Rename services
  - **Do**: Rename `flush_tote_services.py` → `discharge_testing_services.py`; rename all functions (`create_flush_tote_reading` → `create_discharge_test`, etc.); update `__init__.py` exports.
  - **Deliverable**: Service module with new names.
  - **Verify**: Imports resolve; functions callable in shell.

- [ ] **8.4** Rename API views
  - **Do**: In `app/core/views/api.py`, rename `flush_tote_list_api` → `discharge_testing_list_api`, `flush_tote_detail_api` → `discharge_testing_detail_api`; update imports to use renamed services/selectors.
  - **Deliverable**: API views with new names.

- [ ] **8.5** Rename web views
  - **Do**: In `app/core/views/web.py`, rename `flush_tote_entry_view` → `discharge_testing_entry_view`, `flush_totes_view` → `discharge_testing_records_view`; update template paths and context.
  - **Deliverable**: Web views with new names.

- [ ] **8.6** Rename URL routes
  - **Do**: In `app/core/urls.py`, change paths: `/flush-tote-entry/` → `/discharge-testing/`, `/flush-tote-records/` → `/discharge-testing-records/`; update API paths: `/api/flush-totes/` → `/api/discharge-testing/`.
  - **Deliverable**: New URL structure active.
  - **Verify**: `python manage.py show_urls` shows new paths.

- [ ] **8.7** Rename templates
  - **Do**: Rename `flush_tote_entry.html` → `discharge_testing_entry.html`, `flush_totes.html` → `discharge_testing_records.html`; update internal references, page titles, headings.
  - **Deliverable**: Templates with new names and content.

- [ ] **8.8** Rename JS modules
  - **Do**: Rename `FlushToteEntry.js` → `DischargeTestingEntry.js`, `FlushTotes.js` → `DischargeTestingRecords.js`; update internal function names, API endpoint URLs, module registration.
  - **Deliverable**: JS modules with new names.
  - **Verify**: Page loads without JS errors.

- [ ] **8.9** Update navigation links
  - **Do**: In all navbar templates, update link URLs and labels from "Flush Tote" to "Discharge Testing".
  - **Deliverable**: Nav links use new URLs/labels.

- [ ] **8.10** Apply migrations (delegate to user)
  - **Do**: Prompt user to run migrations and delete old table if needed.

---

## Phase 9: Model Enhancements

- [ ] **9.1** Add `final_disposition` field
  - **Do**: Add `final_disposition` TextField (required) to `DischargeTestingRecord` model; purpose is to record what happens to container after testing.
  - **Deliverable**: Field added to model.
  - **Verify**: `python manage.py makemigrations` succeeds.

- [ ] **9.2** Update services for new field
  - **Do**: Update `create_discharge_test` service to accept and save `final_disposition`; add validation that field is not empty.
  - **Deliverable**: Service handles new field.

- [ ] **9.3** Apply migrations (delegate to user)
  - **Do**: Prompt user to run migrations.

---

## Phase 10: Form & Interface Updates

- [ ] **10.1** Add Approved checkbox to entry form
  - **Do**: Add prominent "Approved" checkbox to `discharge_testing_entry.html` form; style as large/visible checkbox.
  - **Deliverable**: Checkbox visible on form.
  - **Requirement**: Clear visual indicator for approval status.

- [ ] **10.2** Add Approved checkbox to records interface
  - **Do**: Add Approved column to admin records table in `discharge_testing_records.html`; show checkbox state in table rows.
  - **Deliverable**: Approval status visible in records view.

- [ ] **10.3** Wire Approved checkbox to API
  - **Do**: Update JS modules to send `approved` field on form submit; update API views/services to handle field.
  - **Deliverable**: Approval status persists to database.
  - **Verify**: Creating/editing record saves approval state.

- [ ] **10.4** Add lab personnel field to entry form
  - **Do**: Add `lab_technician` display field to entry form; autopopulate with current user; make readonly.
  - **Deliverable**: Lab tech sees their name on form.
  - **Requirement**: Visual confirmation of who is recording.

- [ ] **10.5** Add final_disposition field to forms
  - **Do**: Add `final_disposition` textarea to entry form and records edit interface; mark as required.
  - **Deliverable**: Field appears on both forms.
  - **Verify**: Form validation requires field.

- [ ] **10.6** Show action_required by default
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
| 8. Rename | In Progress | 1/10 |
| 9. Model Enhancements | Pending | 0/3 |
| 10. Form & Interface | Pending | 0/6 |
| 11. Navigation | Pending | 0/2 |

**Overall**: 1/21 tasks (5%)

---

**Status**: In Progress
