# Audit Group Inline Edit — Tasks

## Overview

Implementation tasks for audit group inline editing, DataTables integration, and record-type-filtered dropdown. Work through sequentially.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Selector & Dropdown Filtering

- [ ] **1.1** Filter `get_distinct_audit_groups` by record type
  - **Do**: Add `record_type=None` parameter to `get_distinct_audit_groups()` in `inventory_selectors.py`. When provided, filter queryset by `item_type=record_type` before returning distinct values.
  - **Deliverable**: Updated function in `app/core/selectors/inventory_selectors.py`
  - **Requirement**: Dropdown filtered by recordType

- [ ] **1.2** Pass record type through service layer
  - **Do**: Update both call sites in `build_audit_group_display_items()` in `inventory_services.py` to pass `record_type` to `get_distinct_audit_groups(record_type)`.
  - **Deliverable**: Updated calls in `app/core/services/inventory_services.py`
  - **Requirement**: Dropdown filtered by recordType

## Phase 2: API Endpoints

- [ ] **2.1** Add serializer and API functions
  - **Do**: In `inventory_services.py`, add `_serialize_audit_group(record)`, `update_audit_group_api(request, audit_group_id)`, and `create_audit_group_api(request)` following the container-classification pattern (JSON body, form validation, JsonResponse).
  - **Deliverable**: Three new functions in `app/core/services/inventory_services.py`
  - **Requirement**: Inline editing async save

- [ ] **2.2** Add URL routes
  - **Do**: In `urls.py`, add `path('api/audit-group/<int:audit_group_id>/', inventory_services.update_audit_group_api, name='update-audit-group-api')` and `path('api/audit-group/create/', inventory_services.create_audit_group_api, name='create-audit-group-api')`.
  - **Deliverable**: Two new routes in `app/core/urls.py`

## Phase 3: View Cleanup

- [ ] **3.1** Remove POST handling and modal form from view
  - **Do**: In `display_items_by_audit_group` in `web.py`, remove the `if request.method == 'POST'` block (lines 880-910). Remove `AuditGroupForm` instantiation and `edit_audit_group_form` from context dict. Add `counting_unit_choices` (the static list from the form) to context for the template to embed as JS data.
  - **Deliverable**: Simplified GET-only view in `app/core/views/web.py`
  - **Requirement**: Inline editing replaces modal

## Phase 4: Template Updates

- [ ] **4.1** Add DataTables prerequisites and choice data
  - **Do**: In `itemsbyauditgroup.html`, add `{% include 'core/partials/datatableprerequisites.html' %}` to `{% block scripts %}`. Add a `<script>` block embedding `audit_group_list` and `counting_unit_choices` as JSON variables (`window.AUDIT_GROUP_CHOICES`, `window.COUNTING_UNIT_CHOICES`).
  - **Deliverable**: Updated script block in template

- [ ] **4.2** Add data attributes to table rows and cells
  - **Do**: Add `data-id="{{ item.id|default:'' }}"`, `data-item-code="{{ item.item_code }}"`, `data-item-description="{{ item.item_description }}"`, `data-item-type="{{ item.item_type }}"` to each `<tr>`. Add `data-field="audit_group"` to the audit group `<td>`, `data-field="counting_unit"` to counting unit `<td>`, `data-field="actions"` to the edit button `<td>`.
  - **Deliverable**: Annotated table rows/cells
  - **Requirement**: Inline editing

- [ ] **4.3** Remove modal and text search input
  - **Do**: Remove the entire `#editAuditGroupItemModal` div. Remove the text search `<input>` and Apply/Reset buttons from the filter form (keep the audit group dropdown and recordType hidden input). Remove `data-bs-toggle="modal"` and `data-bs-target` from the edit button; change class to `editRowButton`.
  - **Deliverable**: Simplified template without modal
  - **Requirement**: Inline editing replaces modal

## Phase 5: JavaScript

- [ ] **5.1** Replace page module with DataTables + inline edit
  - **Do**: Rewrite `itemsByAuditGroup.js`:
    - Import `initDataTableWithExport` from `tableObjects.js` (replace `FilterForm`/`DropDownFilter` imports)
    - Keep `CreateCountListButton`, `ShiftSelectCheckBoxes`, `SelectAllCheckBox`, `BlendComponentFilterButton` imports
    - Remove `ItemsByAuditGroupPage` import
    - Call `initDataTableWithExport('#displayTable', { columnDefs })` with non-sortable checkbox (col 0 for staff) and actions (last col) columns
    - Add audit group dropdown auto-submit: `$('#auditGroupLinks').on('change', () => $('#auditGroupFilterForm').submit())`
    - Add inline edit handlers: `enterEditMode(row)`, `exitEditMode(row, snapshot)`, `handleSave(row)` following the containerClassificationRecords pattern
    - `enterEditMode`: snapshot row data, replace `[data-field="audit_group"]` with `<select>` from `window.AUDIT_GROUP_CHOICES`, replace `[data-field="counting_unit"]` with `<select>` from `window.COUNTING_UNIT_CHOICES`, replace actions cell with Save/Cancel buttons, add `table-warning` class
    - `handleSave`: collect values from selects, POST JSON to `/core/api/audit-group/<id>/` (or `/create/` if no data-id), update row on success, alert on error
    - `exitEditMode`: restore cell text from snapshot or new values, remove `table-warning` class
  - **Deliverable**: Rewritten `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
  - **Requirement**: All three requirements

- [ ] **5.2** Remove `ItemsByAuditGroupPage` class from pageObjects.js
  - **Do**: Delete the `ItemsByAuditGroupPage` class definition (lines ~3018-3089) and its export from `pageObjects.js`.
  - **Deliverable**: Cleaned up `app/core/static/core/js/objects/pageObjects.js`

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Selector & Dropdown | Not Started | 0/2 |
| 2. API Endpoints | Not Started | 0/2 |
| 3. View Cleanup | Not Started | 0/1 |
| 4. Template Updates | Not Started | 0/3 |
| 5. JavaScript | Not Started | 0/2 |

**Overall**: 0/10 tasks (0%)

---

**Status**: Draft
