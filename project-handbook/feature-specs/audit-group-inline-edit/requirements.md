# Audit Group Inline Edit — Requirements

## Problem Statement

The items-by-audit-group page lacks column sorting, uses a full-page-reload modal for editing audit groups, and shows audit group filter options from all record types even when the user has filtered to a specific type. These friction points slow down inventory counting workflows.

## User Stories

### Management Staff
- **As a** count list creator, **I want to** sort the items table by any column, **so that** I can find items by name, last count date, audit group, etc. without relying only on text search.
- **As a** count list creator, **I want to** edit an item's audit group inline without a modal or page reload, **so that** I can quickly reassign items while reviewing the list.
- **As a** count list creator, **I want to** see only audit groups relevant to the current record type in the filter dropdown, **so that** I'm not scrolling through groups that belong to blends when I'm working on components.

## Acceptance Criteria

### Sorting & Filtering (DataTables)
- **WHEN** the page loads, **THEN** the table **SHALL** be sortable by clicking any column header (except the checkbox and edit columns).
- **WHEN** the user types in the DataTables search box, **THEN** rows **SHALL** filter in real time by matching visible cell text.
- **WHEN** DataTables is active, **THEN** export buttons (copy, CSV, Excel, print) **SHALL** be available.

### Inline Editing
- **WHEN** the user clicks the edit pencil on a row, **THEN** the audit group and counting unit cells **SHALL** become inline `<select>` dropdowns, and the actions cell **SHALL** show Save/Cancel buttons.
- **WHEN** the user clicks Save, **THEN** the system **SHALL** POST the updated values to a JSON API endpoint and update the row in place on success.
- **WHEN** the user clicks Cancel, **THEN** the row **SHALL** revert to its original display values.
- **WHEN** the API returns an error, **THEN** the row **SHALL** remain in edit mode and an alert **SHALL** display the error.
- **IF** the item has no existing AuditGroup record (new assignment), **THEN** the system **SHALL** create one via a separate create endpoint.

### Audit Group Dropdown Filtered by Record Type
- **WHEN** the user has selected a `recordType` filter, **THEN** the audit group dropdown **SHALL** only show groups that have at least one item of that record type.
- **WHEN** the user switches record types, **THEN** the dropdown options **SHALL** update to match.

## Scope

### In Scope
- DataTables integration on items-by-audit-group table
- Inline edit for audit group and counting unit fields
- JSON API endpoints for update and create
- Filtering `get_distinct_audit_groups()` by `item_type`
- Removing the edit modal and related POST handling from the view

### Out of Scope
- Inline editing of item_code or item_description (read-only)
- Drag-and-drop row reordering
- Bulk editing of audit groups
- Changes to the missing-audit-groups page

## Dependencies

- `core_auditgroup` table with `item_type` field for record-type filtering
- DataTables library via `datatableprerequisites.html` partial
- `tableObjects.js` — `initDataTableWithExport`
- Existing inline-edit pattern from `containerClassificationRecords.js`

---

**Status**: Draft
