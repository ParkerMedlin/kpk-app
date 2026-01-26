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

- [x] **8.6** Rename selectors
  - **Do**: Rename `flush_tote_selectors.py` → `discharge_testing_selectors.py`; rename functions `list_flush_totes` → `list_discharge_tests`, `get_flush_tote` → `get_discharge_test`, `get_flush_type_options` → `get_discharge_type_options`; update `__init__.py` exports.
  - **Deliverable**: Selector module with new names.
  - **Verify**: Imports resolve in shell.

- [x] **8.7** Rename services
  - **Do**: Rename `flush_tote_services.py` → `discharge_testing_services.py`; rename all functions (`create_flush_tote_reading` → `create_discharge_test`, etc.); update `__init__.py` exports.
  - **Deliverable**: Service module with new names.
  - **Verify**: Imports resolve; functions callable in shell.

- [x] **8.8** Rename API views
  - **Do**: In `app/core/views/api.py`, rename `flush_tote_list_api` → `discharge_testing_list_api`, `flush_tote_detail_api` → `discharge_testing_detail_api`; update imports to use renamed services/selectors.
  - **Deliverable**: API views with new names.

- [x] **8.9** Rename web views
  - **Do**: In `app/core/views/web.py`, rename `flush_tote_entry_view` → `discharge_testing_entry_view`, `flush_totes_view` → `discharge_testing_records_view`; update template paths and context.
  - **Deliverable**: Web views with new names.

- [x] **8.10** Rename URL routes
  - **Do**: In `app/core/urls.py`, change paths: `/flush-tote-entry/` → `/discharge-testing/`, `/flush-tote-records/` → `/discharge-testing-records/`; update API paths: `/api/flush-totes/` → `/api/discharge-testing/`.
  - **Deliverable**: New URL structure active.
  - **Verify**: `python manage.py show_urls` shows new paths.

- [x] **8.11** Rename templates
  - **Do**: Rename `flush_tote_entry.html` → `discharge_testing_entry.html`, `flush_totes.html` → `discharge_testing_records.html`; update internal references, page titles, headings.
  - **Deliverable**: Templates with new names and content.

- [x] **8.12** Rename JS modules
  - **Do**: Rename `FlushToteEntry.js` → `DischargeTestingEntry.js`, `FlushTotes.js` → `DischargeTestingRecords.js`; update internal function names, API endpoint URLs, module registration.
  - **Deliverable**: JS modules with new names.
  - **Verify**: Page loads without JS errors.

- [x] **8.13** Update navigation links
  - **Do**: In all navbar templates, update link URLs and labels from "Flush Tote" to "Discharge Testing".
  - **Deliverable**: Nav links use new URLs/labels.

---

## Phase 9: Selector & Service Updates for Field Changes

- [x] **9.1** Update selectors for field changes
  - **Do**: In `discharge_testing_selectors.py`, update any references to `production_line` → `discharge_source`; remove any `approval_status` filtering/sorting.
  - **Deliverable**: Selectors use new field names.

- [x] **9.2** Update services for field changes
  - **Do**: In `discharge_testing_services.py`, update `create_discharge_test` to accept `discharge_source` (not `production_line`) and `final_disposition`; remove any `approval_status` logic.
  - **Deliverable**: Services use new field names; handle new required field.

---

## Phase 10: Form & Interface Updates

- [x] **10.1** Update entry form for discharge_source rename
  - **Do**: In `discharge_testing_entry.html`, rename `production_line` field/label to `discharge_source`; update any associated help text.
  - **Deliverable**: Entry form uses new field name.

- [x] **10.2** Update records interface for discharge_source rename
  - **Do**: In `discharge_testing_records.html`, rename column header and field references from `production_line` to `discharge_source`.
  - **Deliverable**: Records table uses new field name.

- [x] **10.3** Update JS modules for discharge_source rename
  - **Do**: In `DischargeTestingEntry.js` and `DischargeTestingRecords.js`, update field references from `production_line` to `discharge_source`.
  - **Deliverable**: JS uses new field name.

- [x] **10.4** Remove approval_status from entry form
  - **Do**: In `discharge_testing_entry.html`, remove any approval_status field, badge, or related UI elements.
  - **Deliverable**: No approval_status on entry form.

- [x] **10.5** Remove approval_status from records interface
  - **Do**: In `discharge_testing_records.html`, remove approval_status column, badges, and any filter/sort options.
  - **Deliverable**: No approval_status in records view.

- [x] **10.6** Remove approval_status from JS modules
  - **Do**: In `DischargeTestingEntry.js` and `DischargeTestingRecords.js`, remove any approval_status handling, validation, or display logic.
  - **Deliverable**: JS has no approval_status references.

- [x] **10.7** Add lab personnel field to entry form
  - **Do**: Add `lab_technician` display field to entry form; autopopulate with current user; make readonly.
  - **Deliverable**: Lab tech sees their name on form.
  - **Requirement**: Visual confirmation of who is recording.

- [x] **10.8** Add final_disposition field to forms
  - **Do**: Add `final_disposition` textarea to entry form and records edit interface; mark as required.
  - **Deliverable**: Field appears on both forms.
  - **Verify**: Form validation requires field.

- [x] **10.9** Show action_required by default
  - **Do**: In `DischargeTestingEntry.js`, remove JS that conditionally hides `action_required` field; display field at all times.
  - **Deliverable**: Action required field always visible.
  - **Verify**: Field shows on page load without interaction.

---

## Phase 11: Navigation Reorganization

- [x] **11.1** Move nav item to Blending dropdown
  - **Do**: In `admin-navbar-items.html` and any other navbar templates, move Discharge Testing link from standalone item into Blending dropdown menu.
  - **Deliverable**: Nav item nested under Blending.
  - **Verify**: Link appears in Blending dropdown for appropriate users.

- [x] **11.2** Remove standalone nav entries
  - **Do**: Remove any remaining standalone "Flush Tote" or "Discharge Testing" nav items outside Blending dropdown.
  - **Deliverable**: Clean nav structure.

---

## Phase 12: Rename line_personnel → sampling_personnel

_Rename field across model, services, selectors, views, templates, and JS._

- [x] **12.1** Rename model field
  - **Do**: In `app/core/models.py`, rename field `line_personnel` to `sampling_personnel` in `DischargeTestingRecord` model; update `related_name` from `discharge_tests_line` to `discharge_tests_sampling`.
  - **Deliverable**: Model field renamed.

- [x] **12.2** Create migration
  - **Do**: Create migration to rename `line_personnel` → `sampling_personnel` column.
  - **Verify**: `python manage.py makemigrations` succeeds.

- [x] **12.3** Apply migration (delegate to user)
  - **Do**: Prompt user to run migrations.
  - **Verify**: Migration applies cleanly.

- [x] **12.4** Update selectors
  - **Do**: In `discharge_testing_selectors.py`, update `select_related` calls from `line_personnel` to `sampling_personnel`; update any docstrings.
  - **Deliverable**: Selectors use new field name.

- [x] **12.5** Rename service helper functions
  - **Do**: In `discharge_testing_services.py`, rename `_line_personnel_display` → `_sampling_personnel_display`, `_resolve_line_personnel` → `_resolve_sampling_personnel`.
  - **Deliverable**: Helper functions renamed.

- [x] **12.6** Update service field references
  - **Do**: In `discharge_testing_services.py`, update all references: `line_personnel_id` → `sampling_personnel_id`, `line_personnel_name` → `sampling_personnel_name`, `line_personnel` → `sampling_personnel`; update validation error messages.
  - **Deliverable**: Service uses new field names throughout.

- [x] **12.7** Rename API view helper functions
  - **Do**: In `app/core/views/api.py`, rename `_line_personnel_display` → `_sampling_personnel_display`.
  - **Deliverable**: API helper function renamed.

- [x] **12.8** Update API view field references
  - **Do**: In `app/core/views/api.py`, update all references: `line_personnel_id` → `sampling_personnel_id`, `line_personnel_name` → `sampling_personnel_name`, `line_personnel` → `sampling_personnel` in serialization and payload handling.
  - **Deliverable**: API uses new field names.

- [x] **12.9** Update entry form template
  - **Do**: In `discharge_testing_entry.html`, rename input field `name="line_personnel_name"` to `name="sampling_personnel_name"`; update any labels or help text.
  - **Deliverable**: Entry form uses new field name.

- [x] **12.10** Update records template
  - **Do**: In `discharge_testing_records.html`, update `data-field` attributes, `data-value` references, and display logic from `line_personnel` to `sampling_personnel`.
  - **Deliverable**: Records table uses new field name.

- [x] **12.11** Update DischargeTestingEntry.js
  - **Do**: In `DischargeTestingEntry.js`, update field references from `line_personnel_name` to `sampling_personnel_name`; update validation messages; rename any related variables (e.g., `linePersonnel` → `samplingPersonnel`).
  - **Deliverable**: Entry JS uses new field names.

- [x] **12.12** Update DischargeTestingRecords.js
  - **Do**: In `DischargeTestingRecords.js`, update field references from `line_personnel_name` to `sampling_personnel_name` in edit logic, rendering, and data handling.
  - **Deliverable**: Records JS uses new field names.

---

## Phase 13: Rename flush_type → discharge_type

_Rename field across model, services, selectors, views, templates, and JS._

- [x] **13.1** Rename model field
  - **Do**: In `app/core/models.py`, rename field `flush_type` to `discharge_type` in `DischargeTestingRecord` model.
  - **Deliverable**: Model field renamed.

- [x] **13.2** Update model `__str__` method
  - **Do**: In `app/core/models.py`, update `DischargeTestingRecord.__str__` to reference `self.discharge_type` instead of `self.flush_type`.
  - **Deliverable**: String representation uses new field name.

- [x] **13.3** Create migration
  - **Do**: Create migration to rename `flush_type` → `discharge_type` column.
  - **Verify**: `python manage.py makemigrations` succeeds.

- [x] **13.4** Apply migration (delegate to user)
  - **Do**: Prompt user to run migrations.
  - **Verify**: Migration applies cleanly.

- [x] **13.5** Update selector docstring
  - **Do**: In `discharge_testing_selectors.py`, update `get_discharge_type_options` docstring to say "discharge type" instead of "flush type".
  - **Deliverable**: Docstring updated.

- [x] **13.6** Update service field references
  - **Do**: In `discharge_testing_services.py`, update all references: `flush_type` → `discharge_type`, including parameter names, validation, and model assignment.
  - **Deliverable**: Service uses new field name throughout.

- [x] **13.7** Update API view field references
  - **Do**: In `app/core/views/api.py`, update all references: `flush_type` → `discharge_type` in serialization, payload handling, and `line_fields` set.
  - **Deliverable**: API uses new field name.

- [x] **13.8** Update web views context key
  - **Do**: In `app/core/views/web.py`, rename context key `flush_type_options` → `discharge_type_options` in both discharge testing views.
  - **Deliverable**: Context uses new key name.

- [x] **13.9** Update entry form template
  - **Do**: In `discharge_testing_entry.html`, update: field `name="flush_type"` → `name="discharge_type"`, `id` attribute, label text "Flush Type" → "Discharge Type", loop variable `flush_type` → `discharge_type`, context variable `flush_type_options` → `discharge_type_options`.
  - **Deliverable**: Entry form uses new field name.

- [x] **13.10** Update records template
  - **Do**: In `discharge_testing_records.html`, update `data-field="flush_type"` → `data-field="discharge_type"`, `data-value` references.
  - **Deliverable**: Records table uses new field name.

- [x] **13.11** Update DischargeTestingEntry.js
  - **Do**: In `DischargeTestingEntry.js`, update: field references `flush_type` → `discharge_type`, validation error key, variable name `flushType` → `dischargeType`, getter mapping.
  - **Deliverable**: Entry JS uses new field names.

- [x] **13.12** Update DischargeTestingRecords.js
  - **Do**: In `DischargeTestingRecords.js`, update: field references `flush_type` → `discharge_type` in selectors, snapshot, payload building, and rendering.
  - **Deliverable**: Records JS uses new field names.

---

## Phase 14: Convert discharge_type to Model-Defined Choices

_Replace dynamic options lookup with predefined model choices._

- [x] **14.1** Define DISCHARGE_TYPE_CHOICES in model
  - **Do**: In `app/core/models.py`, add `DISCHARGE_TYPE_CHOICES` constant to `DischargeTestingRecord` with tuples: `('Acid', 'Acid'), ('Base', 'Base'), ('Soap', 'Soap'), ('Polish', 'Polish'), ('Oil', 'Oil')`.
  - **Deliverable**: Choices constant defined.

- [x] **14.2** Update discharge_type field to use choices
  - **Do**: In `app/core/models.py`, update `discharge_type` field: add `choices=DISCHARGE_TYPE_CHOICES`, adjust `max_length` if needed (current is 100, max choice length is 6).
  - **Deliverable**: Field uses predefined choices.

- [x] **14.3** Create migration
  - **Do**: Create migration for choices constraint.
  - **Verify**: `python manage.py makemigrations` succeeds.

- [x] **14.4** Apply migration (delegate to user)
  - **Do**: Prompt user to run migrations.
  - **Verify**: Migration applies cleanly.

- [x] **14.5** Remove get_discharge_type_options selector
  - **Do**: In `discharge_testing_selectors.py`, delete `get_discharge_type_options` function.
  - **Deliverable**: Selector function removed.

- [x] **14.6** Update selector exports
  - **Do**: In `app/core/selectors/__init__.py`, remove `get_discharge_type_options` from imports and exports.
  - **Deliverable**: Export removed.

- [x] **14.7** Update web views to use model choices
  - **Do**: In `app/core/views/web.py`, remove import of `get_discharge_type_options`; change context to `'discharge_type_options': DischargeTestingRecord.DISCHARGE_TYPE_CHOICES`.
  - **Deliverable**: Views use model choices directly.

- [x] **14.8** Update entry form template for choices format
  - **Do**: In `discharge_testing_entry.html`, update options loop to handle tuple format: `{% for value, label in discharge_type_options %}` with `value="{{ value }}"` and display `{{ label }}`.
  - **Deliverable**: Template iterates model choices correctly.

---

## Phase 15: Sampling Personnel User Dropdown

_Replace free-text input with user selection dropdown._

- [x] **15.1** Create selector for eligible users
  - **Do**: In `discharge_testing_selectors.py`, add `get_sampling_personnel_options()` function that returns active users as list of `(id, display_name)` tuples, ordered by display name.
  - **Deliverable**: Selector function returns user options.

- [x] **15.2** Update selector exports
  - **Do**: In `app/core/selectors/__init__.py`, add `get_sampling_personnel_options` to imports and exports.
  - **Deliverable**: Function exported from selectors package.

- [x] **15.3** Add user options to web views context
  - **Do**: In `app/core/views/web.py`, import `get_sampling_personnel_options`; add `'sampling_personnel_options': get_sampling_personnel_options()` to context in both discharge testing views.
  - **Deliverable**: User options available in template context.

- [x] **15.4** Update entry form template
  - **Do**: In `discharge_testing_entry.html`, replace text input for sampling_personnel with `<select>` dropdown; iterate `sampling_personnel_options` with `value="{{ id }}"` and display name; change field name to `sampling_personnel_id`.
  - **Deliverable**: Entry form uses dropdown.

- [x] **15.5** Update DischargeTestingEntry.js
  - **Do**: In `DischargeTestingEntry.js`, update field references from `sampling_personnel_name` to `sampling_personnel_id`; update validation to check for selected value; update payload building.
  - **Deliverable**: Entry JS handles dropdown selection.

- [x] **15.6** Update service to accept user ID
  - **Do**: In `discharge_testing_services.py`, update `create_discharge_test` to accept `sampling_personnel_id` parameter; look up user by ID instead of name; keep backward compatibility with name if needed.
  - **Deliverable**: Service accepts user ID directly.

- [x] **15.7** Update API view for user ID
  - **Do**: In `app/core/views/api.py`, update payload handling to read `sampling_personnel_id`; pass ID to service; update serialization if needed.
  - **Deliverable**: API accepts and returns user ID.

- [x] **15.8** Update records template for inline edit
  - **Do**: In `discharge_testing_records.html`, if inline editing uses text input for sampling personnel, update to use dropdown or remove inline edit capability for this field.
  - **Deliverable**: Records template consistent with new field type.

- [x] **15.9** Update DischargeTestingRecords.js for inline edit
  - **Do**: In `DischargeTestingRecords.js`, update inline edit logic for sampling_personnel to handle dropdown or ID-based selection.
  - **Deliverable**: Records JS handles new field type.

- [x] **15.10** Remove name-based resolution (cleanup)
  - **Do**: In `discharge_testing_services.py`, remove `_resolve_sampling_personnel` helper function if no longer needed; clean up any dead code paths.
  - **Deliverable**: Service code cleaned up.

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 8. Model & Rename | Complete | 13/13 |
| 9. Selector & Service Updates | Complete | 2/2 |
| 10. Form & Interface | Complete | 9/9 |
| 11. Navigation | Complete | 2/2 |
| 12. Rename line_personnel | Complete | 12/12 |
| 13. Rename flush_type | Complete | 12/12 |
| 14. Model-Defined Choices | Complete | 8/8 |
| 15. Sampling Personnel Dropdown | Complete | 10/10 |

**Overall**: 68/68 tasks (100%)

---

**Status**: Complete
