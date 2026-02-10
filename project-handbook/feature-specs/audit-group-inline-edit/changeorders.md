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

## Phase 8: "Add New" Custom Audit Group Option

_Add an "Add New..." option to the audit group dropdown in inline edit mode. When selected, a text input appears for entering a custom audit group name. The new name is saved like any other value — no backend changes needed._

**Analysis:** The backend already accepts arbitrary `audit_group` strings — `AuditGroupForm` is a plain `ModelForm` with no choice validation on the `audit_group` field. The `get_distinct_audit_groups()` selector pulls distinct values from the database, so any newly-saved custom name will automatically appear in the dropdown on future page loads. This is entirely a JS change.

The `buildSelect()` function (lines 21-61) constructs the `<select>` element from `auditGroupChoices`. It needs an "Add New..." sentinel option appended at the end. When that option is selected, a text input replaces the dropdown. The `handleSave()` function (lines 223-255) reads from `[data-field="audit_group"] select` — it needs to also check for a text input when the custom entry flow is active.

**No changes needed in:**
- `app/core/views/web.py` — No context changes
- `app/core/services/inventory_services.py` — API already accepts arbitrary audit_group strings
- `app/core/selectors/inventory_selectors.py` — New values appear automatically via distinct query
- `app/core/urls.py` — No route changes
- `app/core/templates/core/inventorycounts/itemsbyauditgroup.html` — No template changes
- `app/core/static/core/css/itemsByAuditGroup.css` — No CSS changes (text input inherits Bootstrap form-control styling)

### JavaScript

- [x] **8.1** Add "Add New..." sentinel option to `buildSelect()`
  - **File**: `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
  - **Function**: `buildSelect()` (lines 21-61)
  - **Do**: After the `normalizedChoices.forEach(...)` loop (after line 54), append one more option:
    ```js
    const addNewOption = document.createElement('option');
    addNewOption.value = '__add_new__';
    addNewOption.textContent = 'Add New...';
    select.appendChild(addNewOption);
    ```
    Use the sentinel value `__add_new__` so it can be detected on change.
  - **Deliverable**: The audit group dropdown ends with an "Add New..." option in every inline edit row

- [x] **8.2** Show text input when "Add New..." is selected
  - **File**: `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
  - **Function**: `enterEditMode()` (lines 188-221)
  - **Do**: After appending the `auditGroupSelect` to `auditGroupCell` (line 214), add a change listener on the select:
    ```js
    auditGroupSelect.addEventListener('change', () => {
        const existingInput = auditGroupCell.querySelector('.custom-audit-group-input');
        if (auditGroupSelect.value === '__add_new__') {
            if (!existingInput) {
                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'form-control form-control-sm custom-audit-group-input mt-1';
                input.placeholder = 'New audit group name';
                auditGroupCell.insertBefore(input, auditGroupCell.querySelector('.d-flex'));
                input.focus();
            }
        } else if (existingInput) {
            existingInput.remove();
        }
    });
    ```
    This inserts the text input between the select and the Save/Cancel button wrapper. Switching back to a regular option removes the text input.
  - **Deliverable**: Selecting "Add New..." shows a text field; selecting any other option hides it

- [x] **8.3** Read custom value in `handleSave()`
  - **File**: `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
  - **Function**: `handleSave()` (lines 223-255)
  - **Do**: After getting the `auditGroupSelect` (line 228), determine the actual audit group value:
    ```js
    let auditGroupValue;
    const customInput = row.querySelector('[data-field="audit_group"] .custom-audit-group-input');
    if (auditGroupSelect.value === '__add_new__' && customInput) {
        auditGroupValue = customInput.value.trim();
        if (!auditGroupValue) {
            alert('Please enter a name for the new audit group.');
            return;
        }
    } else {
        auditGroupValue = auditGroupSelect.value;
    }
    ```
    Then use `auditGroupValue` instead of `auditGroupSelect.value` in the payload (line 236):
    ```js
    audit_group: auditGroupValue,
    ```
  - **Deliverable**: Saving with "Add New..." selected sends the text input value; empty input is rejected with a message

- [x] **8.4** Add new value to in-memory choices after save
  - **File**: `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
  - **Function**: `handleSave()`, inside the `try` block after `exitEditMode` (after line 251)
  - **Do**: After a successful save with a custom value, push it into `auditGroupChoices` so subsequent inline edits on the same page load include the new option without a page refresh:
    ```js
    if (customInput && auditGroupValue && !auditGroupChoices.includes(auditGroupValue)) {
        auditGroupChoices.push(auditGroupValue);
        auditGroupChoices.sort();
    }
    ```
  - **Deliverable**: A newly-created audit group appears in the dropdown for all subsequent inline edits during the same page session

### Testing

- [x] **8.5** Test: "Add New..." option appears and toggles text input
  - Navigate to `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent` as a staff user
  - Click the pencil icon on any row
  - Verify the dropdown ends with "Add New..."
  - Select "Add New..." — a text input should appear below the dropdown
  - Switch back to an existing audit group — the text input should disappear
- [x] **8.6** Test: Save with custom audit group name
  - Select "Add New...", type a new name (e.g., "TEST GROUP"), click Save
  - Verify the row updates to show the new name
  - Click pencil on another row — verify "TEST GROUP" now appears in the dropdown
  - Reload the page — verify "TEST GROUP" appears in both the inline edit dropdown and the page filter dropdown
- [x] **8.7** Test: Empty custom name rejected
  - Select "Add New...", leave the text field empty, click Save
  - Verify an alert appears asking for a name
  - Verify the row stays in edit mode
- [x] **8.8** Test: Cancel with "Add New..." active
  - Select "Add New...", type something in the text field, click Cancel
  - Verify the row restores to its original value with no custom input visible

---

## Phase 9: Create Count List from Audit Group

_Add a button that opens a modal where the user selects an audit group and names the count list. Submitting the modal creates a count list containing all items in that group — no manual checkbox selection needed._

**Analysis:** The existing `add_count_list` endpoint (`/core/count-list/add/`) accepts `itemsToAdd` (base64-encoded item codes), `recordType`, and creates count records + a `CountCollectionLink`. The `collection_name` is currently auto-generated as `{record_type}_count_{now_str}`. To support a user-provided name, we'll add an optional `collectionName` query parameter — when present, the backend uses it instead of the auto-generated name. The item codes for a given audit group can be resolved on the backend via a new endpoint that returns item codes for a group, or on the frontend from the table DOM. The backend approach is more reliable since it includes items not currently visible (pagination/filtering), so we'll add a lightweight API endpoint that accepts an audit group name and record type, resolves the item codes, and delegates to the existing `add_count_records` flow.

**Approach:**
1. New API endpoint `POST /core/api/count-list-from-group/` that accepts `{ audit_group, record_type, collection_name }`
2. Backend queries `AuditGroup` for all item codes in that group, then calls existing `add_count_records()` + creates `CountCollectionLink` with the user-provided name
3. Frontend: button in the page header, Bootstrap modal with audit group dropdown + name input, submit handler

**No changes needed in:**
- `app/core/selectors/inventory_selectors.py` — Existing `get_distinct_audit_groups()` provides the dropdown choices (already on the page as `window.AUDIT_GROUP_CHOICES`)
- `app/core/static/core/css/itemsByAuditGroup.css` — Modal uses Bootstrap defaults

### Backend

- [x] **9.1** Add service function to create a count list from an audit group
  - **File**: `app/core/services/inventory_services.py`
  - **Do**: Add a new function after `add_count_list` (after line 973):
    ```python
    @login_required
    @require_POST
    def create_count_list_from_group(request):
        """Create a count list from all items in an audit group."""
        try:
            payload = json.loads(request.body.decode('utf-8')) if request.body else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'status': 'error', 'error': 'Invalid JSON payload.'}, status=400)

        audit_group_name = payload.get('audit_group', '').strip()
        record_type = payload.get('record_type', '').strip()
        collection_name = payload.get('collection_name', '').strip()

        if not audit_group_name or not record_type:
            return JsonResponse({'status': 'error', 'error': 'audit_group and record_type are required.'}, status=400)

        item_codes = list(
            AuditGroup.objects.filter(audit_group__iexact=audit_group_name, item_type=record_type)
            .values_list('item_code', flat=True)
        )

        if not item_codes:
            return JsonResponse({'status': 'error', 'error': f'No items found in audit group "{audit_group_name}".'}, status=400)

        list_info = add_count_records(item_codes, record_type)

        if not collection_name:
            now_str = dt.datetime.now().strftime('%m-%d-%Y_%H:%M')
            collection_name = f'{record_type}_count_{now_str}'

        new_count_collection = CountCollectionLink(
            link_order=CountCollectionLink.objects.aggregate(Max('link_order'))['link_order__max'] + 1 if CountCollectionLink.objects.exists() else 1,
            collection_name=collection_name,
            count_id_list=list(list_info['primary_keys']),
            collection_id=list_info['collection_id'],
            record_type=record_type,
        )
        new_count_collection.save()

        event_data = {
            'id': new_count_collection.id,
            'link_order': new_count_collection.link_order,
            'collection_name': new_count_collection.collection_name,
            'collection_id': new_count_collection.collection_id,
            'record_type': record_type,
        }
        append_count_collection_event('collection_added', event_data)
        broadcast_count_collection_event('collection_added', event_data)

        return JsonResponse({
            'status': 'success',
            'collection_name': new_count_collection.collection_name,
            'item_count': len(item_codes),
        })
    ```
    Import `require_POST` from `django.views.decorators.http` if not already imported. Import `login_required` from `django.contrib.auth.decorators` if not already imported. The function follows the same pattern as `update_audit_group_api` (JSON body, `@login_required`, `@require_POST`).
  - **Deliverable**: New function in `inventory_services.py` that creates a count list from all items in an audit group

- [x] **9.2** Add URL route
  - **File**: `app/core/urls.py`
  - **Do**: Add route near the other audit-group API routes:
    ```python
    path('api/count-list-from-group/', inventory_services.create_count_list_from_group, name='create-count-list-from-group'),
    ```
  - **Deliverable**: Route accessible at `/core/api/count-list-from-group/`

### Template

- [x] **9.3** Add "Create List from Group" button and modal
  - **File**: `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`
  - **Do**: After the existing `<button id="create_list">Create Count List</button>` (line 33), add a second button (staff-only):
    ```html
    {% if user.is_staff %}
        <button type="button" class="btn btn-outline-primary btn-sm ms-2" data-bs-toggle="modal" data-bs-target="#createListFromGroupModal">
            Create List from Group
        </button>
    {% endif %}
    ```
    Then before `{% endblock content %}` (before line 98), add the modal:
    ```html
    {% if user.is_staff %}
    <div class="modal fade" id="createListFromGroupModal" tabindex="-1" aria-labelledby="createListFromGroupLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="createListFromGroupLabel">Create Count List from Audit Group</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="groupSelectModal" class="form-label">Audit Group</label>
                        <select id="groupSelectModal" class="form-select">
                            <option value="">Select a group...</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="listNameInput" class="form-label">List Name</label>
                        <input type="text" id="listNameInput" class="form-control" placeholder="e.g. Weekly Blend Count">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="submitCreateListFromGroup">Create List</button>
                </div>
            </div>
        </div>
    </div>
    {% endif %}
    ```
  - **Deliverable**: Button visible next to "Create Count List"; clicking it opens a modal with group dropdown and name input

### JavaScript

- [x] **9.4** Populate the modal dropdown and handle submission
  - **File**: `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
  - **Do**: Inside the `$(document).ready()` block (after the DataTable init), add:
    ```js
    const $groupSelectModal = $('#groupSelectModal');
    if ($groupSelectModal.length) {
        auditGroupChoices.forEach(group => {
            $groupSelectModal.append(`<option value="${group}">${group}</option>`);
        });

        $('#submitCreateListFromGroup').on('click', async function () {
            const selectedGroup = $groupSelectModal.val();
            const listName = $('#listNameInput').val().trim();

            if (!selectedGroup) {
                alert('Please select an audit group.');
                return;
            }

            const urlParams = new URLSearchParams(window.location.search);
            const recordType = urlParams.get('recordType') || '';

            try {
                const response = await fetch('/core/api/count-list-from-group/', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        audit_group: selectedGroup,
                        record_type: recordType,
                        collection_name: listName,
                    }),
                });

                const data = await response.json();
                if (!response.ok || data.status !== 'success') {
                    alert(data.error || 'Failed to create count list.');
                    return;
                }

                alert(`Count list "${data.collection_name}" created with ${data.item_count} items.`);
                const modal = bootstrap.Modal.getInstance(document.getElementById('createListFromGroupModal'));
                if (modal) modal.hide();
                $groupSelectModal.val('');
                $('#listNameInput').val('');
            } catch (error) {
                alert('Unable to create count list. Please try again.');
            }
        });
    }
    ```
    This reuses `getCsrfToken()` (already defined in the file) and `auditGroupChoices` (already populated from `window.AUDIT_GROUP_CHOICES`).
  - **Deliverable**: Modal dropdown populated with audit groups; clicking "Create List" posts to the API and shows a confirmation

- [x] **9.5** Auto-populate list name when a group is selected
  - **File**: `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
  - **Do**: Add a change listener on `$groupSelectModal` (inside the `if ($groupSelectModal.length)` block, after populating the options):
    ```js
    $groupSelectModal.on('change', function () {
        $('#listNameInput').val($(this).val());
    });
    ```
    The user can still edit the name after it's populated. Selecting the blank "Select a group..." option clears the name field.
  - **Deliverable**: Selecting an audit group pre-fills the list name input with the group name

### Testing

- [x] **9.6** Test: Modal opens and dropdown is populated
  - Navigate to `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent` as a staff user
  - Verify "Create List from Group" button appears next to "Create Count List"
  - Click it — modal should open with all audit groups in the dropdown and an empty name field
- [x] **9.7** Test: Group selection auto-populates list name
  - Select an audit group from the dropdown
  - Verify the list name field auto-fills with the group name
  - Verify you can still edit the name after it's populated
  - Select the blank option — verify the name field clears
- [x] **9.8** Test: Create list with custom name
  - Select an audit group from the dropdown, change the name to "Test List", click "Create List"
  - Verify success alert shows the name and item count
  - Verify the list appears on the count links page (navigate to count links and confirm)
- [x] **9.9** Test: Create list without a name (auto-generated)
  - Select an audit group, clear the name field, click "Create List"
  - Verify success alert shows an auto-generated name
- [x] **9.10** Test: Validation
  - Click "Create List" without selecting a group — verify alert asks for a group
  - Verify modal closes and fields reset after successful creation
- [x] **9.11** Test: Non-staff user
  - Log in as a non-staff user
  - Verify neither the button nor the modal are visible

---

## Phase 10: Record Type Switcher Dropdown

_Add a dropdown at the top of the page that shows the current record type (Blend / Blend Component / Warehouse) and allows switching to another, including an "All" option that removes the record type filter._

**Analysis:** The view `display_items_by_audit_group` (web.py line 867) validates `recordType` against `{'blend', 'blendcomponent', 'warehouse'}` and defaults to `blendcomponent`. The downstream selector `get_ci_items_for_audit_group(record_type)` already handles `None` by skipping all item-prefix filters, returning everything. `get_distinct_audit_groups(None)` also returns all groups across types. So the backend mostly works — the view just needs to accept `all` as a valid value and pass `None` to the service layer when it's selected.

The dropdown is a simple navigation element — selecting a value reloads the page with the new `?recordType=` parameter. No AJAX needed.

**Considerations for "All" mode:**
- `get_upcoming_runs_for_items(item_codes, None)` defaults to `prodverse_warehousecountrecord` for the count table lookup — acceptable for display
- Items without an `AuditGroup` record will get `item_type = 'all'` as fallback — this only affects `data-item-type` attribute on rows and is harmless for display
- The "Create Count List" button (checkbox-based) still sends `recordType` from the URL param, which will be `all` — the `add_count_records` function calls `get_count_record_model(record_type)` which won't recognize `all`. This needs a guard or the button should be hidden in "All" mode

**No changes needed in:**
- `app/core/selectors/inventory_selectors.py` — Already handles `None` for both selectors
- `app/core/urls.py` — Same route
- `app/core/static/core/js/pageModules/itemsByAuditGroup.js` — Dropdown uses native form navigation, no JS needed

### View

- [x] **10.1** Accept "all" as a valid record type
  - **File**: `app/core/views/web.py`
  - **Function**: `display_items_by_audit_group` (line 867)
  - **Do**: Change the validation logic (lines 870-873) from:
    ```python
    valid_record_types = {'blend', 'blendcomponent', 'warehouse'}
    record_type = (request.GET.get('recordType') or 'blendcomponent').lower()
    if record_type not in valid_record_types:
        record_type = 'blendcomponent'
    ```
    to:
    ```python
    valid_record_types = {'blend', 'blendcomponent', 'warehouse', 'all'}
    record_type = (request.GET.get('recordType') or 'blendcomponent').lower()
    if record_type not in valid_record_types:
        record_type = 'blendcomponent'
    ```
    Then pass `None` to the service when `record_type == 'all'`. Change line 879-882:
    ```python
    service_record_type = None if record_type == 'all' else record_type
    audit_items, audit_group_list = build_audit_group_display_items(
        service_record_type,
        search_query=search_query,
        audit_group_filter=selected_audit_group,
    )
    ```
    Keep passing `record_type` (the string `'all'`) to the template context so the dropdown knows what's selected.
  - **Deliverable**: Page loads with all items when `?recordType=all` is in the URL

### Template

- [x] **10.2** Add record type switcher dropdown
  - **File**: `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`
  - **Do**: After the `<h1>Select Items to Count</h1>` (line 21), add a small inline form:
    ```html
    <form method="get" class="d-inline-block mb-2">
        <label class="form-label me-2 mb-0" for="recordTypeSwitcher">Viewing:</label>
        <select id="recordTypeSwitcher" name="recordType" class="form-select form-select-sm d-inline-block w-auto" onchange="this.form.submit()">
            <option value="blendcomponent" {% if record_type == 'blendcomponent' %}selected{% endif %}>Blend Components</option>
            <option value="blend" {% if record_type == 'blend' %}selected{% endif %}>Blends</option>
            <option value="warehouse" {% if record_type == 'warehouse' %}selected{% endif %}>Warehouse</option>
            <option value="all" {% if record_type == 'all' %}selected{% endif %}>All</option>
        </select>
    </form>
    ```
    The `onchange="this.form.submit()"` makes it navigate immediately on selection. The form uses `method="get"` so it sets `?recordType=` in the URL.
  - **Deliverable**: Dropdown visible below the page title showing current record type; selecting a different type reloads the page

- [x] **10.3** Hide checkbox-based "Create Count List" button in "All" mode
  - **File**: `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`
  - **Do**: Wrap the existing `<button id="create_list">` (line 32) in a record type guard:
    ```html
    {% if record_type != 'all' %}
        <button id="create_list">Create Count List</button>
    {% endif %}
    ```
    The checkbox-based count list creation requires a specific record type to know which count model to use. The "Create List from Group" modal (Phase 9) is also affected — the JS sends `recordType` from the URL. Wrap the "Create List from Group" button similarly:
    ```html
    {% if user.is_staff and record_type != 'all' %}
    ```
  - **Why**: `add_count_records` calls `get_count_record_model(record_type)` which doesn't handle `'all'` — it would error or create records in the wrong table
  - **Deliverable**: Count list creation buttons hidden when viewing "All"; visible for specific record types

- [x] **10.4** Hide checkbox column in "All" mode
  - **File**: `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`
  - **Do**: Change the checkbox `<th>` guard (line 58) and the checkbox `<td>` guard (line 75) from `{% if user.is_staff %}` to `{% if user.is_staff and record_type != 'all' %}`.
  - **Why**: Checkboxes feed the "Create Count List" button which is hidden in "All" mode. Showing checkboxes with no action button would be confusing.
  - **Deliverable**: No checkbox column in "All" mode

### Fix: "All" should mean blend + blendcomponent only

- [x] **10.5** Restrict "All" to blend and blendcomponent in the selector
  - **File**: `app/core/selectors/inventory_selectors.py`
  - **Function**: `get_ci_items_for_audit_group` (line 354)
  - **Do**: Currently when `record_type` is `None`, no filter is applied — this returns everything including warehouse items. Add a filter for the `None` case so "All" means blend + blendcomponent. Change the if/elif block (lines 362-369) to:
    ```python
    if record_type == 'blend':
        queryset = queryset.filter(itemcodedesc__istartswith='BLEND')
    elif record_type == 'blendcomponent':
        queryset = queryset.filter(
            Q(itemcodedesc__istartswith='CHEM') |
            Q(itemcodedesc__istartswith='DYE') |
            Q(itemcodedesc__istartswith='FRAGRANCE')
        )
    elif record_type is None:
        queryset = queryset.filter(
            Q(itemcodedesc__istartswith='BLEND') |
            Q(itemcodedesc__istartswith='CHEM') |
            Q(itemcodedesc__istartswith='DYE') |
            Q(itemcodedesc__istartswith='FRAGRANCE')
        )
    ```
    The `warehouse` case (no explicit branch) continues to return everything, which is the existing behavior.
  - **Deliverable**: `?recordType=all` shows blends + blend components only, no warehouse items

- [x] **10.6** Restrict "All" audit group choices to blend + blendcomponent
  - **File**: `app/core/selectors/inventory_selectors.py`
  - **Function**: `get_distinct_audit_groups` (line 417)
  - **Do**: Currently when `record_type` is `None`, it returns all audit groups including warehouse groups. Add a filter for the `None` case (after line 421):
    ```python
    if record_type:
        audit_groups = audit_groups.filter(item_type=record_type)
    else:
        audit_groups = audit_groups.filter(item_type__in=['blend', 'blendcomponent'])
    ```
  - **Deliverable**: "All" mode audit group dropdown/choices only include blend and blendcomponent groups

- [x] **10.7** Rename "All" option label to clarify scope
  - **File**: `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`
  - **Do**: In the record type switcher dropdown (added in 10.2), change the "All" option text to make it clear it's blend + components:
    ```html
    <option value="all" {% if record_type == 'all' %}selected{% endif %}>All (Blends + Components)</option>
    ```
  - **Deliverable**: Dropdown label clearly communicates what "All" includes

### Testing

- [x] **10.8** Test: Dropdown shows current record type
  - Navigate to `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent`
  - Verify dropdown shows "Blend Components" selected
  - Navigate to `?recordType=blend` — verify "Blends" selected
  - Navigate to `?recordType=warehouse` — verify "Warehouse" selected
- [x] **10.9** Test: Switching record types
  - Select "Blends" from the dropdown — page reloads with `?recordType=blend` and shows blend items
  - Select "Warehouse" — page reloads with warehouse items
  - Select "All (Blends + Components)" — page reloads showing blends AND blend components but NO warehouse items
- [x] **10.10** Test: "All" mode hides count list creation
  - In "All" mode, verify "Create Count List" button is hidden
  - Verify "Create List from Group" button is hidden
  - Verify no checkbox column
  - Verify inline edit pencil icons still work (editing audit groups is valid across all types)
- [x] **10.11** Test: Default behavior preserved
  - Navigate to `/core/items-by-audit-group/` with no `recordType` param
  - Verify it defaults to "Blend Components"
  - Navigate with an invalid `?recordType=bogus` — verify it defaults to "Blend Components"

---

## Phase 11: Prompt for Count List Name on Creation

_When clicking "Create Count List" (the checkbox-based button), prompt the user for a list name before creating it. The default name is pre-filled with the existing auto-generated format (`{recordType}_count_{timestamp}`). Applies everywhere `CreateCountListButton` is used._

**Analysis:** The `CreateCountListButton` class in `buttonObjects.js` (lines 6-46) handles the click for the `#create_list` button across 7 pages. On click, it gathers checked item codes, base64-encodes them, and fires a GET to `/core/count-list/add?itemsToAdd=...&recordType=...`. The backend `add_count_list()` in `inventory_services.py` (line 880) auto-generates the name as `f'{record_type}_count_{MM-DD-YYYY_HH:MM}'` (line 950) — the user never gets a chance to name it.

The fix is two changes:
1. **JS**: Before sending the AJAX request, show a `prompt()` with the default name pre-filled. If the user confirms, append the name to the request URL. If they cancel, abort.
2. **Backend**: Read the optional name from the query string. If provided, use it instead of auto-generating.

A `prompt()` dialog is the right UX here — it's a single text field with a default, no need for a modal. The user can accept the default by pressing Enter, type a custom name, or cancel to abort list creation entirely.

**Pages affected (all use `CreateCountListButton`):**
- `itemsbyauditgroup.html` — has `recordType` in URL
- `countrecords.html` — has `recordType` in URL
- `upcomingblends.html` — no `recordType` param (items are all blends)
- `upcomingcomponents.html` — no `recordType` param (items are all blendcomponents)
- `blendshortages.html` — no `recordType` param (items are all blends)
- `lotnumrecords.html` — no `recordType` param, button hidden by default
- `listtocountlist.html` — no `recordType` param

For pages without `recordType` in the URL, the default name uses the generic format `count_{timestamp}` (dropping the null prefix).

**No changes needed in:**
- Templates — No HTML changes, the prompt is JS-native
- `app/core/urls.py` — Same route
- `app/core/selectors/` — No query changes
- CSS — No styling changes

### JavaScript

- [x] **11.1** Add name prompt to `CreateCountListButton`
  - **File**: `app/core/static/core/js/objects/buttonObjects.js`
  - **Function**: `setUpCountListButton()` (lines 15-44)
  - **Do**: After getting `recordType` (line 28), generate the default name and prompt the user. Replace lines 29-43 with:
    ```js
    let now = new Date();
    let pad = (n) => String(n).padStart(2, '0');
    let dateStr = `${pad(now.getMonth()+1)}-${pad(now.getDate())}-${now.getFullYear()}_${pad(now.getHours())}:${pad(now.getMinutes())}`;
    let defaultName = recordType ? `${recordType}_count_${dateStr}` : `count_${dateStr}`;
    let collectionName = prompt('Enter a name for the count list:', defaultName);
    if (collectionName === null) return;
    collectionName = collectionName.trim() || defaultName;
    let requestURL = `/core/count-list/add?itemsToAdd=${encodedItemCodes}&recordType=${recordType}&collectionName=${encodeURIComponent(collectionName)}`;
    $.ajax({
        url: requestURL,
        type: 'GET',
        success: function(response) {
            console.log("Request successful:", response);
            alert("Count list generated. Check count links page.");
        },
        error: function(xhr, status, error) {
            console.error("Request failed:", status, error);
        }
    });
    ```
    Key behavior:
    - `prompt()` returns `null` on Cancel → aborts, no request sent
    - Empty string after trim → falls back to the default name
    - User can accept default by pressing Enter or type a custom name
    - `encodeURIComponent` handles special characters in the name
  - **Deliverable**: Clicking "Create Count List" on any page shows a prompt with the default name; user can accept, customize, or cancel

### Backend

- [x] **11.2** Read optional `collectionName` from query string
  - **File**: `app/core/services/inventory_services.py`
  - **Function**: `add_count_list()` (line 880)
  - **Do**: After `list_info = add_count_records(...)` (line 943), change the name generation (lines 945-950) from:
    ```python
    now_str = dt.datetime.now().strftime('%m-%d-%Y_%H:%M')

    try:
        new_count_collection = CountCollectionLink(
            ...
            collection_name = f'{record_type}_count_{now_str}',
            ...
        )
    ```
    to:
    ```python
    collection_name = request.GET.get('collectionName', '').strip()
    if not collection_name:
        now_str = dt.datetime.now().strftime('%m-%d-%Y_%H:%M')
        collection_name = f'{record_type}_count_{now_str}'

    try:
        new_count_collection = CountCollectionLink(
            ...
            collection_name=collection_name,
            ...
        )
    ```
    Read `collectionName` from the GET params. If provided and non-empty, use it. Otherwise fall back to the existing auto-generated format.
  - **Deliverable**: Backend uses user-provided name when available; existing auto-generated behavior preserved as fallback

### Testing

- [ ] **11.3** Test: Prompt appears with correct default name
  - Navigate to `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent`
  - Check a few items, click "Create Count List"
  - Verify a browser prompt appears with default text like `blendcomponent_count_02-04-2026_14:30`
  - Press Enter to accept — verify count list created with that name
- [ ] **11.4** Test: Custom name
  - Check items, click "Create Count List"
  - Change the name to "My Custom List", press OK
  - Verify the count list is created with name "My Custom List" (check count links page)
- [ ] **11.5** Test: Cancel aborts creation
  - Check items, click "Create Count List"
  - Click Cancel on the prompt
  - Verify no count list is created (no success alert, no new list on count links page)
- [ ] **11.6** Test: Empty name uses default
  - Check items, click "Create Count List"
  - Clear the text field completely, press OK
  - Verify the count list is created with the auto-generated default name
- [ ] **11.7** Test: Works on other pages
  - Navigate to `http://localhost:8000/core/upcoming-blends/`
  - Check items, click "Create Count List"
  - Verify prompt appears with default name like `count_02-04-2026_14:30` (no recordType prefix since none in URL)
  - Repeat on `http://localhost:8000/core/upcoming-components/`

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 6. Remove Count Unit & Restrict Sorting | Complete | 8/8 |
| 7. Merge Actions Column & Table Styling | Complete | 8/8 |
| 8. "Add New" Custom Audit Group | Complete | 8/8 |
| 9. Create Count List from Group | Complete | 11/11 |
| 10. Record Type Switcher | Complete | 11/11 |
| 11. Prompt for Count List Name | In Progress | 2/7 |

**Overall**: 48/53 tasks (91%)

---

**Status**: Draft
