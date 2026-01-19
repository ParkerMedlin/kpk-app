# Table Utilities Consolidation Requirements

## Problem Statement

Table-related JavaScript functionality is scattered across the codebase with significant duplication. Three pages have nearly identical drag-and-drop implementations, filtering is text-based rather than per-column, and inline form row patterns are reimplemented from scratch on each page. This increases maintenance burden and makes it harder to add consistent table behaviors to new pages.

## User Stories

### Developer
- **As a** developer, **I want to** add row drag-and-drop to a table with one line of code, **so that** I don't have to copy/paste 20 lines of boilerplate each time.
- **As a** developer, **I want to** compose multiple table behaviors (sorting, filtering, inline editing), **so that** I can pick what I need without taking everything.
- **As a** developer, **I want to** add per-column filtering to a table, **so that** users can filter on specific columns instead of searching all text.

### End User
- **As a** warehouse user, **I want to** filter a table by a specific column value, **so that** I can find items faster than searching all visible text.
- **As a** blend scheduler, **I want to** reorder table rows by dragging, **so that** I can prioritize items visually.

## Acceptance Criteria

### SortableRows (Drag-and-Drop)

- **WHEN** a developer instantiates SortableRows with a table selector and onReorder callback, **THEN** the table rows **SHALL** become draggable.
- **WHEN** a user drags a row to a new position, **THEN** the system **SHALL** visually indicate the dragged row (e.g., "selected" class).
- **WHEN** a user drops a row, **THEN** the system **SHALL** update order column values and invoke the onReorder callback.
- **WHEN** a row is excluded by selector (e.g., "Add New" button row), **THEN** that row **SHALL NOT** be draggable.

### ColumnFilter

- **WHEN** a developer instantiates ColumnFilter with column configuration, **THEN** filter inputs **SHALL** appear in the table header row.
- **WHEN** a user types in a column filter input, **THEN** the table **SHALL** hide rows that don't match on that column.
- **WHEN** multiple column filters are active, **THEN** filtering **SHALL** be cumulative (AND logic).
- **WHEN** a filter input is cleared, **THEN** the table **SHALL** show all rows that pass other active filters.

### FormRowTable (Inline Editing)

- **WHEN** a developer instantiates FormRowTable with configuration, **THEN** an "Add New" row **SHALL** be appended to the table.
- **WHEN** a user clicks "Add New", **THEN** a new editable row **SHALL** appear with empty fields.
- **WHEN** a user modifies a field and loses focus, **THEN** the system **SHALL** persist the change (via callback or API).
- **WHEN** a user clicks a row's delete button, **THEN** the system **SHALL** remove that row (via callback or API).
- **WHEN** unsaved changes exist and user navigates away, **THEN** the system **SHALL** warn the user (dirty tracking).

### Column Reordering

- **WHEN** ColReorder is enabled on a DataTables instance, **THEN** users **SHALL** be able to drag column headers to reorder.
- **WHEN** columns are reordered, **THEN** the new order **SHALL** persist for the session (localStorage optional).

### enhanceTable() Helper

- **WHEN** a developer calls enhanceTable() with multiple behavior options, **THEN** all requested behaviors **SHALL** be applied to the table.
- **WHEN** behaviors are composed, **THEN** they **SHALL NOT** conflict (e.g., row sorting shouldn't break column filtering).

## Scope

### In Scope
- Create `objects/tableObjects.js` with SortableRows, ColumnFilter, FormRowTable classes
- Migrate DeskSchedulePage, CountCollectionLinksPage, BlendInstructionEditorPage to use SortableRows
- Per-column text filtering inputs in table headers
- Add DataTables ColReorder plugin for column reordering (where DataTables is already in use)
- enhanceTable() helper to compose multiple behaviors
- Dirty form tracking for inline editing

### Out of Scope
- Converting non-DataTables tables to DataTables (only add ColReorder where DT already exists)
- Server-side pagination/filtering
- Undo/redo functionality
- Keyboard navigation between editable cells
- Mobile-specific touch gestures (beyond jQuery UI's touch-punch if already present)

## Dependencies

- jQuery and jQuery UI (.sortable) - already in stack
- DataTables (for ColReorder plugin) - already in stack for some pages
- Existing pages using sortable: DeskSchedulePage, CountCollectionLinksPage, BlendInstructionEditorPage
- Existing filtering classes: FilterForm, DropDownFilter in lookupFormObjects.js

---

**Status**: Draft
