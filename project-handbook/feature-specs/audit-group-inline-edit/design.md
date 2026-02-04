# Audit Group Inline Edit — Design

## Overview

Replace the modal-based edit flow on items-by-audit-group with DataTables (sort/filter/export) and inline row editing backed by JSON API endpoints. Filter the audit group dropdown by the active `recordType` using the existing `item_type` field on `AuditGroup`.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/templates/core/inventorycounts/itemsbyauditgroup.html` | Add DataTables partial, add `data-field`/`data-id` attributes to cells/rows, remove modal, remove text search input, embed audit group + counting unit choice lists as JS data |
| `app/core/static/core/js/pageModules/itemsByAuditGroup.js` | Replace `FilterForm`/`DropDownFilter`/`ItemsByAuditGroupPage` with `initDataTableWithExport` + inline edit class |
| `app/core/views/web.py` | Remove POST handling block from `display_items_by_audit_group`, remove `AuditGroupForm` from context |
| `app/core/services/inventory_services.py` | Add `update_audit_group_api` and `create_audit_group_api` JSON endpoint functions |
| `app/core/selectors/inventory_selectors.py` | Add `record_type` parameter to `get_distinct_audit_groups()` |
| `app/core/urls.py` | Add two API routes |
| `app/core/static/core/js/objects/pageObjects.js` | Remove `ItemsByAuditGroupPage` class (logic moves to pageModule) |

### New Files to Create
None. All logic fits in existing files.

## Data Model

No model changes. The existing `AuditGroup` model has all needed fields:
- `item_code`, `item_description`, `audit_group`, `item_type`, `counting_unit`

The `item_type` field already stores record type values (`blend`, `blendcomponent`, `warehouse`) and is the key for filtering the dropdown.

## URL Routes

```python
# In app/core/urls.py — add to existing API section
path('api/audit-group/<int:audit_group_id>/', inventory_services.update_audit_group_api, name='update-audit-group-api'),
path('api/audit-group/create/', inventory_services.create_audit_group_api, name='create-audit-group-api'),
```

## Layer Design

### Selectors (data retrieval)
```python
def get_distinct_audit_groups(record_type=None):
    """Return ordered list of distinct audit group names, optionally filtered by item_type."""
    qs = AuditGroup.objects.all()
    if record_type:
        qs = qs.filter(item_type=record_type)
    return list(qs.values_list('audit_group', flat=True).distinct().order_by('audit_group'))
```

Both call sites in `build_audit_group_display_items` will pass `record_type` through.

### Services (API endpoints)
```python
@login_required
@require_POST
def update_audit_group_api(request, audit_group_id):
    """Update an existing AuditGroup record. Returns JSON."""
    audit_group_item = get_object_or_404(AuditGroup, pk=audit_group_id)
    payload = json.loads(request.body)
    merged = {field: payload.get(field, getattr(audit_group_item, field))
              for field in ('item_code', 'item_description', 'audit_group', 'counting_unit', 'item_type')}
    form = AuditGroupForm(data=merged, instance=audit_group_item)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    updated = form.save()
    return JsonResponse({'status': 'success', 'record': _serialize_audit_group(updated)})

@login_required
@require_POST
def create_audit_group_api(request):
    """Create a new AuditGroup record. Returns JSON with status 201."""
    payload = json.loads(request.body)
    form = AuditGroupForm(data=payload)
    if not form.is_valid():
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    record = form.save()
    return JsonResponse({'status': 'success', 'record': _serialize_audit_group(record)}, status=201)

def _serialize_audit_group(record):
    return {
        'id': record.id,
        'item_code': record.item_code,
        'item_description': record.item_description,
        'audit_group': record.audit_group,
        'counting_unit': record.counting_unit,
        'item_type': record.item_type,
    }
```

### Views
```python
def display_items_by_audit_group(request):
    """GET-only. Renders page with DataTables. No POST handling."""
    # parse recordType, search_query, selected_audit_group from GET params
    # call build_audit_group_display_items(...)
    # context: audit_group_queryset, audit_group_list, record_type, search_query, selected_audit_group
    # (no longer includes edit_audit_group_form)
```

## Frontend

### Template Structure
```
itemsbyauditgroup.html
├── extends base.html
├── {% include 'core/partials/datatableprerequisites.html' %}
├── loads itemsByAuditGroup.js (module)
├── audit group dropdown filter (server-side GET, unchanged)
├── <table #displayTable> with data-field and data-id attributes
└── <script> block embedding AUDIT_GROUP_CHOICES and COUNTING_UNIT_CHOICES as JSON
```

Key template changes:
- Each `<tr>` gets `data-id="{{ item.id|default:'' }}"` and `data-item-code="{{ item.item_code }}"` and `data-item-description="{{ item.item_description }}"` and `data-item-type="{{ item.item_type }}"`
- Audit group `<td>` gets `data-field="audit_group"`
- Counting unit `<td>` gets `data-field="counting_unit"`
- Actions `<td>` gets `data-field="actions"`
- Modal div removed entirely
- Text search input removed (DataTables provides its own)
- Audit group choices and counting unit choices embedded as `<script>` JSON for populating inline selects

### JavaScript
```javascript
// pageModules/itemsByAuditGroup.js
import { initDataTableWithExport } from '../objects/tableObjects.js';
import { ShiftSelectCheckBoxes, SelectAllCheckBox } from '../objects/pageUtilities.js';
import { CreateCountListButton, BlendComponentFilterButton } from '../objects/buttonObjects.js';

// On ready:
// 1. initDataTableWithExport('#displayTable', { columnDefs for non-sortable cols })
// 2. new CreateCountListButton()
// 3. new ShiftSelectCheckBoxes()
// 4. new BlendComponentFilterButton(...)
// 5. new SelectAllCheckBox()
// 6. Set up inline edit handlers:
//    - Click .editRowButton → enterEditMode(row)
//    - enterEditMode: snapshot row data, replace audit_group/counting_unit cells with <select>,
//      replace actions cell with Save/Cancel buttons
//    - Save: collect values, POST JSON to /core/api/audit-group/<id>/ (or /create/ if no id),
//      on success exitEditMode with new values
//    - Cancel: exitEditMode with snapshot values
```

The `DropDownFilter`, `FilterForm`, and `ItemsByAuditGroupPage` imports are removed. The audit group dropdown auto-submit on change is handled with a simple inline event listener rather than a class.

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| API returns 400 (validation error) | Alert with error details, row stays in edit mode |
| API returns 404 (record deleted) | Alert "Record not found", row stays in edit mode |
| Network failure | Alert "Unable to save. Check your connection.", row stays in edit mode |
| No `id` on row (new record) | Use create endpoint instead of update |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| Sort by any column | `initDataTableWithExport` on `#displayTable` |
| Real-time text filter | DataTables built-in search |
| Export buttons | DataTables buttons config |
| Inline edit with selects | `enterEditMode()` in pageModule JS |
| Async save | `update_audit_group_api` / `create_audit_group_api` endpoints |
| Cancel reverts row | Snapshot/restore pattern in JS |
| Error keeps edit mode | Error handler in save flow |
| Dropdown filtered by recordType | `get_distinct_audit_groups(record_type)` |

---

**Status**: Draft
