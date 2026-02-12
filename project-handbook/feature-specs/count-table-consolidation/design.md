# Count Table Consolidation Design

## Overview

Replace the three polymorphic count record models (`BlendCountRecord`, `BlendComponentCountRecord`, `WarehouseCountRecord`) with a single `CountRecord` model. The `count_type` field already stores the discriminator (`"blend"`, `"blendcomponent"`, `"warehouse"`), so the model dispatch pattern (`get_model_for_record_type`) becomes a simple `.filter(count_type=...)` call. No URL, template, JavaScript, or user-facing changes are needed.

## Migration Strategy

The migration is the highest-risk part of this project. Here is the exact sequence:

```
1. ALTER TABLE core_blendcountrecord RENAME TO core_countrecord
   → Blend rows keep their existing PKs. Sequence continues from max blend ID.

2. ALTER TABLE core_countrecord ADD COLUMN counted_by TEXT NULL
   → Adds the field that only WarehouseCountRecord had.

3. INSERT INTO core_countrecord (item_code, ..., count_type, counted_by)
     SELECT item_code, ..., count_type, NULL
     FROM core_blendcomponentcountrecord
   → PostgreSQL auto-assigns new IDs. Capture old_id → new_id mapping.

4. INSERT INTO core_countrecord (item_code, ..., count_type, counted_by)
     SELECT item_code, ..., count_type, counted_by
     FROM prodverse_warehousecountrecord
   → Same approach. Capture old_id → new_id mapping.

5. For each CountCollectionLink where record_type = 'blendcomponent':
     Rewrite count_id_list using the blendcomponent old→new mapping.

6. For each CountCollectionLink where record_type = 'warehouse':
     Rewrite count_id_list using the warehouse old→new mapping.

7. ALTER TABLE core_blendcomponentcountrecord RENAME TO core_blendcomponentcountrecord_deprecated
   ALTER TABLE prodverse_warehousecountrecord RENAME TO prodverse_warehousecountrecord_deprecated
   → Kept as backup. Drop after verification.
```

This is a **Django RunSQL + RunPython migration**, not a standard schema migration.

## Affected Components

### Existing Files to Modify

| File | Changes |
|------|---------|
| `app/core/models.py` | Rename `BlendCountRecord` → `CountRecord`, add `counted_by` field, delete `BlendComponentCountRecord` class |
| `app/prodverse/models.py` | Delete `WarehouseCountRecord` class |
| `app/core/forms.py` | Delete `BlendCountRecordForm`, `BlendComponentCountRecordForm`, `WarehouseCountRecordForm` (all three are dead code — never instantiated anywhere) |
| `app/core/admin.py` | Change `BlendCountRecord` → `CountRecord` in registration |
| `app/core/selectors/inventory_selectors.py` | Remove `get_count_record_model()` dispatch. Replace `count_table_lookup` dict with `"core_countrecord"`. Update `get_recently_counted_item_codes()` and `get_last_counted_dates()` / `get_latest_count_dates_any()` to query single model. |
| `app/core/selectors/component_count_selectors.py` | Change `BlendComponentCountRecord` → `CountRecord` with `.filter(count_type='blendcomponent')` |
| `app/core/services/inventory_services.py` | Remove model import branching. Replace `get_count_record_model()` calls with `CountRecord`. Add `count_type` filter where needed. |
| `app/core/services/reports_services.py` | Replace three-way `if/elif` model lookups in `generate_count_history_report()` and `generate_counts_and_transactions_report()` with single `CountRecord` query. |
| `app/core/services/blend_count_services.py` | Change `count_table` default to `"core_countrecord"` |
| `app/core/views/web.py` | Remove `BlendCountRecord`/`BlendComponentCountRecord`/`WarehouseCountRecord` direct references in `display_count_report()`. Replace with `CountRecord.objects.filter(pk__in=...)`. Remove `get_count_record_model` usage in `display_count_records()`. |
| `app/core/views/api.py` | 3 endpoints use `get_count_record_model(record_type)`: `get_json_containers_from_count()` (line 771), `get_json_container_label_data()` (line 1489), `get_json_all_container_labels_data()` (line 1600). Replace with `CountRecord.objects.get(id=count_record_id)`. Remove `get_count_record_model` import. |
| `app/core/websockets/count_list/consumer.py` | Remove `get_model_for_record_type()`. Replace all three model imports with `CountRecord`. All DB methods use `CountRecord` directly. |
| `app/core/consumers.py` | Remove `BlendComponentCountRecord`, `BlendCountRecord` imports, `WarehouseCountRecord` import. Replace with `CountRecord` (consumer doesn't query count records directly, but imports them). |
| `app/core/table_builds.py` | Replace `core_blendcountrecord` → `core_countrecord` in raw SQL |
| `local_machine_scripts/.../table_builder.py` | Replace `core_blendcountrecord` → `core_countrecord` and `core_blendcomponentcountrecord` → `core_countrecord` (with `count_type` filter) in raw SQL |

### New Files to Create

| File | Purpose |
|------|---------|
| `app/core/migrations/XXXX_consolidate_count_tables.py` | Data migration: rename table, add field, copy rows, remap CountCollectionLink IDs, deprecate old tables |

### No New Files Needed For
- Templates (no changes)
- JavaScript (no changes)
- URL routes (no changes)
- WebSocket routes (no changes)

## Data Model

### Unified Model (replaces three models)

```python
class CountRecord(models.Model):
    item_code = models.TextField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)
    expected_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    sage_converted_quantity = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted_date = models.DateField(blank=True, null=True)
    variance = models.DecimalField(max_digits=50, decimal_places=5, blank=True, null=True)
    counted = models.BooleanField(default=False)
    count_type = models.TextField(blank=True, null=True)
    collection_id = models.TextField(blank=True, null=True)
    counted_by = models.TextField(blank=True, null=True)       # ← from WarehouseCountRecord
    comment = models.TextField(blank=True, null=True)
    containers = models.JSONField(default=list, blank=True, null=True)

    class Meta:
        db_table = 'core_countrecord'

    def __str__(self):
        return self.item_code + "; " + str(self.counted_date)
```

### Models Deleted

| Model | Location | Replacement |
|-------|----------|-------------|
| `BlendCountRecord` | `core/models.py` | Renamed to `CountRecord` |
| `BlendComponentCountRecord` | `core/models.py` | Deleted; rows migrated into `CountRecord` |
| `WarehouseCountRecord` | `prodverse/models.py` | Deleted; rows migrated into `CountRecord` |

## Layer Design

### Selectors (data retrieval)

**Before** (inventory_selectors.py):
```python
def get_count_record_model(record_type):
    if record_type == 'blend':
        model = BlendCountRecord
    elif record_type == 'blendcomponent':
        model = BlendComponentCountRecord
    elif record_type == 'warehouse':
        model = WarehouseCountRecord
    return model
```

**After**:
```python
# Function removed entirely. Callers use:
CountRecord.objects.filter(count_type=record_type)
```

**Before** (inventory_selectors.py `get_upcoming_runs_for_items`):
```python
count_table_lookup = {
    'blend': 'core_blendcountrecord',
    'blendcomponent': 'core_blendcomponentcountrecord',
    'warehouse': 'core_warehousecountrecord',   # BUG: wrong table name
}
count_table = count_table_lookup.get(record_type, 'core_warehousecountrecord')
```

**After**:
```python
count_table = 'core_countrecord'
# Raw SQL callers must add WHERE count_type = %s if they need type-specific results.
# But get_latest_count_dates() already matches by item_code, so count_type filter
# is not strictly needed there (an item_code uniquely implies its type).
```

**Before** (inventory_selectors.py `get_recently_counted_item_codes`):
```python
blend_codes = BlendCountRecord.objects.filter(id__in=count_ids).values_list('item_code', flat=True)
component_codes = BlendComponentCountRecord.objects.filter(id__in=count_ids).values_list('item_code', flat=True)
```

**After**:
```python
all_codes = CountRecord.objects.filter(id__in=count_ids).values_list('item_code', flat=True)
```

**Before** (inventory_selectors.py `get_last_counted_dates` / `get_latest_count_dates_any`):
```python
blend_dates = dict(BlendCountRecord.objects.filter(...))
component_dates = dict(BlendComponentCountRecord.objects.filter(...))
# merge logic
```

**After**:
```python
all_dates = dict(CountRecord.objects.filter(...))
# single query, no merge needed
```

**Before** (component_count_selectors.py):
```python
BlendComponentCountRecord.objects.filter(item_code__in=item_codes, counted=True)
```

**After**:
```python
CountRecord.objects.filter(item_code__in=item_codes, counted=True, count_type='blendcomponent')
```

### Services (business logic)

**inventory_services.py changes:**

All calls to `get_count_record_model(record_type)` replaced with `CountRecord`. Where the code creates new records, it sets `count_type=record_type` (already happens today). The `_generate_automated_countlist` function's `BlendCountRecord.objects.filter(...)` for recent count deduplication becomes `CountRecord.objects.filter(count_type='blend', ...)`.

**reports_services.py changes:**

The three-way `if/elif` chains in `generate_count_history_report()` and `generate_counts_and_transactions_report()` collapse to:
```python
count_records = CountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')
```

**blend_count_services.py changes:**

Default `count_table` parameter changes from `"core_blendcountrecord"` to `"core_countrecord"`.

### WebSocket Consumers

**count_list/consumer.py changes:**

```python
# Before (imports):
from core.models import BlendComponentCountRecord, BlendCountRecord, ...
from prodverse.models import WarehouseCountRecord

# After (imports):
from core.models import CountRecord, ...

# Before (method):
def get_model_for_record_type(self, record_type):
    if record_type == 'blend': return BlendCountRecord
    if record_type == 'blendcomponent': return BlendComponentCountRecord
    if record_type == 'warehouse': return WarehouseCountRecord

# After: method deleted. All callers use CountRecord directly.
# e.g., save_count: record = CountRecord.objects.get(id=record_id)
# e.g., add_count_to_db: new_count_record = CountRecord(count_type=record_type, ...)
```

**consumers.py changes:**

Remove the three count-record model imports. If `CountCollectionConsumer` doesn't actually query count records (it only manages `CountCollectionLink`), just clean up the unused imports.

### Views

**web.py `display_count_report()` changes:**

```python
# Before:
if record_type == "blend":
    count_records_queryset = BlendCountRecord.objects.filter(pk__in=count_ids_list)
elif record_type == 'blendcomponent':
    count_records_queryset = BlendComponentCountRecord.objects.filter(pk__in=count_ids_list)
elif record_type == 'warehouse':
    count_records_queryset = WarehouseCountRecord.objects.filter(pk__in=count_ids_list)

# After:
count_records_queryset = CountRecord.objects.filter(pk__in=count_ids_list)
```

### Forms

`BlendCountRecordForm`, `BlendComponentCountRecordForm`, and `WarehouseCountRecordForm` are **dead code** — defined in `forms.py` but never instantiated in any view, template, or JavaScript. All count record CRUD flows through WebSockets (`CountListConsumer`), not Django forms.

**Action:** Delete all three form classes. No replacement needed. If a form is required in the future, it can be created then against `CountRecord`.

### API Endpoints (api.py)

Three JSON endpoints use `get_count_record_model(record_type)` to resolve which model to query:

```python
# Before (in all three endpoints):
model = get_count_record_model(record_type)
count_record = model.objects.get(id=count_record_id)

# After:
count_record = CountRecord.objects.get(id=count_record_id)
# record_type param is no longer needed for model dispatch, but endpoints
# may still accept it for backward compatibility with existing JS callers.
```

Affected endpoints:
- `get_json_containers_from_count()` — retrieves containers JSON for a count record
- `get_json_container_label_data()` — retrieves single container label data
- `get_json_all_container_labels_data()` — retrieves all container labels for batch printing

### Raw SQL Changes

| File | Current Table Name | New Table Name | Notes |
|------|--------------------|----------------|-------|
| `core/table_builds.py:219-224` | `core_blendcountrecord` | `core_countrecord` | Blend shortage WHATIF last_count lookups |
| `local_machine_scripts/.../table_builder.py:295-299` | `core_blendcountrecord` | `core_countrecord` | component_shortage_TEMP last_count |
| `local_machine_scripts/.../table_builder.py:596-604` | `core_blendcountrecord` | `core_countrecord` | upcoming_blend_count_TEMP |
| `local_machine_scripts/.../table_builder.py:647-655` | `core_blendcomponentcountrecord` | `core_countrecord` | upcoming_component_count_TEMP |
| `local_machine_scripts/.../table_builder.py:810-818` | `core_blendcountrecord` | `core_countrecord` | adjustment_statistic_TEMP |
| `core/selectors/inventory_selectors.py:389-394` | `count_table_lookup` dict | `'core_countrecord'` constant | Eliminates the lookup + fixes warehouse bug |
| `core/services/blend_count_services.py:21` | `"core_blendcountrecord"` | `"core_countrecord"` | Default count_table param |

For the raw SQL in `get_latest_count_dates()` (inventory_selectors.py), the table name is passed as a parameter. After consolidation, the caller always passes `"core_countrecord"` — no `count_type` filter is needed because the SQL already matches by `item_code`, which is unique to a type.

For `table_builder.py` queries that reference `core_blendcomponentcountrecord`, the replacement query against `core_countrecord` should add `AND count_type = 'blendcomponent'` for correctness, since blends and components could share an item_code pattern in theory.

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Migration fails mid-way (e.g., after rename but before copy) | Database backup taken before migration. Rollback via `ALTER TABLE core_countrecord RENAME TO core_blendcountrecord`. Deprecated tables still exist. |
| `CountCollectionLink.count_id_list` contains an ID that doesn't map | Log a warning and skip the unmappable ID. This handles orphaned/deleted records gracefully. |
| ETL runs before table_builder.py is updated | ETL queries will fail with "relation does not exist". Must deploy ETL changes at same time. |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| Single `CountRecord` model | `CountRecord` class in `core/models.py` |
| Preserve all field values during migration | `RunSQL` + `RunPython` migration copies every column |
| Preserve `counted_by` from warehouse records | `counted_by` field added to `CountRecord` |
| Remap `CountCollectionLink.count_id_list` | `RunPython` migration builds old→new ID maps and rewrites JSONField |
| Blend IDs preserved (no remapping) | Table rename preserves PKs and sequence |
| No user-facing changes | No template, URL, or JS changes |
| API endpoints continue to work | 3 `api.py` endpoints updated from `get_count_record_model()` to direct `CountRecord` query |
| Dead form code cleaned up | 3 unused form classes deleted from `forms.py` |
| Raw SQL updated | All 7 raw SQL locations updated to `core_countrecord` |
| `record_type` / `count_type` values unchanged | String values `"blend"`, `"blendcomponent"`, `"warehouse"` kept as-is |

---

**Status**: Draft
