# Count Status Report Requirements

## Problem Statement

There is no single view that shows, for each inventory item in an audit group, the latest Sage transaction activity alongside the latest physical count results. Users currently have to cross-reference multiple screens to determine whether an item's count is current relative to its transaction activity.

## User Stories

### Inventory Manager
- **As an** inventory manager, **I want to** see each audit-group item's most recent Sage transaction next to its most recent physical count, **so that** I can identify items where transactions have occurred since the last count.
- **As an** inventory manager, **I want to** filter the report by record type (blend vs. component), **so that** I can focus on the item category I'm responsible for.

## Acceptance Criteria

### Core Functionality
- **WHEN** the user navigates to the count-status page, **THEN** the system **SHALL** display a table of all items returned by `get_ci_items_for_audit_group()`.
- **FOR** each item, the system **SHALL** display the item code and item description.
- **FOR** each item, the system **SHALL** fetch the most recent `ImItemTransactionHistory` record (by `transactiondate`) and display `transactioncode`, `transactiondate`, and `transactionqty`.
- **FOR** each item, the system **SHALL** determine whether the item is a blend or blend component (based on description prefix), query the appropriate count model (`BlendCountRecord` or `BlendComponentCountRecord`), and display the latest `counted_date`, `counted`, `counted_quantity`, and `variance`.
- **IF** an item has no transaction history, **THEN** the transaction columns **SHALL** display "--" or equivalent empty indicator.
- **IF** an item has no count records, **THEN** the count columns **SHALL** display "--" or equivalent empty indicator.

### User Experience
- **WHEN** the page loads, **THEN** the table **SHALL** be rendered with DataTables for sorting, searching, and export.
- **WHEN** the user selects a record type filter (All / Blend / Component), **THEN** the table **SHALL** refresh showing only matching items.

## Scope

### In Scope
- Read-only report page displaying combined transaction + count data
- Record type filter (all, blend, blendcomponent)
- DataTables integration for sorting, search, and export
- Selector function to build the combined dataset

### Out of Scope
- Editing count records from this page
- Triggering new counts from this page
- Historical trend data (only latest transaction/count shown)
- Warehouse items (only blend and blendcomponent types)

## Dependencies

- `get_ci_items_for_audit_group` selector (exists)
- `ImItemTransactionHistory` model (exists, Sage-synced)
- `BlendCountRecord` model (exists)
- `BlendComponentCountRecord` model (exists)

---

**Status**: Draft
