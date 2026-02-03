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

- [ ] **6.4** Remove counting unit from inline edit logic
  - **Do**: In `app/core/static/core/js/pageModules/itemsByAuditGroup.js`:
    - Remove `countingUnitChoices` variable (line 168: `const countingUnitChoices = window.COUNTING_UNIT_CHOICES || [];`)
    - In `getRowSnapshot()` (line 63-74): remove the `countingUnitCell` query and `snapshot.counting_unit` assignment
    - In `enterEditMode()` (line 199-234): remove the `countingUnitCell` variable, the `countingUnitSelect` creation, and the lines that clear/append to `countingUnitCell`. Remove `countingUnitCell` from the null guard on line 216.
    - In `exitEditMode()` (line 172-197): remove the `countingUnitCell` query and the block that sets its `textContent`
    - In `handleSave()` (line 236-271): remove the `countingUnitSelect` query, remove `counting_unit` from the payload object, remove `countingUnitSelect` from the null guard on line 243, and remove `counting_unit` from the `exitEditMode` updatedValues object
  - **Deliverable**: Inline edit only manages audit_group; counting_unit is not referenced in JS

- [ ] **6.5** Restrict DataTables sorting to columns 1, 4, 5, 7, 8 only
  - **Do**: In `app/core/static/core/js/pageModules/itemsByAuditGroup.js`, replace the current `nonSortableColumns` logic (lines 151-157) and the `columnDefs` in `initDataTableWithExport` (lines 160-165). After Count Unit removal, the staff table has 10 columns (0-9) and non-staff has 9 columns (0-8). The sortable columns by header name are: Item, Next Run, Latest Txn, Last Count, Audit Group.

    For staff (with checkbox col 0): sortable indices are 1, 4, 5, 7, 8. Non-sortable: 0, 2, 3, 6, 9.
    For non-staff (no checkbox): sortable indices are 0, 3, 4, 6, 7. Non-sortable: 1, 2, 5, 8.

    Replace the `nonSortableColumns` block and `columnDefs` with logic that computes non-sortable indices based on `hasSelectColumn`:
    ```js
    const nonSortableColumns = hasSelectColumn
        ? [0, 2, 3, 6, 9]
        : [1, 2, 5, 8];
    ```
    Keep the existing `order` line using `itemColumnIndex`.
  - **Deliverable**: Sort chevrons appear only on Item, Next Run, Latest Txn, Last Count, and Audit Group columns. All other columns show no sort indicator.

### Testing

- [ ] **6.6** Test: Column removal and sorting
  - Navigate to `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent` as a staff user
  - Verify Count Unit column is gone from the table
  - Verify sort chevrons appear only on Item, Next Run, Latest Txn, Last Count, Audit Group headers
  - Click each sortable header — rows should reorder
  - Click a non-sortable header (Description, On Hand, Code) — nothing should happen
- [ ] **6.7** Test: Inline edit still works without counting unit
  - Click the edit pencil on a row
  - Verify only the Audit Group dropdown appears (no Count Unit dropdown)
  - Change audit group, click Save — should succeed
  - Verify the saved value persists after page reload
- [ ] **6.8** Test: Non-staff view
  - Log in as a non-staff user and navigate to the same page
  - Verify no checkbox column, no Count Unit column, correct sort chevrons

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 6. Remove Count Unit & Restrict Sorting | Not Started | 0/8 |

**Overall**: 0/8 tasks (0%)

---

**Status**: Draft
