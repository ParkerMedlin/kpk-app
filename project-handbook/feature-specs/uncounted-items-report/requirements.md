# Uncounted Items Report - Requirements

## Problem Statement

There is no way to identify which item codes have NOT been counted within a given time period. Users need visibility into inventory items that may be going stale or uncounted, so they can ensure complete cycle count coverage across all inventory.

## User Stories

**US-1:** As an inventory manager, I want to see which items have not been included in any countlist in the last X days, so that I can ensure no items are missed in our cycle count rotation.

**US-2:** As an inventory manager, I want to filter uncounted items by type (blend, component, warehouse), so that I can focus on specific categories.

**US-3:** As an inventory manager, I want to create a countlist directly from the uncounted items report, so that I can immediately schedule counts for missing items.

## Acceptance Criteria

### Report Display
- WHEN user navigates to the uncounted items report, THEN the system SHALL display all item codes that do not appear in any countlist created within the last 3 days (default)
- WHEN user changes the days parameter, THEN the system SHALL recalculate and display items not counted within that new period
- WHEN displaying results, THEN the system SHALL show: item code, item description, item type, audit group, and last counted date (if ever)

### Audit Group Editing
- WHEN displaying an item row, THEN the system SHALL show the audit group as an inline editable field
- WHEN user changes an audit group value inline, THEN the system SHALL save the change immediately (no separate save button)
- WHEN audit group is updated, THEN the system SHALL update the AuditGroup record for that item code

### Filtering
- WHEN user selects an item type filter, THEN the system SHALL show only uncounted items of that type
- The system SHALL support filtering by: All, Blends, Components (CHEM/DYE/FRAGRANCE), Warehouse

### Create Countlist Action
- WHEN user selects items from the report and clicks "Create Countlist", THEN the system SHALL create a new CountCollectionLink with those items
- WHEN countlist is created, THEN the system SHALL redirect user to the new countlist

## Scope Boundaries

### In Scope
- Report showing items not in any countlist within X days
- Configurable days parameter (default: 3)
- Filter by item type
- Create countlist from selected items
- Show last counted date for each item

### Out of Scope
- Scheduled/automated reports
- Email notifications
- Export to Excel/CSV (can be added later)
- Historical trending of count coverage
