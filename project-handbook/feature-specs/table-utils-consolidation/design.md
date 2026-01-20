# Table Utilities Consolidation Design

## Overview

This design consolidates scattered table functionality into a single `tableObjects.js` module. The two pages with drag-and-drop (DeskSchedulePage, CountCollectionLinksPage) all use nearly identical jQuery `.sortable()` patterns that can be abstracted into a reusable `SortableRows` class. Filtering is currently whole-table text search; this adds per-column filtering via `ColumnFilter`. Inline editing patterns are standardized in `FormRowTable`.

The approach is composition-based: each behavior (sorting, filtering, inline editing) is a standalone class that can be applied independently or combined via an `enhanceTable()` helper.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/static/core/js/objects/pageObjects.js` | DeskSchedulePage, CountCollectionLinksPage refactored to use SortableRows |
| `app/core/static/core/js/objects/lookupFormObjects.js` | Keep FilterForm/DropDownFilter, add re-export of ColumnFilter for discoverability |

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/static/core/js/objects/tableObjects.js` | SortableRows, ColumnFilter, FormRowTable, enhanceTable() |

## Data Model

No database changes required. This feature is purely frontend JavaScript refactoring.

### Existing Tables Used
- `core_deskoneschedule` - DeskSchedulePage row ordering
- `core_countcollectionlink` - CountCollectionLinksPage row ordering and inline name editing

## URL Routes

No new routes required. Existing pages already have endpoints for order updates:
- `/api/deskone-schedule/update-order/` (POST)
- WebSocket channel for CountCollectionLinks
- `/api/blend-instructions/update-order/` (POST)

## Class Design

### SortableRows

Wraps jQuery UI `.sortable()` with a consistent interface.

```javascript
/**
 * Enables drag-and-drop row reordering on a table.
 *
 * @param {Object} options
 * @param {string} options.tableSelector - CSS selector for the table/tbody
 * @param {string} options.rowSelector - CSS selector for draggable rows (default: 'tr.tableBodyRow')
 * @param {string} options.excludeSelector - CSS selector for non-draggable rows (e.g., 'tr#addNewRow')
 * @param {string} options.orderColumnIndex - Column index containing order value (default: 0)
 * @param {Function} options.onReorder - Callback(orderedIds[]) after drop completes
 * @param {string} options.dragHandleSelector - Optional handle selector (drags whole row if omitted)
 */
export class SortableRows {
    constructor(options) {
        this.tableSelector = options.tableSelector;
        this.rowSelector = options.rowSelector || 'tr.tableBodyRow';
        this.excludeSelector = options.excludeSelector || null;
        this.orderColumnIndex = options.orderColumnIndex ?? 0;
        this.onReorder = options.onReorder || (() => {});
        this.dragHandleSelector = options.dragHandleSelector || null;

        this._init();
    }

    _init() {
        const $table = $(this.tableSelector);
        const itemsSelector = this.excludeSelector
            ? `${this.rowSelector}:not(${this.excludeSelector})`
            : this.rowSelector;

        $table.sortable({
            items: itemsSelector,
            cursor: 'move',
            axis: 'y',
            dropOnEmpty: false,
            handle: this.dragHandleSelector || false,
            start: (e, ui) => ui.item.addClass('selected'),
            stop: (e, ui) => {
                ui.item.removeClass('selected');
                this._updateOrderValues();
                this._invokeCallback();
            }
        });
    }

    _updateOrderValues() {
        // Update visible order numbers in each row's order column
    }

    _invokeCallback() {
        // Gather row IDs in new order, call this.onReorder(orderedIds)
    }

    destroy() {
        $(this.tableSelector).sortable('destroy');
    }
}
```

**Usage in refactored DeskSchedulePage:**
```javascript
this.sortableRows = new SortableRows({
    tableSelector: '#deskScheduleTable',
    onReorder: (orderedIds) => this.updateScheduleOrder(orderedIds)
});
```

---

### ColumnFilter

Per-column text filtering with filter inputs in header row.

```javascript
/**
 * Adds per-column filter inputs to table headers.
 *
 * @param {Object} options
 * @param {string} options.tableSelector - CSS selector for the table
 * @param {string} options.rowSelector - CSS selector for filterable rows (default: 'tr.filterableRow')
 * @param {Array<Object>} options.columns - Column config: [{index: 0, filterable: true}, ...]
 * @param {number} options.debounceMs - Input debounce delay (default: 150)
 */
export class ColumnFilter {
    constructor(options) {
        this.tableSelector = options.tableSelector;
        this.rowSelector = options.rowSelector || 'tr.filterableRow';
        this.columns = options.columns || [];
        this.debounceMs = options.debounceMs ?? 150;
        this.activeFilters = {}; // {columnIndex: filterValue}

        this._init();
    }

    _init() {
        this._createFilterRow();
        this._attachListeners();
    }

    _createFilterRow() {
        // Insert a <tr class="column-filter-row"> after the header row
        // For each column with filterable: true, add an <input type="text">
        // For non-filterable columns, add empty <th>
    }

    _attachListeners() {
        // Debounced keyup on filter inputs
        // On change, update this.activeFilters and call _applyFilters()
    }

    _applyFilters() {
        // For each row, check all active filters (AND logic)
        // Hide rows that don't match, show rows that do
    }

    clearFilters() {
        // Reset all inputs and show all rows
    }

    destroy() {
        // Remove filter row and listeners
    }
}
```

**Usage:**
```javascript
this.columnFilter = new ColumnFilter({
    tableSelector: '#itemTable',
    columns: [
        { index: 0, filterable: true, placeholder: 'Item #' },
        { index: 1, filterable: true, placeholder: 'Description' },
        { index: 2, filterable: false }, // Actions column
    ]
});
```

---

### FormRowTable

Manages inline editing with add/delete rows and dirty tracking.

```javascript
/**
 * Adds inline editing capabilities to a table.
 *
 * @param {Object} options
 * @param {string} options.tableSelector - CSS selector for the table
 * @param {string} options.rowSelector - CSS selector for editable rows
 * @param {string} options.addButtonSelector - Selector for "Add New" trigger
 * @param {Function} options.onAdd - Callback when new row is added
 * @param {Function} options.onDelete - Callback(rowId) when row is deleted
 * @param {Function} options.onChange - Callback(rowId, field, value) on field change
 * @param {Object} options.rowTemplate - Template config for new rows
 * @param {boolean} options.trackDirty - Enable unsaved changes warning (default: true)
 */
export class FormRowTable {
    constructor(options) {
        this.tableSelector = options.tableSelector;
        this.rowSelector = options.rowSelector || 'tr.editableRow';
        this.addButtonSelector = options.addButtonSelector;
        this.onAdd = options.onAdd || (() => {});
        this.onDelete = options.onDelete || (() => {});
        this.onChange = options.onChange || (() => {});
        this.rowTemplate = options.rowTemplate || null;
        this.trackDirty = options.trackDirty !== false;

        this.isDirty = false;
        this._init();
    }

    _init() {
        this._attachAddHandler();
        this._attachChangeHandlers();
        this._attachDeleteHandlers();
        if (this.trackDirty) {
            this._setupDirtyTracking();
        }
    }

    _attachAddHandler() {
        // Click handler on addButtonSelector
        // Clone rowTemplate or create new row
        // Call onAdd callback
    }

    _attachChangeHandlers() {
        // Delegated blur/change handlers on inputs within rows
        // Track original values, call onChange on actual changes
    }

    _attachDeleteHandlers() {
        // Delegated click handler on delete buttons
        // Confirm if needed, remove row, call onDelete
    }

    _setupDirtyTracking() {
        // Set isDirty=true on any change
        // beforeunload warning if isDirty
    }

    addRow(data = {}) {
        // Programmatically add a row with optional initial data
    }

    markClean() {
        // Reset isDirty state (call after successful save)
    }

    destroy() {
        // Remove handlers and dirty tracking
    }
}
```

---

### enhanceTable()

Composition helper that applies multiple behaviors.

```javascript
/**
 * Applies multiple table behaviors in one call.
 *
 * @param {string} tableSelector - CSS selector for the table
 * @param {Object} options
 * @param {Object} options.sortable - SortableRows options (or false to disable)
 * @param {Object} options.columnFilter - ColumnFilter options (or false to disable)
 * @param {Object} options.formRow - FormRowTable options (or false to disable)
 * @returns {Object} - { sortable: SortableRows|null, columnFilter: ColumnFilter|null, formRow: FormRowTable|null }
 */
export function enhanceTable(tableSelector, options = {}) {
    const result = {
        sortable: null,
        columnFilter: null,
        formRow: null
    };

    if (options.sortable !== false && options.sortable) {
        result.sortable = new SortableRows({
            tableSelector,
            ...options.sortable
        });
    }

    if (options.columnFilter !== false && options.columnFilter) {
        result.columnFilter = new ColumnFilter({
            tableSelector,
            ...options.columnFilter
        });
    }

    if (options.formRow !== false && options.formRow) {
        result.formRow = new FormRowTable({
            tableSelector,
            ...options.formRow
        });
    }

    return result;
}
```

**Usage:**
```javascript
const enhancements = enhanceTable('#myTable', {
    sortable: {
        onReorder: (ids) => saveOrder(ids)
    },
    columnFilter: {
        columns: [
            { index: 0, filterable: true },
            { index: 1, filterable: true }
        ]
    }
});
```

## Frontend Integration

### Template Changes

For ColumnFilter, tables need a header row where filter inputs will be injected:

```html
<table id="myTable">
    <thead>
        <tr class="header-row">
            <th>Item #</th>
            <th>Description</th>
            <th>Actions</th>
        </tr>
        <!-- ColumnFilter inserts filter row here -->
    </thead>
    <tbody>
        <tr class="tableBodyRow filterableRow">...</tr>
    </tbody>
</table>
```

### CSS Additions

```css
/* Column filter inputs */
.column-filter-row input {
    width: 100%;
    padding: 4px 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 0.875rem;
}

/* Drag feedback */
tr.selected {
    background-color: #e3f2fd;
    opacity: 0.8;
}

/* Dirty state indicator (optional) */
.form-row-table.dirty::before {
    content: '* Unsaved changes';
    color: #f57c00;
    font-size: 0.75rem;
}
```

### JavaScript Module Structure

```
js/objects/tableObjects.js
├── export class SortableRows
├── export class ColumnFilter
├── export class FormRowTable
└── export function enhanceTable
```

**Import pattern in page modules:**
```javascript
import { SortableRows, enhanceTable } from '../objects/tableObjects.js';
```

## DataTables ColReorder

For pages already using DataTables (limited use in this codebase), ColReorder can be enabled:

```javascript
// Only where DataTables is already initialized
$('#dataTable').DataTable({
    colReorder: true,
    stateSave: true // Persists column order in localStorage
});
```

This is opt-in and only documented as an option, not applied globally.

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Table selector not found | Console warning, graceful no-op |
| onReorder callback throws | Log error, don't break drag-drop |
| Filter input XSS attempt | Text is escaped by jQuery `.text()` comparison |
| Row template missing for FormRowTable add | Console error, no row added |
| beforeunload blocked by browser | Standard browser behavior, no custom handling |

## Migration Path

### Phase 1: Create tableObjects.js
- Implement SortableRows, ColumnFilter, FormRowTable, enhanceTable()
- Unit-testable in isolation

### Phase 2: Migrate DeskSchedulePage
- Replace inline sortable code with `new SortableRows({...})`
- Verify order updates still work
- ~20 lines removed, 5 lines added

### Phase 3: Migrate CountCollectionLinksPage
- Replace inline sortable code
- Keep WebSocket integration in onReorder callback
- Test inline editing still works

### Phase 4: Migrate BlendInstructionEditorPage
- Replace inline sortable code
- Handle excludeSelector for "Add New" row
- Test form row addition still works

### Phase 5: Add ColumnFilter to candidate pages
- Identify tables that would benefit from per-column filtering
- Add filter configuration to those pages

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| SortableRows - instantiate with selector and callback | `SortableRows` constructor |
| SortableRows - rows become draggable | jQuery `.sortable()` in `_init()` |
| SortableRows - visual indication on drag | `start` handler adds `.selected` class |
| SortableRows - update order values on drop | `_updateOrderValues()` method |
| SortableRows - invoke onReorder callback | `_invokeCallback()` method |
| SortableRows - exclude rows by selector | `excludeSelector` option |
| ColumnFilter - filter inputs in header | `_createFilterRow()` method |
| ColumnFilter - hide non-matching rows | `_applyFilters()` method |
| ColumnFilter - cumulative AND filtering | `activeFilters` object with multi-column check |
| ColumnFilter - clear restores rows | `clearFilters()` method |
| FormRowTable - Add New row appended | `addButtonSelector` + `_attachAddHandler()` |
| FormRowTable - new editable row on click | `addRow()` method |
| FormRowTable - persist on blur | `_attachChangeHandlers()` with `onChange` callback |
| FormRowTable - delete row | `_attachDeleteHandlers()` with `onDelete` callback |
| FormRowTable - dirty tracking warning | `_setupDirtyTracking()` with `beforeunload` |
| ColReorder - drag column headers | DataTables ColReorder plugin (opt-in) |
| enhanceTable - compose behaviors | `enhanceTable()` function |
| enhanceTable - no conflicts | Each behavior operates independently on different concerns |

---

**Status**: Draft
