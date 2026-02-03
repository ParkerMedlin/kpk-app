# Audit Group Inline Edit – Change Orders

## Overview

Change orders for the audit group inline edit feature after initial implementation.

**Parent**: See `tasks.md` for completed Phase 1–5 work.

---

## Phase 6: Remove Count Unit Column and Restrict Sorting

_Remove the counting unit column from the table display and inline edit UI. Restrict DataTables sorting chevrons to only the Item, Next Run, Latest Txn, Last Count, and Audit Group columns._

**Analysis:** The counting unit column is displayed and editable inline but is not needed on this page. The `counting_unit` field remains in the model and form — this change is UI-only. DataTables currently marks all columns except checkbox (col 0) and actions (last col) as sortable, which adds sort chevrons to columns where sorting isn't useful (Description, On Hand, Code). After removing Count Unit, the table has 10 columns for staff (with checkbox) and 9 for non-staff.

**No changes needed in:**
- `app/core/forms.py` — `AuditGroupForm` keeps `counting_unit` in its fields (the API merge logic uses it as a fallback for existing values)
- `app/core/services/inventory_services.py` — API endpoints unchanged; `counting_unit` omitted from payload will default to existing value on update
- `app/core/urls.py` — No route changes

### Template

- [x] **6.1** Remove Count Unit header and cells from table
  - **Do**: In `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`:
    - Remove the `<th>` for "Count Unit" (line 61)
    - Remove the `<td data-field="counting_unit">` cell from the `{% for %}` loop (line 84)
  - **Deliverable**: Table renders without a Count Unit column

- [x] **6.2** Remove counting_unit_choices JSON embed from template
  - **Do**: In `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`:
    - Remove line 10: `{{ counting_unit_choices|json_script:"counting-unit-choices" }}`
    - Remove line 13: `window.COUNTING_UNIT_CHOICES = JSON.parse(document.getElementById('counting-unit-choices').textContent);`
  - **Deliverable**: No counting unit data embedded in the page

### View

- [x] **6.3** Remove counting_unit_choices from view context
  - **Do**: In `app/core/views/web.py`, in the `display_items_by_audit_group` function:
    - Remove the `counting_unit_choices` list definition (lines 884-905)
    - Remove `'counting_unit_choices': counting_unit_choices` from the context dict (line 910)
  - **Deliverable**: View no longer passes counting unit choices to the template

### JavaScript

- [x] **6.4** Remove counting unit from inline edit logic
  - **Do**: In `app/core/static/core/js/pageModules/itemsByAuditGroup.js`:
    - Remove `countingUnitChoices` variable (line 168: `const countingUnitChoices = window.COUNTING_UNIT_CHOICES || [];`)
    - In `getRowSnapshot()` (line 63-74): remove the `countingUnitCell` query and `snapshot.counting_unit` assignment
    - In `enterEditMode()` (line 199-234): remove the `countingUnitCell` variable, the `countingUnitSelect` creation, and the lines that clear/append to `countingUnitCell`. Remove `countingUnitCell` from the null guard on line 216.
    - In `exitEditMode()` (line 172-197): remove the `countingUnitCell` query and the block that sets its `textContent`
    - In `handleSave()` (line 236-271): remove the `countingUnitSelect` query, remove `counting_unit` from the payload object, remove `countingUnitSelect` from the null guard on line 243, and remove `counting_unit` from the `exitEditMode` updatedValues object
  - **Deliverable**: Inline edit only manages audit_group; counting_unit is not referenced in JS

- [x] **6.5** Restrict DataTables sorting to columns 1, 4, 5, 7, 8 only
  - **Do**: In `app/core/static/core/js/pageModules/itemsByAuditGroup.js`, replace the current `nonSortableColumns` logic (lines 151-157) and the `columnDefs` in `initDataTableWithExport` (lines 160-165). The sortable columns by header name are: Item, Next Run, Latest Txn, Last Count, Audit Group.

    **NOTE**: These indices assume the Actions column has been removed (Phase 7). After both Count Unit and Actions columns are removed, staff table has 9 columns (0-8) and non-staff has 8 columns (0-7). If the Actions column still exists when this task was executed, the non-sortable arrays will need updating after Phase 7 completes.

    For staff (with checkbox col 0): sortable indices are 1, 4, 5, 7, 8. Non-sortable: 0, 2, 3, 6.
    For non-staff (no checkbox): sortable indices are 0, 3, 4, 6, 7. Non-sortable: 1, 2, 5.

    Replace the `nonSortableColumns` block and `columnDefs` with logic that computes non-sortable indices based on `hasSelectColumn`:
    ```js
    const nonSortableColumns = hasSelectColumn
        ? [0, 2, 3, 6]
        : [1, 2, 5];
    ```
    Keep the existing `order` line using `itemColumnIndex`.
  - **Deliverable**: Sort chevrons appear only on Item, Next Run, Latest Txn, Last Count, and Audit Group columns. All other columns show no sort indicator.

### Testing

- [x] **6.6** Test: Column removal and sorting
  - Navigate to `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent` as a staff user
  - Verify Count Unit column is gone from the table
  - Verify sort chevrons appear only on Item, Next Run, Latest Txn, Last Count, Audit Group headers
  - Click each sortable header — rows should reorder
  - Click a non-sortable header (Description, On Hand, Code) — nothing should happen
- [x] **6.7** Test: Inline edit still works without counting unit
  - Click the edit pencil on a row
  - Verify only the Audit Group dropdown appears (no Count Unit dropdown)
  - Change audit group, click Save — should succeed
  - Verify the saved value persists after page reload
- [x] **6.8** Test: Non-staff view
  - Log in as a non-staff user and navigate to the same page
  - Verify no checkbox column, no Count Unit column, correct sort chevrons

---

## Phase 7: Merge Actions into Audit Group Column and Table Styling

_Move the edit/save/cancel controls into the Audit Group column (eliminating the separate Actions column) and add horizontal row borders. Style the edit icon in a muted blue._

**Analysis:** The Actions column currently holds only a pencil icon (display mode) or Save/Cancel buttons (edit mode). Moving these into the Audit Group cell simplifies the table layout and removes one column. The JS functions `renderEditButton`, `renderSaveCancelButtons`, `enterEditMode`, `exitEditMode`, and `getRowSnapshot` all reference a separate `[data-field="actions"]` cell — these need to operate within the `[data-field="audit_group"]` cell instead. The template also needs the `<th>` and `<td>` for the actions column removed.

**No changes needed in:**
- `app/core/views/web.py` — No context changes
- `app/core/services/inventory_services.py` — API unchanged
- `app/core/urls.py` — No route changes

### Template

- [x] **7.1** Remove the Actions column header and cells
  - **Do**: In `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`:
    - Remove the empty `<th scope="col" class='text-center'></th>` (currently line 62, the last `<th>`)
    - Remove the entire `<td class="text-center" data-field="actions">...</td>` block (currently lines 84-88)
  - **Deliverable**: Table has no Actions column

- [x] **7.2** Add edit button inline within the Audit Group cell
  - **Do**: In `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`, change the audit group `<td>` (currently line 83) from:
    ```html
    <td data-field="audit_group">{{ item.audit_group }}</td>
    ```
    to:
    ```html
    <td data-field="audit_group">
        <span class="audit-group-value">{{ item.audit_group }}</span>
        <button type="button" class="btn btn-link editRowButton p-0 ms-1">
            <i class="fa fa-pencil" aria-hidden="true"></i>
        </button>
    </td>
    ```
  - **Deliverable**: Pencil icon appears next to audit group text in each row

### CSS

- [x] **7.3** Add horizontal row borders and style the edit icon
  - **Do**: In `app/core/static/core/css/itemsByAuditGroup.css`, add:
    ```css
    #displayTable td {
        border-bottom: 1px solid #dee2e6;
    }

    .editRowButton {
        color: #8cb4d5;
    }

    .editRowButton:hover {
        color: #5a9bd5;
    }
    ```
  - **Deliverable**: Every row has a visible bottom border; pencil icon is a washed-out blue that darkens on hover

### JavaScript

- [x] **7.4** Remove all `actionsCell` / `data-field="actions"` references from inline edit logic
  - **Do**: In `app/core/static/core/js/pageModules/itemsByAuditGroup.js`:
    - **`getRowSnapshot()`**: Remove the `actionsCell` query and `snapshot.actionsHtml` assignment. The snapshot only needs `audit_group`.
    - **`renderEditButton(actionsCell)`**: Change the function signature to `renderEditButton(auditGroupCell, textValue)`. Instead of clearing `innerHTML` and appending just a button, it should:
      1. Clear the cell
      2. Create a `<span class="audit-group-value">` with `textValue` as `textContent`
      3. Append the span
      4. Create the edit button (existing code)
      5. Add class `ms-1` to the button
      6. Append the button
    - **`renderSaveCancelButtons(actionsCell)`**: Change signature to `renderSaveCancelButtons(container)` (no logic change needed — it clears `innerHTML` and appends buttons, which now happens within a wrapper inside the audit group cell).
    - **`enterEditMode(row)`**: Remove the `actionsCell` query. Remove `actionsCell` from the null guard. After appending the `auditGroupSelect` to `auditGroupCell`, create a wrapper `<div class="d-flex align-items-center gap-1 mt-1">` and call `renderSaveCancelButtons` targeting that wrapper, then append the wrapper to `auditGroupCell`.
    - **`exitEditMode(row, snapshot, updatedValues)`**: Remove the `actionsCell` query. Remove the `if (actionsCell) { renderEditButton(actionsCell); }` block. Instead, after setting `auditGroupCell.textContent`, call `renderEditButton(auditGroupCell, updatedValues ? updatedValues.audit_group : snapshot.audit_group)`.
  - **Deliverable**: Edit/save/cancel controls render inside the audit group cell. No references to `data-field="actions"` remain.

- [x] **7.5** Remove `renderEditButton` and `renderSaveCancelButtons` standalone functions if inlined
  - **Do**: If the refactored `renderEditButton` in 7.4 makes the standalone function unnecessary (all rendering consolidated into `enterEditMode`/`exitEditMode`), remove the standalone functions entirely. Otherwise keep them with the updated signatures from 7.4.
  - **Deliverable**: No dead code

### Testing

- [x] **7.6** Test: Edit controls render inside Audit Group column
  - Navigate to `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent` as a staff user
  - Verify pencil icon appears next to each audit group value in a muted blue color
  - Verify there is no separate Actions column
  - Verify every row has a visible horizontal bottom border
- [x] **7.7** Test: Inline edit flow works from within the cell
  - Click the pencil icon — audit group cell should show a dropdown + Save/Cancel buttons, row highlights yellow
  - Click Cancel — row restores to text + pencil icon
  - Click pencil again, change audit group, click Save — value updates, pencil icon returns
  - Click pencil on a different row while one is being edited — previous row should cancel
- [x] **7.8** Test: Non-staff view
  - Log in as a non-staff user
  - Verify no pencil icons appear (or verify they do — depends on whether non-staff should edit)
  - Verify horizontal borders still render

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 6. Remove Count Unit & Restrict Sorting | Complete | 8/8 |
| 7. Merge Actions Column & Table Styling | Not Started | 0/8 |

**Overall**: 8/16 tasks (50%)

---

**Status**: Draft
