# Table Utilities Consolidation Requirements

## Problem Statement

Table enhancement code (filtering, sorting, drag-and-drop reordering, inline editing, export buttons) is scattered across multiple files with duplicated patterns. This makes maintenance harder and leads to inconsistent behavior across pages. Consolidating these patterns into a single `tableObjects.js` module improves code reuse and consistency.

## User Stories

### Developer
- **As a** developer, **I want to** import table utilities from a single module, **so that** I don't have to hunt through multiple files to find the right class
- **As a** developer, **I want to** add drag-and-drop row reordering with a single class instantiation, **so that** I don't have to copy-paste jQuery sortable boilerplate
- **As a** developer, **I want to** add DataTables with export buttons using a helper function, **so that** I get consistent defaults without remembering all the configuration options
- **As a** developer, **I want** FilterForm in tableObjects.js instead of lookupFormObjects.js, **so that** table-related utilities are co-located

## Acceptance Criteria

### FilterForm (moved from lookupFormObjects.js)
- **WHEN** FilterForm is instantiated with a table selector, **THEN** the system **SHALL** filter rows based on text input matching row content
- **WHEN** a user types in the filter input, **THEN** the system **SHALL** hide rows that don't match and show rows that do
- **WHEN** ignoreSelectors option is provided, **THEN** the system **SHALL** exclude those elements from the search text
- **WHEN** FilterForm is imported from lookupFormObjects.js, **THEN** the system **SHALL** still work (backwards-compatible re-export)

### initDataTableWithExport()
- **WHEN** initDataTableWithExport is called with a table selector, **THEN** the system **SHALL** initialize DataTables with Copy/CSV/Excel/Print buttons
- **WHEN** options are passed, **THEN** the system **SHALL** merge them with defaults (paging: false, order: [[0, 'asc']], dom: 'Bfrtip')
- **WHEN** the user clicks a column header, **THEN** the table **SHALL** sort by that column

### SortableRows
- **WHEN** SortableRows is instantiated with a table selector, **THEN** the system **SHALL** make rows draggable via jQuery UI sortable
- **WHEN** a user starts dragging a row, **THEN** the row **SHALL** receive the 'selected' class for visual feedback
- **WHEN** a user drops a row, **THEN** the system **SHALL** update order values in the first column and invoke the onReorder callback
- **WHEN** getRowId option is provided, **THEN** the system **SHALL** use it to extract row identifiers for the callback

### InlineEditTable
- **WHEN** a user clicks an edit button, **THEN** the row **SHALL** enter edit mode with input fields replacing display values
- **WHEN** a user clicks save, **THEN** the system **SHALL** call the onSave callback with row data
- **WHEN** a user clicks cancel, **THEN** the system **SHALL** restore original values without calling any callback
- **WHEN** a user clicks delete, **THEN** the system **SHALL** confirm and call the onDelete callback
- **WHEN** a user has unsaved changes and tries to edit another row, **THEN** the system **SHALL** prompt to abandon changes

### Error Handling
- **WHEN** a table selector doesn't match any element, **THEN** the system **SHALL** log a warning and gracefully no-op
- **WHEN** an onReorder/onSave/onDelete callback throws, **THEN** the system **SHALL** log the error and display an alert

## Scope

### In Scope
- Move FilterForm from lookupFormObjects.js to tableObjects.js
- Create initDataTableWithExport() helper function
- Create SortableRows class
- Document InlineEditTable interface
- Refactor DeskSchedulePage and CountCollectionLinksPage to use SortableRows
- Backwards-compatible re-export of FilterForm from lookupFormObjects.js

### Out of Scope
- Full InlineEditTable implementation (may keep ContainerClassificationTable as-is if abstraction cost is too high)
- Per-column filtering (not currently used in codebase)
- DataTables ColReorder (not currently used)
- Refactoring pages that don't use these patterns

## Dependencies

- jQuery and jQuery UI (already included globally)
- DataTables library with Buttons extension (already in static files)
- Existing pages: DeskSchedulePage, CountCollectionLinksPage, ContainerClassificationRecords

---

**Status**: Draft
