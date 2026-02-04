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

## Phase 16: Acid/Base Material Autocomplete

_When discharge_type is Acid or Base, require user to specify the material via autocomplete from ci_item records where itemcodedesc starts with BLEND or CHEM._

### Model Changes

- [x] **16.1** Add `discharge_material_code` field
  - **Do**: In `app/core/models.py`, add `discharge_material_code = models.CharField(max_length=50, blank=True, null=True)` to `DischargeTestingRecord` model; stores itemcode from ci_item.
  - **Deliverable**: Field added to model.

- [x] **16.2** Create migration
  - **Do**: Create migration for new field.
  - **Verify**: `python manage.py makemigrations` succeeds.

- [x] **16.3** Apply migration (delegate to user)
  - **Do**: Prompt user to run migrations.
  - **Verify**: Migration applies cleanly.

### Selector Layer

- [x] **16.4** Create material autocomplete selector
  - **Do**: In `discharge_testing_selectors.py`, add `get_acid_base_material_options(search_term: str, limit: int = 20)` function that queries `CiItem.objects.filter(itemcodedesc__istartswith='BLEND') | CiItem.objects.filter(itemcodedesc__istartswith='CHEM')`, filters by search_term matching itemcode or itemcodedesc (case-insensitive), returns list of `{'value': itemcode, 'label': f"{itemcode}: {itemcodedesc}"}` dicts, ordered by itemcode, limited to `limit` results.
  - **Deliverable**: Selector function returns filtered material options.

- [x] **16.5** Update selector exports
  - **Do**: In `app/core/selectors/__init__.py`, add `get_acid_base_material_options` to imports and exports.
  - **Deliverable**: Function exported from selectors package.

### API Layer - Autocomplete Endpoint

- [x] **16.6** Create material search API view
  - **Do**: In `app/core/views/api.py`, add `discharge_material_search_api(request)` view function; accept GET with `q` query param; return JSON `{"status": "ok", "results": [...]}` using `get_acid_base_material_options(q)`; require login.
  - **Deliverable**: API endpoint returns matching materials.

- [x] **16.7** Add URL route for material search
  - **Do**: In `app/core/urls.py`, add path `api/discharge-material-search/` pointing to `discharge_material_search_api` view.
  - **Deliverable**: Endpoint accessible at `/core/api/discharge-material-search/`.
  - **Verify**: `python manage.py show_urls` shows new path.

### Service Layer

- [x] **16.8** Update create_discharge_test signature
  - **Do**: In `discharge_testing_services.py`, update `create_discharge_test` to accept optional `discharge_material_code` parameter.
  - **Deliverable**: Function accepts new parameter.

- [x] **16.9** Add material validation
  - **Do**: In `discharge_testing_services.py`, add validation in `create_discharge_test`: if `discharge_type` is 'Acid' or 'Base', require `discharge_material_code` to be non-empty; raise `ValidationError` with key `discharge_material_code` if missing.
  - **Deliverable**: Service validates material requirement.

- [x] **16.10** Assign material field to model
  - **Do**: In `discharge_testing_services.py`, in `create_discharge_test`, assign `discharge_material_code` to the `DischargeTestingRecord` instance before save.
  - **Deliverable**: Material field saved to database.

- [x] **16.11** Update service serialization
  - **Do**: In `discharge_testing_services.py`, update `_serialize_discharge_test` to include `discharge_material_code` in returned dict.
  - **Deliverable**: WebSocket broadcasts include material field.

### API View Updates

- [x] **16.12** Update API payload handling
  - **Do**: In `app/core/views/api.py`, update `discharge_testing_list_api` POST handler to extract `discharge_material_code` from payload and pass to `create_discharge_test`.
  - **Deliverable**: API accepts material field.

- [x] **16.13** Update API serialization
  - **Do**: In `app/core/views/api.py`, update `_serialize_flush_tote` helper to include `discharge_material_code` in output.
  - **Deliverable**: API GET responses include material field.

### Template Layer

- [x] **16.14** Add material autocomplete field to entry form
  - **Do**: In `discharge_testing_entry.html`, add new form group after discharge_type: label "Discharge Material", text input with `id="discharge-testing-entry-discharge-material"` for display, hidden input `id="discharge-testing-entry-discharge-material-code"` with `name="discharge_material_code"`, autocomplete results container div; wrap in container with `data-role="discharge-material-group"`.
  - **Deliverable**: Material field structure in template.

- [x] **16.15** Add conditional visibility styling
  - **Do**: In `discharge_testing_entry.html`, add `style="display: none;"` to discharge-material-group container (JS will show/hide based on discharge_type).
  - **Deliverable**: Field hidden by default.

### JavaScript Layer - Field Setup

- [x] **16.16** Add material field element references
  - **Do**: In `DischargeTestingEntry.js`, in constructor, add references: `this.dischargeMaterialGroup`, `this.dischargeMaterialInput` (display input), `this.dischargeMaterialCode` (hidden), `this.dischargeMaterialResults` (autocomplete dropdown).
  - **Deliverable**: Element references in class.

- [x] **16.17** Add material field constants
  - **Do**: In `DischargeTestingEntry.js`, add `const MATERIAL_SEARCH_ENDPOINT = '/core/api/discharge-material-search/';` and `const ACID_BASE_TYPES = ['Acid', 'Base'];`.
  - **Deliverable**: Constants defined.

### JavaScript Layer - Visibility Logic

- [x] **16.18** Add discharge_type change handler
  - **Do**: In `DischargeTestingEntry.js`, in `registerEvents`, add change listener on `this.dischargeType` that calls `this.syncMaterialFieldVisibility()`.
  - **Deliverable**: Event listener registered.

- [x] **16.19** Implement syncMaterialFieldVisibility
  - **Do**: In `DischargeTestingEntry.js`, add `syncMaterialFieldVisibility()` method: show `dischargeMaterialGroup` if `dischargeType.value` is in `ACID_BASE_TYPES`, hide otherwise; clear material fields when hiding.
  - **Deliverable**: Field visibility toggles correctly.

- [x] **16.20** Call sync on page load
  - **Do**: In `DischargeTestingEntry.js`, in constructor after `registerEvents()`, call `this.syncMaterialFieldVisibility()`.
  - **Deliverable**: Correct initial visibility.

### JavaScript Layer - Autocomplete

- [x] **16.21** Add debounce utility
  - **Do**: In `DischargeTestingEntry.js`, add `debounce(fn, delay)` helper function that returns a debounced version of the function.
  - **Deliverable**: Debounce utility available.

- [x] **16.22** Add material search input handler
  - **Do**: In `DischargeTestingEntry.js`, in `registerEvents`, add debounced input listener on `dischargeMaterialInput` that calls `this.searchMaterials()` with 250ms delay.
  - **Deliverable**: Input triggers debounced search.

- [x] **16.23** Implement searchMaterials
  - **Do**: In `DischargeTestingEntry.js`, add `async searchMaterials()` method: get search term from input; if less than 2 chars, hide results; otherwise fetch from `MATERIAL_SEARCH_ENDPOINT?q=${term}`; call `renderMaterialResults(data.results)`.
  - **Deliverable**: Search fetches and triggers render.

- [x] **16.24** Implement renderMaterialResults
  - **Do**: In `DischargeTestingEntry.js`, add `renderMaterialResults(results)` method: clear results container; if no results, show "No matches" message; otherwise render clickable items with `data-value` (itemcode) and `data-label` (full display string); show container.
  - **Deliverable**: Dropdown displays search results.

- [x] **16.25** Add result item click handler
  - **Do**: In `DischargeTestingEntry.js`, add event delegation on `dischargeMaterialResults` for click on result items; on click, set `dischargeMaterialInput.value` to label, `dischargeMaterialCode.value` to itemcode; hide results; clear field feedback.
  - **Deliverable**: Selection populates fields.

- [x] **16.26** Add click-outside handler
  - **Do**: In `DischargeTestingEntry.js`, add document click listener that hides `dischargeMaterialResults` when clicking outside the autocomplete area.
  - **Deliverable**: Dropdown closes on outside click.

### JavaScript Layer - Validation & Submission

- [x] **16.27** Update collectPayload for material field
  - **Do**: In `DischargeTestingEntry.js`, update `collectPayload()`: if discharge_type is Acid or Base, validate that `dischargeMaterialCode` has a value; add error if missing; include `discharge_material_code` in returned payload.
  - **Deliverable**: Payload includes material; validation enforces requirement.

- [x] **16.28** Update applyValidationErrors for material field
  - **Do**: In `DischargeTestingEntry.js`, update `applyValidationErrors()` to handle `discharge_material_code` error key, applying feedback to `dischargeMaterialInput`.
  - **Deliverable**: Server errors display on material field.

- [x] **16.29** Update resetForm for material fields
  - **Do**: In `DischargeTestingEntry.js`, update `resetForm()` to clear `dischargeMaterialInput`, `dischargeMaterialCode`, hide results dropdown, and call `syncMaterialFieldVisibility()`.
  - **Deliverable**: Reset clears material state.

### Records View Updates

- [x] **16.30** Add material column to records table
  - **Do**: In `discharge_testing_records.html`, add table column header "Discharge Material"; in row template, display `discharge_material_code` (or empty if null).
  - **Deliverable**: Records table shows material code.

- [x] **16.31** Update DischargeTestingRecords.js for material display
  - **Do**: In `DischargeTestingRecords.js`, update row rendering to include `discharge_material_code`; no inline edit for this field (read-only in records view).
  - **Deliverable**: Records JS renders material correctly.

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
| 16. Acid/Base Material Autocomplete | Complete | 31/31 |

**Overall**: 99/99 tasks (100%)

---

## Phase 17: pH Active Component Tracking

_Auto-detect and record which specific material caused pH deviation. When discharge_material_code matches a watch list item (directly or as a blend component), store the matching item code in ph_active_component._

**Watch List**: `030050`, `030015`, `030024`, `200126`, `030025`, `240079`

### Model Changes

- [x] **17.1** Define PH_ACTIVE_WATCH_CODES constant
  - **Do**: In `app/core/models.py`, add `PH_ACTIVE_WATCH_CODES = ('030050', '030015', '030024', '200126', '030025', '240079')` tuple constant to `DischargeTestingRecord` class.
  - **Deliverable**: Constant defined on model class.

- [x] **17.2** Add `ph_active_component` field
  - **Do**: In `app/core/models.py`, add `ph_active_component = models.CharField(max_length=50, blank=True, null=True)` to `DischargeTestingRecord` model; stores the itemcode of the pH-affecting material.
  - **Deliverable**: Field added to model.

- [x] **17.3** Create migration
  - **Do**: Create migration for new field.
  - **Verify**: `python manage.py makemigrations` succeeds.

- [x] **17.4** Apply migration (delegate to user)
  - **Do**: Prompt user to run migrations.
  - **Verify**: Migration applies cleanly.

### Selector Layer

- [x] **17.5** Create selector to find pH active component from BOM
  - **Do**: In `discharge_testing_selectors.py`, add `find_ph_active_component(material_code: str) -> Optional[str]` function: first check if `material_code` is directly in `DischargeTestingRecord.PH_ACTIVE_WATCH_CODES`, return it if so; otherwise query `bill_of_materials` table where `parent_item_code = material_code` and `component_item_code` is in watch list; return first match or None.
  - **Deliverable**: Selector function returns matching watch list code or None.

- [x] **17.6** Update selector exports
  - **Do**: In `app/core/selectors/__init__.py`, add `find_ph_active_component` to imports and exports.
  - **Deliverable**: Function exported from selectors package.

### Service Layer

- [x] **17.7** Import selector in service
  - **Do**: In `discharge_testing_services.py`, add `find_ph_active_component` to imports from selectors.
  - **Deliverable**: Import statement added.

- [x] **17.8** Add ph_active_component logic in create_discharge_test
  - **Do**: In `discharge_testing_services.py`, in `create_discharge_test`, after setting `discharge_material_code`, call `find_ph_active_component(cleaned_material_code)` and assign result to `tote.ph_active_component` if not None.
  - **Deliverable**: Service auto-populates ph_active_component on create.

- [x] **17.9** Update service serialization
  - **Do**: In `discharge_testing_services.py`, update `_serialize_discharge_test` to include `ph_active_component` in returned dict.
  - **Deliverable**: WebSocket broadcasts include ph_active_component.

### API View Updates

- [x] **17.10** Update API serialization
  - **Do**: In `app/core/views/api.py`, update `_serialize_flush_tote` helper to include `ph_active_component` in output.
  - **Deliverable**: API GET responses include ph_active_component.

### Records View Updates

- [x] **17.11** Add column to records table
  - **Do**: In `discharge_testing_records.html`, add table column header "pH Active Component"; in row template, display `ph_active_component` value (or empty/dash if null).
  - **Deliverable**: Records table shows ph_active_component.

- [x] **17.12** Update DischargeTestingRecords.js for display
  - **Do**: In `DischargeTestingRecords.js`, update row rendering to include `ph_active_component`; read-only field (no inline edit).
  - **Deliverable**: Records JS renders ph_active_component correctly.

---

## Phase 18: Form UX Enhancements

_Two enhancements: (1) Show bold alert when a pH-active component is detected in the selected material. (2) Hide pH and Action Required fields when discharge type is Oil._

### pH Active Component Alert

- [x] **18.1** Add API endpoint to check pH active component
  - **Do**: In `app/core/views/api.py`, add `discharge_material_ph_check_api(request)` view; accept GET with `code` query param; use `find_ph_active_component(code)` selector; return JSON `{"status": "ok", "ph_active_component": "<code or null>"}`.
  - **Deliverable**: Endpoint returns detected component.

- [x] **18.2** Add URL route for pH check
  - **Do**: In `app/core/urls.py`, add path `api/discharge-material-ph-check/` pointing to `discharge_material_ph_check_api`.
  - **Deliverable**: Endpoint accessible.

- [x] **18.3** Add alert container to template
  - **Do**: In `discharge_testing_entry.html`, add alert container inside form: `<div id="discharge-testing-entry-ph-alert" class="alert alert-warning fw-bold" style="display: none;" role="alert"></div>` positioned after discharge material group.
  - **Deliverable**: Alert container in template (hidden by default).

- [x] **18.4** Add alert element reference
  - **Do**: In `DischargeTestingEntry.js`, add `this.phAlert = document.getElementById('discharge-testing-entry-ph-alert');` in constructor.
  - **Deliverable**: Element reference available.

- [x] **18.5** Add constant for pH check endpoint
  - **Do**: In `DischargeTestingEntry.js`, add `const PH_CHECK_ENDPOINT = '/core/api/discharge-material-ph-check/';`.
  - **Deliverable**: Constant defined.

- [x] **18.6** Implement checkPhActiveComponent method
  - **Do**: In `DischargeTestingEntry.js`, add `async checkPhActiveComponent(materialCode)` method: fetch from `PH_CHECK_ENDPOINT?code=${materialCode}`; if response has `ph_active_component`, call `showPhAlert(code)`; otherwise call `hidePhAlert()`.
  - **Deliverable**: Method checks and triggers alert.

- [x] **18.7** Implement showPhAlert method
  - **Do**: In `DischargeTestingEntry.js`, add `showPhAlert(componentCode)` method: set `phAlert.textContent` to warning message like `"⚠️ pH-affecting material detected: ${componentCode}"`; set `phAlert.style.display = 'block'`.
  - **Deliverable**: Alert displays with component code.

- [x] **18.8** Implement hidePhAlert method
  - **Do**: In `DischargeTestingEntry.js`, add `hidePhAlert()` method: set `phAlert.style.display = 'none'`; clear `textContent`.
  - **Deliverable**: Alert hides.

- [x] **18.9** Call checkPhActiveComponent on material selection
  - **Do**: In `DischargeTestingEntry.js`, in the material result click handler (after setting `dischargeMaterialCode.value`), call `this.checkPhActiveComponent(value)`.
  - **Deliverable**: Alert triggers on material selection.

- [x] **18.10** Hide alert when material cleared
  - **Do**: In `DischargeTestingEntry.js`, update `syncMaterialFieldVisibility()` to call `this.hidePhAlert()` when hiding material group.
  - **Deliverable**: Alert clears when discharge type changes.

- [x] **18.11** Clear alert on form reset
  - **Do**: In `DischargeTestingEntry.js`, update `resetForm()` to call `this.hidePhAlert()`.
  - **Deliverable**: Alert clears on reset.

### Oil Discharge Type - Hide pH Fields

- [x] **18.12** Add pH fields group wrapper in template
  - **Do**: In `discharge_testing_entry.html`, wrap Initial pH, Final pH, and Action Required fields in a container `<div data-role="ph-fields-group">...</div>`.
  - **Deliverable**: pH-related fields wrapped in identifiable container.

- [x] **18.13** Add phFieldsGroup element reference
  - **Do**: In `DischargeTestingEntry.js`, add `this.phFieldsGroup = this.form ? this.form.querySelector('[data-role="ph-fields-group"]') : null;` in constructor.
  - **Deliverable**: Element reference available.

- [x] **18.14** Add OIL_TYPE constant
  - **Do**: In `DischargeTestingEntry.js`, add `const OIL_TYPE = 'Oil';` near other type constants.
  - **Deliverable**: Constant defined.

- [x] **18.15** Implement syncPhFieldsVisibility method
  - **Do**: In `DischargeTestingEntry.js`, add `syncPhFieldsVisibility()` method: if `dischargeType.value === OIL_TYPE`, hide `phFieldsGroup` and clear pH/action fields; otherwise show `phFieldsGroup`.
  - **Deliverable**: pH fields hide/show based on type.

- [x] **18.16** Call syncPhFieldsVisibility on discharge type change
  - **Do**: In `DischargeTestingEntry.js`, in the discharge type change handler, add call to `this.syncPhFieldsVisibility()`.
  - **Deliverable**: Visibility syncs on type change.

- [x] **18.17** Call syncPhFieldsVisibility on page load
  - **Do**: In `DischargeTestingEntry.js`, in constructor after `registerEvents()`, add call to `this.syncPhFieldsVisibility()`.
  - **Deliverable**: Correct initial visibility.

- [x] **18.18** Skip pH validation when Oil selected
  - **Do**: In `DischargeTestingEntry.js`, update `collectPayload()`: if `dischargeType === OIL_TYPE`, skip pH and action_required validation; set pH values to null in payload.
  - **Deliverable**: No pH validation errors for Oil type.

- [x] **18.19** Update service validation for Oil type
  - **Do**: In `discharge_testing_services.py`, update `create_discharge_test`: if `discharge_type == 'Oil'`, skip pH range validation and action_required requirement.
  - **Deliverable**: Server allows null pH for Oil.

---

## Phase 19: pH Alert Description Enhancement

_Include itemcodedesc in the pH active component alert for better user context._

### Selector Layer

- [x] **19.1** Update selector to return description
  - **Do**: In `discharge_testing_selectors.py`, update `find_ph_active_component` to return a dict `{'code': itemcode, 'description': itemcodedesc}` instead of just the code string; return `None` if no match; look up description from `CiItem` for the matched code.
  - **Deliverable**: Selector returns code and description.

- [x] **19.2** Update selector in service layer
  - **Do**: In `discharge_testing_services.py`, update usage of `find_ph_active_component`: extract `['code']` from returned dict when assigning to `tote.ph_active_component`.
  - **Deliverable**: Service handles new return format.

### API Layer

- [x] **19.3** Update pH check API response
  - **Do**: In `app/core/views/api.py`, update `discharge_material_ph_check_api` to return both fields: `{"status": "ok", "ph_active_component": "<code or null>", "ph_active_component_desc": "<description or null>"}`.
  - **Deliverable**: API returns code and description.

### JavaScript Layer

- [x] **19.4** Update showPhAlert to display description
  - **Do**: In `DischargeTestingEntry.js`, update `showPhAlert(componentCode, componentDesc)` to accept description parameter; display message like `"⚠️ pH-affecting material detected: ${componentCode}: ${componentDesc}"`.
  - **Deliverable**: Alert shows full item info.

- [x] **19.5** Update checkPhActiveComponent to pass description
  - **Do**: In `DischargeTestingEntry.js`, update `checkPhActiveComponent` to extract `ph_active_component_desc` from response and pass to `showPhAlert(code, desc)`.
  - **Deliverable**: Description flows through to alert.

---

## Phase 20: Admin Row Deletion on Records Page

_Allow admin users to delete discharge testing records via a trash button in the records table._

### API Layer

- [x] **20.1** Add DELETE handler to detail API
  - **Do**: In `app/core/views/api.py`, update `discharge_testing_detail_api` to handle DELETE method; check `request.user.is_staff` or `is_superuser`; return 403 if not admin; delete record and return `{"status": "ok"}`.
  - **Deliverable**: API supports DELETE for admins.

- [x] **20.2** Return 403 for non-admin DELETE
  - **Do**: Ensure DELETE returns `{"status": "error", "error": "Permission denied"}` with 403 status for non-admin users.
  - **Deliverable**: Permission enforced server-side.

### Service Layer

- [x] **20.3** Create delete_discharge_test service function
  - **Do**: In `discharge_testing_services.py`, add `delete_discharge_test(tote_id: int, user: User)` function; verify user is admin; delete record; optionally broadcast deletion event.
  - **Deliverable**: Service function handles deletion logic.

### Template Layer

- [x] **20.4** Add delete button column to records table
  - **Do**: In `discharge_testing_records.html`, add column header (empty or icon); in row template, add delete button with trash icon: `<button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="{{ record.id }}"><i class="fas fa-trash"></i></button>`.
  - **Deliverable**: Trash button visible in each row.

- [x] **20.5** Conditionally show delete button for admins only
  - **Do**: In `discharge_testing_records.html`, wrap delete button in `{% if user.is_staff %}...{% endif %}` to hide from non-admin users.
  - **Deliverable**: Button only visible to staff/superusers.

### JavaScript Layer

- [x] **20.6** Add delete button click handler
  - **Do**: In `DischargeTestingRecords.js`, add event delegation for `[data-action="delete"]` clicks; extract `data-id` from button.
  - **Deliverable**: Click events captured.

- [x] **20.7** Implement confirmation dialog
  - **Do**: In `DischargeTestingRecords.js`, on delete click, show `confirm("Are you sure you want to delete this record?")` dialog; proceed only if confirmed.
  - **Deliverable**: User must confirm before deletion.

- [x] **20.8** Implement deleteRecord method
  - **Do**: In `DischargeTestingRecords.js`, add `async deleteRecord(id)` method; send DELETE request to `/core/api/discharge-testing/${id}/`; on success, remove row from DOM; show success toast.
  - **Deliverable**: Record deleted and UI updated.

- [x] **20.9** Handle delete errors
  - **Do**: In `DischargeTestingRecords.js`, in `deleteRecord`, catch errors; show error toast with message; do not remove row on failure.
  - **Deliverable**: Errors displayed to user.

---

## Phase 21: Polish Type Behaves Like Oil (pH-Exempt)

_Polish discharge type should hide pH fields, skip pH validation, and bypass action required — identical to Oil behavior._

**Analysis:** Oil-specific behavior is controlled by exactly 2 variables across 2 files. Both use a single check that gates all downstream logic, so the fix is changing 2 comparisons from single-value to set membership.

**No changes needed in:** `api.py` (delegates to services), `models.py` (constraints already allow null pH), `DischargeTestingRecords.js` (no type-specific logic), HTML templates (no Oil-specific logic). `syncMaterialFieldVisibility()` uses `ACID_BASE_TYPES = ['Acid', 'Base']` — Polish is already excluded, so the material field correctly stays hidden.

### Entry Page JS (`DischargeTestingEntry.js`)

- [x] **21.1** Replace `OIL_TYPE` constant with pH-exempt set
  - **Do**: Replace `const OIL_TYPE = 'Oil';` (line 5) with `const PH_EXEMPT_TYPES = ['Oil', 'Polish'];`
  - **Deliverable**: Constant updated.

- [x] **21.2** Update `syncPhFieldsVisibility()` to use pH-exempt set
  - **Do**: Change `dischargeTypeValue === OIL_TYPE` (line 331) to `PH_EXEMPT_TYPES.includes(dischargeTypeValue)`. This controls hiding pH fields group, clearing pH/action values, and removing required attributes.
  - **Deliverable**: Selecting Polish hides Initial pH, Final pH, and Action Required fields.

- [x] **21.3** Update `collectPayload()` to use pH-exempt set
  - **Do**: Change `dischargeType === OIL_TYPE` (line 599) to `PH_EXEMPT_TYPES.includes(dischargeType)`. The resulting variable gates all downstream pH skip logic (lines 602, 625, 639, 653), so no further changes needed in this method.
  - **Deliverable**: Polish submissions skip pH parsing, pH required validation, out-of-range checks, and action required enforcement.

### Service Layer (`discharge_testing_services.py`)

- [x] **21.4** Update `create_discharge_test()` to treat Polish as pH-exempt
  - **Do**: Change `cleaned_discharge_type.lower() == "oil"` (line 131) to `cleaned_discharge_type.lower() in {"oil", "polish"}`. The resulting variable gates all downstream logic (lines 138, 147, 151), so no further changes needed.
  - **Deliverable**: Server accepts Polish submissions without pH values and nullifies action_required.

### Testing

- [x] **21.5** Test: Selecting Polish hides pH fields and Action Required on entry form
- [x] **21.6** Test: Submitting Polish type without pH values succeeds
- [x] **21.7** Test: Switching from Polish to Acid re-shows pH fields and restores required
- [x] **21.8** Test: Polish record created with null pH values in database

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
| 16. Acid/Base Material Autocomplete | Complete | 31/31 |
| 17. pH Active Component Tracking | Complete | 12/12 |
| 18. Form UX Enhancements | Complete | 19/19 |
| 19. pH Alert Description Enhancement | Complete | 5/5 |
| 20. Admin Row Deletion | Complete | 14/14 |
| 21. Polish pH-Exempt | Pending | 4/8 |
| 22. Hide Entry Fields (Reversible) | Complete | 6/6 |

**Overall**: 159/163 tasks (97%)

---

## Phase 22: Hide Entry Fields (Reversible)

_Quick-and-dirty hiding of discharge_material_code, ph_active_component, action_required, and final_disposition from the entry form. Fields kept in code/template for easy reactivation. Null allowed on all four._

**Reason**: Users are indecisive — fields may come back. All hidden with `display: none !important` and validation bypassed rather than removed.

- [x] **22.1** Make final_disposition nullable in model
  - **Do**: In `app/core/models.py`, change `final_disposition = models.TextField()` to `models.TextField(blank=True, null=True)`. Other three fields already nullable.
  - **Deliverable**: Migration needed.

- [x] **22.2** Hide fields in entry template
  - **Do**: In `discharge_testing_entry.html`, add `style="display: none !important;"` to discharge-material-group, ph-alert, action-required-group, and final-disposition wrapper. Remove `required` from final_disposition textarea.
  - **Deliverable**: Fields invisible on page load and immune to JS show/hide.

- [x] **22.3** Disable JS validation for hidden fields
  - **Do**: In `DischargeTestingEntry.js`, remove `final_disposition` required error, skip `discharge_material_code` acid/base required error, skip `action_required` out-of-range required error.
  - **Deliverable**: Form submits without hidden fields populated.

- [x] **22.4** Prevent JS from showing material group
  - **Do**: In `DischargeTestingEntry.js`, set `shouldShow = false` in `syncMaterialFieldVisibility()` so acid/base selection never reveals the material autocomplete.
  - **Deliverable**: Material field stays hidden regardless of discharge type.

- [x] **22.5** Remove server-side required checks for hidden fields
  - **Do**: In `discharge_testing_services.py`, remove `final_disposition` required ValidationError, remove `discharge_material_code` acid/base required ValidationError, remove `action_required` out-of-range required ValidationError. Make `final_disposition` parameter optional.
  - **Deliverable**: Server accepts submissions with all four fields null/empty.

- [x] **22.6** Create and apply migration for final_disposition
  - **Do**: Run `makemigrations` and `migrate` to apply nullable change.
  - **Deliverable**: Database allows null final_disposition.

### Reactivation Guide

To restore any of these fields:
1. **Template**: Remove `style="display: none !important;"` from the field's wrapper div. Re-add `required` attribute if needed.
2. **JS**: Restore validation checks in `collectPayload()`. For material field, change `shouldShow = false` back to `shouldShow = ACID_BASE_TYPES.includes(dischargeTypeValue)`.
3. **Service**: Restore `ValidationError` checks in `create_discharge_test()`. Change `final_disposition` param back to required `str`.
4. **Model**: If restoring `final_disposition` as required, change back to `models.TextField()` and backfill existing null rows.

---

**Status**: In Progress
