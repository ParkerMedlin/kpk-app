# Table Utilities Consolidation Design

## Overview

This design consolidates scattered table functionality into a single `tableObjects.js` module. The codebase has four distinct table enhancement patterns that can be standardized:

1. **Column sorting + export buttons** - DataTables with Buttons extension (blenditemstatus.html)
2. **Drag-and-drop row ordering** - jQuery UI sortable (DeskSchedulePage, CountCollectionLinksPage)
3. **Inline editing** - Custom form row editing (ContainerClassificationTable)
4. **Whole-table text filtering** - FilterForm from lookupFormObjects.js

The approach is composition-based: each behavior is a standalone class or function that can be applied independently.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/static/core/js/objects/pageObjects.js` | DeskSchedulePage, CountCollectionLinksPage refactored to use SortableRows |
| `app/core/static/core/js/objects/lookupFormObjects.js` | Remove FilterForm (moved to tableObjects.js), add re-export for backwards compatibility |
| `app/core/static/core/js/pageModules/containerClassificationRecords.js` | Update import path for FilterForm |

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/static/core/js/objects/tableObjects.js` | FilterForm, SortableRows, initDataTableWithExport(), InlineEditTable |

## Data Model

No database changes required. This feature is purely frontend JavaScript refactoring.

## URL Routes

No new routes required. Existing pages already have endpoints for order updates and inline edits.

---

## Pattern 1: Column Sorting + Export Buttons (DataTables)

### Current Implementation

From `blenditemstatus.html`:

```javascript
$('#blendItemStatusTable').DataTable({
    paging: false,
    order: [[0, 'asc']],
    dom: 'Bfrtip',
    buttons: ['copy', 'csv', 'excel', 'print']
});
```

### Required Assets

```html
<!-- CSS -->
<link rel="stylesheet" href="{% static 'core/css/thirdPartyLibraries/jquery.dataTables.min.css' %}">
<link rel="stylesheet" href="{% static 'core/css/thirdPartyLibraries/buttons.dataTables.min.css' %}">

<!-- JS -->
<script src="{% static 'core/js/thirdPartyLibraries/jszip.min.js' %}"></script>
<script src="{% static 'core/js/thirdPartyLibraries/pdfmake.min.js' %}"></script>
<script src="{% static 'core/js/thirdPartyLibraries/vfs_fonts.js' %}"></script>
<script src="{% static 'core/js/thirdPartyLibraries/datatables/jquery.dataTables.min.js' %}"></script>
<script src="{% static 'core/js/thirdPartyLibraries/datatables/dataTables.buttons.min.js' %}"></script>
<script src="{% static 'core/js/thirdPartyLibraries/datatables/buttons.html5.min.js' %}"></script>
<script src="{% static 'core/js/thirdPartyLibraries/datatables/buttons.print.min.js' %}"></script>
<script src="{% static 'core/js/thirdPartyLibraries/datatables/buttons.colVis.min.js' %}"></script>
```

### Proposed Helper

```javascript
/**
 * Initializes a DataTable with standard export buttons.
 *
 * @param {string} tableSelector - CSS selector for the table
 * @param {Object} options - Additional DataTable options to merge
 * @returns {DataTable} - The initialized DataTable instance
 */
export function initDataTableWithExport(tableSelector, options = {}) {
    const defaults = {
        paging: false,
        order: [[0, 'asc']],
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel', 'print']
    };

    return $(tableSelector).DataTable({ ...defaults, ...options });
}
```

**Usage:**
```javascript
import { initDataTableWithExport } from '../objects/tableObjects.js';

initDataTableWithExport('#blendItemStatusTable');

// With custom options:
initDataTableWithExport('#myTable', {
    order: [[1, 'desc']],
    buttons: ['copy', 'excel']  // Subset of buttons
});
```

---

## Pattern 2: Drag-and-Drop Row Ordering (SortableRows)

### Current Implementation

From `pageObjects.js` (DeskSchedulePage and CountCollectionLinksPage):

```javascript
$("#deskScheduleTable").sortable({
    items: '.tableBodyRow',
    cursor: 'move',
    axis: 'y',
    dropOnEmpty: false,
    start: function (e, ui) {
        ui.item.addClass("selected");
    },
    stop: function (e, ui) {
        ui.item.removeClass("selected");
        $(this).find("tr").each(function(index) {
            if (index > 0) {
                $(this).find("td").eq(0).html(index);
            }
        });
        updateScheduleOrder();
    }
});
```

### Proposed Class

```javascript
/**
 * Enables drag-and-drop row reordering on a table.
 *
 * @param {Object} options
 * @param {string} options.tableSelector - CSS selector for the table/tbody
 * @param {string} options.rowSelector - CSS selector for draggable rows (default: '.tableBodyRow')
 * @param {number} options.orderColumnIndex - Column index containing order value (default: 0)
 * @param {Function} options.onReorder - Callback(orderedData[]) after drop completes
 * @param {Function} options.getRowId - Function(row) to extract row identifier (default: uses data-id attribute)
 */
export class SortableRows {
    constructor(options) {
        this.tableSelector = options.tableSelector;
        this.rowSelector = options.rowSelector || '.tableBodyRow';
        this.orderColumnIndex = options.orderColumnIndex ?? 0;
        this.onReorder = options.onReorder || (() => {});
        this.getRowId = options.getRowId || ((row) => $(row).data('id'));

        this._init();
    }

    _init() {
        const $table = $(this.tableSelector);

        $table.sortable({
            items: this.rowSelector,
            cursor: 'move',
            axis: 'y',
            dropOnEmpty: false,
            start: (e, ui) => ui.item.addClass('selected'),
            stop: (e, ui) => {
                ui.item.removeClass('selected');
                this._updateOrderValues();
                this._invokeCallback();
            }
        });
    }

    _updateOrderValues() {
        const orderColIndex = this.orderColumnIndex;
        $(this.tableSelector).find('tr').each(function(index) {
            if (index > 0) {
                $(this).find('td').eq(orderColIndex).html(index);
            }
        });
    }

    _invokeCallback() {
        const orderedData = [];
        $(this.tableSelector).find(this.rowSelector).each((index, row) => {
            orderedData.push({
                id: this.getRowId(row),
                order: index + 1
            });
        });
        this.onReorder(orderedData);
    }

    destroy() {
        $(this.tableSelector).sortable('destroy');
    }
}
```

**Usage in refactored DeskSchedulePage:**
```javascript
import { SortableRows } from '../objects/tableObjects.js';

this.sortableRows = new SortableRows({
    tableSelector: '#deskScheduleTable',
    onReorder: (orderedData) => {
        const encodedOrder = btoa(JSON.stringify(orderedData));
        $.ajax({
            url: `/core/update-desk-order?encodedDeskScheduleOrder=${encodedOrder}`,
            async: false,
            dataType: 'json'
        });
    }
});
```

**Usage in refactored CountCollectionLinksPage:**
```javascript
this.sortableRows = new SortableRows({
    tableSelector: '#countCollectionLinkTable',
    getRowId: (row) => $(row).find('td:eq(1)').attr('data-collection-id'),
    onReorder: (orderedData) => {
        const collectionLinkDict = {};
        orderedData.forEach(item => {
            collectionLinkDict[item.id] = item.order;
        });
        thisCountCollectionWebSocket.updateCollectionOrder(collectionLinkDict);
    }
});
```

---

## Pattern 3: Inline Editing (InlineEditTable)

### Current Implementation

From `containerClassificationRecords.js`, the `ContainerClassificationTable` class provides:
- Click-to-edit rows with `enterEditMode(row)` / `exitEditMode(row)`
- Dynamic input creation via `buildInput(field, value)`
- Save/Cancel/Delete button group in edit mode
- Validation with visual feedback
- Autofill dropdowns from existing column values
- API calls for create/update/delete

### Proposed Class

The existing `ContainerClassificationTable` is well-structured but tightly coupled to its specific use case. A generalized version would extract the reusable patterns:

```javascript
/**
 * Adds inline editing capabilities to a table.
 *
 * @param {Object} options
 * @param {string} options.tableSelector - CSS selector for the table
 * @param {string} options.rowSelector - CSS selector for editable rows (default: '.filterableRow')
 * @param {Array<Object>} options.fields - Field config: [{name, type, required, validate}]
 * @param {Function} options.onSave - Callback(rowId, data) when row is saved
 * @param {Function} options.onDelete - Callback(rowId) when row is deleted
 * @param {Function} options.onCreate - Callback(data) when new row is created
 * @param {string} options.editButtonSelector - Selector for edit buttons (default: '.edit-row-btn')
 * @param {string} options.addButtonSelector - Selector for add button (optional)
 */
export class InlineEditTable {
    constructor(options) {
        this.tableSelector = options.tableSelector;
        this.rowSelector = options.rowSelector || '.filterableRow';
        this.fields = options.fields || [];
        this.onSave = options.onSave || (() => Promise.resolve());
        this.onDelete = options.onDelete || (() => Promise.resolve());
        this.onCreate = options.onCreate || (() => Promise.resolve());
        this.editButtonSelector = options.editButtonSelector || '.edit-row-btn';
        this.addButtonSelector = options.addButtonSelector || null;

        this.activeRow = null;
        this._init();
    }

    _init() {
        this._attachEditHandlers();
        if (this.addButtonSelector) {
            this._attachAddHandler();
        }
    }

    _attachEditHandlers() {
        const table = document.querySelector(this.tableSelector);
        if (!table) return;

        table.querySelectorAll(this.editButtonSelector).forEach(btn => {
            btn.addEventListener('click', (e) => {
                const row = e.target.closest('tr');
                this.enterEditMode(row);
            });
        });
    }

    _attachAddHandler() {
        const addBtn = document.querySelector(this.addButtonSelector);
        if (addBtn) {
            addBtn.addEventListener('click', () => this.addRow());
        }
    }

    enterEditMode(row) {
        if (this.activeRow && this.activeRow !== row) {
            const abandon = confirm('You have unsaved changes. Abandon them?');
            if (!abandon) return;
            this.exitEditMode(this.activeRow);
        }

        this._saveSnapshot(row);
        this._convertToInputs(row);
        this._showEditButtons(row);
        row.classList.add('table-warning');
        this.activeRow = row;
    }

    exitEditMode(row) {
        this._restoreFromSnapshot(row);
        this._showViewButtons(row);
        row.classList.remove('table-warning');
        if (this.activeRow === row) {
            this.activeRow = null;
        }
    }

    async saveRow(row) {
        const data = this._collectRowData(row);
        const rowId = row.dataset.id;

        try {
            if (row.dataset.isNew === 'true') {
                await this.onCreate(data);
                delete row.dataset.isNew;
            } else {
                await this.onSave(rowId, data);
            }
            this._updateSnapshot(row, data);
            this.exitEditMode(row);
        } catch (error) {
            alert(error.message);
        }
    }

    async deleteRow(row) {
        const rowId = row.dataset.id;
        const confirm = window.confirm('Delete this row? This cannot be undone.');
        if (!confirm) return;

        try {
            await this.onDelete(rowId);
            row.remove();
            if (this.activeRow === row) {
                this.activeRow = null;
            }
        } catch (error) {
            alert(error.message);
        }
    }

    addRow() {
        // Create new row from template, prepend to table, enter edit mode
    }

    // Private helpers for snapshot management, input conversion, etc.
    _saveSnapshot(row) { /* ... */ }
    _restoreFromSnapshot(row) { /* ... */ }
    _convertToInputs(row) { /* ... */ }
    _collectRowData(row) { /* ... */ }
    _showEditButtons(row) { /* ... */ }
    _showViewButtons(row) { /* ... */ }

    destroy() {
        // Remove event handlers
    }
}
```

**Usage:**
```javascript
import { InlineEditTable } from '../objects/tableObjects.js';

const table = new InlineEditTable({
    tableSelector: '#containerClassificationTable',
    addButtonSelector: '#add-classification-btn',
    fields: [
        { name: 'item_code', type: 'text', required: true },
        { name: 'tote_classification', type: 'text' },
        { name: 'flush_tote', type: 'text' },
        { name: 'hose_color', type: 'text' },
        { name: 'tank_classification', type: 'textarea' }
    ],
    onSave: async (id, data) => {
        const response = await fetch(`/core/api/container-classification/${id}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Save failed');
    },
    onDelete: async (id) => {
        const response = await fetch(`/core/api/container-classification/${id}/delete/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() }
        });
        if (!response.ok) throw new Error('Delete failed');
    }
});
```

---

## Pattern 4: Whole-Table Text Filtering (FilterForm)

### Current Implementation

From `lookupFormObjects.js`, the `FilterForm` class provides whole-table text filtering. This class doesn't belong in lookupFormObjects (which handles forms that send requests to the database)—it only deals with on-page DOM manipulation, so it should move to tableObjects.js.

```javascript
export class FilterForm {
    constructor(options = {}) {
        this.inputSelector = options.inputSelector || '#id_filter_criteria';
        this.tableSelector = options.tableSelector || '#displayTable';
        this.rowSelector = options.rowSelector || 'tr.filterableRow';
        this.ignoreSelectors = Array.isArray(options.ignoreSelectors) ? options.ignoreSelectors : [];

        try {
            this.setUpFiltering();
        } catch (err) {
            console.error(err.message);
        }
    }

    setUpFiltering() {
        const $input = $(this.inputSelector);
        if (!$input.length) {
            return;
        }

        $input.on('keyup', () => {
            const value = this._normalizeText($input.val());
            $(`${this.tableSelector} ${this.rowSelector}`).each((_, element) => {
                const $row = $(element);
                const rowText = this._getRowSearchText($row);
                const isMatch = rowText.includes(value);

                $row.toggle(isMatch);
                if (isMatch) {
                    $row.addClass('chosen');
                } else {
                    $row.removeClass('chosen');
                }
            });
        });
    }

    _getRowSearchText($row) {
        let text;

        if (this.ignoreSelectors.length) {
            const $clone = $row.clone();
            this.ignoreSelectors.forEach((selector) => {
                $clone.find(selector).remove();
            });
            text = $clone.text();
        } else {
            text = $row.text();
        }

        return this._normalizeText(text);
    }

    _normalizeText(value) {
        return (value || '').toString().toLowerCase().replace(/\s+/g, '');
    }
}
```

### Migration

1. Move `FilterForm` class to `tableObjects.js`
2. Add re-export in `lookupFormObjects.js` for backwards compatibility:
   ```javascript
   export { FilterForm } from './tableObjects.js';
   ```
3. Update imports in files that use FilterForm directly

**Usage (unchanged):**
```javascript
import { FilterForm } from '../objects/tableObjects.js';

new FilterForm({
    tableSelector: '#containerClassificationTable',
    ignoreSelectors: ['[data-is-input="true"]']
});
```

---

## CSS Requirements

```css
/* Drag feedback for SortableRows */
tr.selected {
    background-color: #e3f2fd;
    opacity: 0.8;
}

/* Edit mode indicator for InlineEditTable */
tr.table-warning {
    /* Bootstrap class, already available */
}
```

---

## Module Structure

```
js/objects/tableObjects.js
├── export class FilterForm
├── export function initDataTableWithExport(tableSelector, options)
├── export class SortableRows
└── export class InlineEditTable
```

**Import pattern:**
```javascript
import { FilterForm, SortableRows, initDataTableWithExport } from '../objects/tableObjects.js';
```

---

## Migration Path

### Phase 1: Create tableObjects.js
- Move `FilterForm` from lookupFormObjects.js
- Add re-export in lookupFormObjects.js for backwards compatibility
- Implement `initDataTableWithExport()` helper
- Implement `SortableRows` class
- Document `InlineEditTable` interface (may defer full implementation)

### Phase 2: Migrate DeskSchedulePage
- Replace inline sortable code with `new SortableRows({...})`
- Verify order updates still work
- ~25 lines removed, ~10 lines added

### Phase 3: Migrate CountCollectionLinksPage
- Replace inline sortable code
- Keep WebSocket integration in onReorder callback

### Phase 4: Evaluate InlineEditTable
- Assess whether `ContainerClassificationTable` should be refactored to use `InlineEditTable`
- Or keep domain-specific implementation if abstraction cost exceeds benefit

---

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| Column sorting | DataTables `order` option |
| Export buttons (Copy/CSV/Excel/Print) | DataTables Buttons extension |
| Drag-and-drop row ordering | `SortableRows` class |
| Visual drag feedback | `.selected` class on start/stop |
| Order value updates | `_updateOrderValues()` method |
| Reorder callback | `onReorder` option |
| Inline editing | `InlineEditTable` class |
| Whole-table filtering | `FilterForm` class (moved from lookupFormObjects.js) |

---

**Status**: Draft
