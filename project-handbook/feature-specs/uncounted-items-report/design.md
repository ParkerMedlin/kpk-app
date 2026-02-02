# Uncounted Items Report - Design

## Overview

A new report page that identifies inventory items not included in any countlist within a configurable time period. Follows the existing `itemsbyauditgroup.html` pattern for display and editing, with filtering by item type and days threshold.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/views/web.py` | Add `display_uncounted_items()` view |
| `app/core/views/api.py` | Add `api_update_audit_group()` for AJAX inline editing |
| `app/core/urls.py` | Add routes for page and API |
| `app/core/services/inventory_services.py` | Add `build_uncounted_items_display()` |
| `app/core/selectors/inventory_selectors.py` | Add `get_uncounted_item_codes()` |

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/templates/core/inventorycounts/uncounted_items.html` | Report page template |
| `app/core/static/core/js/pageModules/uncountedItems.js` | Page initialization, inline editing, countlist creation |

## Data Model

### Model Changes Required

**CountCollectionLink** needs a `created_at` timestamp to support date-range queries:

```python
# In existing CountCollectionLink model:
created_at = models.DateTimeField(auto_now_add=True, null=True)
```

This requires a migration. Existing records will have `created_at = NULL`, which the query will treat as "older than X days" (conservative approach).

### Uses Existing Models
- `CiItem` - Master item list (read-only from Sage)
- `AuditGroup` - Audit group assignments (editable)
- `CountCollectionLink` - Countlist containers with `count_id_list` JSON
- `BlendCountRecord` / `BlendComponentCountRecord` - Individual count records

### Key Query Logic

The core challenge: CountCollectionLink stores count record IDs in `count_id_list` JSON, not item codes. We need to:
1. Find all CountCollectionLinks created within X days
2. Extract all count record IDs from their `count_id_list` arrays
3. Look up those IDs in BlendCountRecord/BlendComponentCountRecord to get item codes
4. Compare against all item codes in CiItem to find those NOT in the set

## URL Routes

```python
# In app/core/urls.py
path('uncounted-items/', views.display_uncounted_items, name='uncounted_items'),
path('api/audit-group/update/', views.api_update_audit_group, name='api_update_audit_group'),
```

## Layer Design

### Selectors (data retrieval)

```python
# In inventory_selectors.py

def get_recently_counted_item_codes(days: int = 3) -> set:
    """
    Returns set of item codes that appear in any countlist created within `days` days.

    Steps:
    1. Query CountCollectionLinks where created_date >= cutoff
    2. Flatten all count_id_list arrays
    3. Query count records by those IDs to get item codes
    4. Return unique set of item codes
    """
    pass

def get_all_active_item_codes(item_type: str = None) -> QuerySet:
    """
    Returns CiItem queryset filtered by item type.

    item_type options:
    - None or 'all': All items
    - 'blend': itemcode starts with 'BLEND-'
    - 'component': itemcode starts with 'CHEM-', 'DYE-', or 'FRAGRANCE-'
    - 'warehouse': Everything else (not blend or component)
    """
    pass

def get_last_counted_dates(item_codes: list) -> dict:
    """
    Returns {item_code: last_counted_date} for given item codes.
    Searches both BlendCountRecord and BlendComponentCountRecord.
    Returns None for items never counted.
    """
    pass
```

### Services (business logic)

```python
# In inventory_services.py

def build_uncounted_items_display(
    days: int = 3,
    item_type: str = None,
    search_query: str = ''
) -> list[dict]:
    """
    Builds display list of uncounted items.

    Returns list of dicts:
    {
        'item_code': str,
        'item_description': str,
        'item_type': str,  # 'blend', 'component', 'warehouse'
        'audit_group': str or None,
        'audit_group_id': int or None,  # For editing
        'last_counted_date': date or None
    }
    """
    # 1. Get recently counted item codes
    counted_codes = get_recently_counted_item_codes(days)

    # 2. Get all active items (filtered by type)
    all_items = get_all_active_item_codes(item_type)

    # 3. Filter to uncounted
    uncounted_items = all_items.exclude(itemcode__in=counted_codes)

    # 4. Apply search filter
    if search_query:
        uncounted_items = uncounted_items.filter(
            Q(itemcode__icontains=search_query) |
            Q(itemcodedesc__icontains=search_query)
        )

    # 5. Enrich with audit group data
    # 6. Enrich with last counted dates

    return display_items


def create_countlist_from_item_codes(item_codes: list, record_type: str) -> CountCollectionLink:
    """
    Creates a new CountCollectionLink from a list of item codes.

    Steps:
    1. For each item_code, create or get a count record (BlendCountRecord or BlendComponentCountRecord)
    2. Collect the record IDs
    3. Create CountCollectionLink with those IDs
    4. Broadcast WebSocket event
    5. Return the new countlist
    """
    pass
```

### Views

```python
# In web.py

def display_uncounted_items(request):
    """
    GET: Renders uncounted items report with filters

    Query params:
    - days: int (default 3)
    - itemType: 'all', 'blend', 'component', 'warehouse'
    - search: text search

    Context:
    - uncounted_items: list of item dicts
    - days: current days filter
    - item_type: current type filter
    - search_query: current search
    - audit_group_form: AuditGroupForm for modal
    """
    pass


# In api.py

def api_update_audit_group(request):
    """
    POST: Updates audit group for an item

    Request JSON:
    {
        'audit_group_id': int,
        'audit_group': str
    }

    Response JSON:
    {
        'success': bool,
        'audit_group': str,
        'error': str (if failed)
    }
    """
    pass
```

## Frontend

### Template Structure

```
uncounted_items.html
├── extends base.html
├── Filter bar
│   ├── Days input (number, default 3)
│   ├── Item type dropdown (All, Blends, Components, Warehouse)
│   ├── Search input
│   └── Reset button
├── Results table (DataTable)
│   ├── Checkbox column (for selection)
│   ├── Item Code
│   ├── Description
│   ├── Item Type
│   ├── Audit Group (editable inline)
│   └── Last Counted
├── Action bar
│   └── Create Countlist button (for selected items)
└── Edit Audit Group modal (reuse existing pattern)
```

### JavaScript

```javascript
// pageModules/uncountedItems.js

// Initialize DataTable with export buttons
// Handle inline audit group editing (click to show dropdown, blur to save)
// Handle checkbox selection for bulk operations
// Handle Create Countlist button -> POST to API -> redirect to countlist
```

### Inline Audit Group Editing Flow

1. User clicks audit group cell -> transforms to dropdown
2. User selects new value -> AJAX POST to `/api/audit-group/update/`
3. On success -> update cell display, show success indicator
4. On error -> revert to original value, show error toast

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| No uncounted items found | Display "All items have been counted within X days" message |
| Audit group update fails | Show error toast, revert cell to previous value |
| Countlist creation fails | Show error alert with details |
| Invalid days parameter | Default to 3, ignore invalid input |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| US-1: See uncounted items within X days | `get_recently_counted_item_codes()` selector, filter bar |
| US-2: Filter by item type | `get_all_active_item_codes()` with type param |
| US-3: Create countlist from report | `create_countlist_from_item_codes()` service |
| AC: Display item code, description, type, audit group, last counted | Template table columns |
| AC: Inline editable audit group | AJAX dropdown in table cells |
| AC: Default 3 days, configurable | Days input with default value |

## Open Questions

1. **Determining record_type for countlist creation**: When creating a countlist from mixed item types, what record_type should be used? Options:
   - Force user to filter by type first (recommended - cleaner)
   - Create separate countlists per type
   - Use a generic record_type

---

**Status**: Draft
