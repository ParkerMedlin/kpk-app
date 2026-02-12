# Count Status Report Design

## Overview

A read-only report page that joins audit-group items with their latest Sage transaction and latest physical count. Follows the existing Views -> Services -> Selectors pattern. Reuses `get_ci_items_for_audit_group` as the base queryset, adds two new selectors for the enrichment data (latest transaction with qty, latest count with full details), and a service function to assemble the display rows.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/selectors/inventory_selectors.py` | Add `get_latest_transactions_for_items()` and `get_latest_count_details()` |
| `app/core/services/inventory_services.py` | Add `build_count_status_display()` |
| `app/core/views/web.py` | Add `display_count_status()` view |
| `app/core/urls.py` | Add `count-status/` route |
| `app/templates/navbars/office-navbar-items.html` | Add nav link in Inventory dropdown |

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/templates/core/inventorycounts/count_status.html` | Report template |
| `app/core/static/core/js/pageModules/countStatus.js` | DataTable init |

## Data Model

No new models or model changes. Uses existing tables only.

### Unmanaged Tables
- `im_itemtransactionhistory` - latest transaction per item (transactioncode, transactiondate, transactionqty)

### Managed Tables
- `core_blendcountrecord` - latest count for blend items
- `core_blendcomponentcountrecord` - latest count for component items

## URL Routes

```python
# In app/core/urls.py (after count-records route, ~line 35)
path('count-status/', web.display_count_status, name='count-status'),
```

## Layer Design

### Selectors (inventory_selectors.py)

**New: `get_latest_transactions_for_items(item_codes)`**

Similar to existing `get_latest_transaction_dates()` but also returns `transactionqty`. Uses raw SQL with a subquery to get the most recent transaction row per item.

```python
def get_latest_transactions_for_items(item_codes):
    """Return {item_code: {transactioncode, transactiondate, transactionqty}} for the latest transaction per item."""
```

Returns dict mapping item_code -> dict with keys `transactioncode`, `transactiondate`, `transactionqty`. Filters to transaction codes `('BI', 'BR', 'II', 'IA')` consistent with the existing `get_latest_transaction_dates`.

**New: `get_latest_count_details(item_codes)`**

Queries both `BlendCountRecord` and `BlendComponentCountRecord` tables to find the most recent count record (by `counted_date`) for each item, returning `counted_date`, `counted`, `counted_quantity`, and `variance`.

```python
def get_latest_count_details(item_codes):
    """Return {item_code: {counted_date, counted, counted_quantity, variance}} for the latest count per item."""
```

Strategy: For each table, use a subquery to get `MAX(counted_date)` per item_code, then fetch the full row. Merge results from both tables, preferring the more recent date when an item appears in both.

### Services (inventory_services.py)

**New: `build_count_status_display(record_type=None)`**

```python
def build_count_status_display(record_type=None):
    """Build display list for count status report."""
```

Steps:
1. Call `get_ci_items_for_audit_group(record_type)` to get base item set
2. Extract item_codes list
3. Call `get_latest_transactions_for_items(item_codes)`
4. Call `get_latest_count_details(item_codes)`
5. Assemble list of dicts, one per item:
   ```python
   {
       'item_code': str,
       'item_description': str,
       'transaction_code': str or None,
       'transaction_date': date or None,
       'transaction_qty': Decimal or None,
       'counted_date': date or None,
       'counted': bool or None,
       'counted_quantity': Decimal or None,
       'variance': Decimal or None,
   }
   ```
6. Return sorted by item_code

### Views (web.py)

```python
def display_count_status(request):
    """Renders count status report with record type filter."""
    record_type = request.GET.get('recordType')  # 'blend', 'blendcomponent', or None (all)
    items = build_count_status_display(record_type=record_type)
    return render(request, 'core/inventorycounts/count_status.html', {
        'items': items,
        'record_type': record_type or 'all',
    })
```

## Frontend

### Template Structure
```
count_status.html
├── extends base.html
├── includes datatableprerequisites.html
├── loads countStatus.js
├── filter form (recordType select + Apply/Reset buttons)
└── DataTable with columns:
    - Item Code
    - Description
    - Last Txn Code
    - Last Txn Date
    - Last Txn Qty
    - Last Counted Date
    - Counted (Yes/No)
    - Counted Qty
    - Variance
```

### JavaScript (countStatus.js)
- Initialize DataTable on `#countStatusTable`
- Enable column sorting, search, and export buttons
- No additional event handlers needed (pure read-only report)

### Navigation
Add link in `office-navbar-items.html` Inventory dropdown, after "Uncounted Items Report":
```html
<li><a class="dropdown-item" href="/core/count-status/">Count Status Report</a></li>
```

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| No items match filter | Display empty table with "No items found" message via `{% empty %}` |
| Item has no transactions | Display "--" in transaction columns |
| Item has no count records | Display "--" in count columns |
| Invalid recordType param | Treat as "all" (same as `get_ci_items_for_audit_group(None)`) |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| Display all audit-group items | `get_ci_items_for_audit_group()` called in service |
| Show latest transaction fields | `get_latest_transactions_for_items()` selector |
| Show latest count fields (blend or component) | `get_latest_count_details()` selector |
| Filter by record type | `recordType` query param -> passed to selector |
| DataTables sorting/search/export | `countStatus.js` + datatableprerequisites partial |

---

**Status**: Draft
