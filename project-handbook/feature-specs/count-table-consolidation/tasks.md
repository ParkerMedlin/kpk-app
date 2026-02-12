# Count Table Consolidation Tasks

## Overview

Implementation tasks for consolidating `BlendCountRecord`, `BlendComponentCountRecord`, and `WarehouseCountRecord` into a single `CountRecord` model. The work is sequenced so that code changes happen first (against the old models), then the migration runs, and only then are old models removed.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Prepare the Unified Model

- [ ] **1.1** Create `CountRecord` model alongside existing models
  - **Do**: In `core/models.py`, add a new `CountRecord` class with all fields from `BlendCountRecord` plus `counted_by` from `WarehouseCountRecord`. Set `db_table = 'core_countrecord'`. Keep the three old model classes in place for now — they'll be removed after migration.
  - **Deliverable**: `CountRecord` model defined in `core/models.py`
  - **Requirement**: Single unified model

- [ ] **1.2** (USER ACTION) Generate and review the schema migration
  - **Do**: Run `python manage.py makemigrations core` to generate the migration that creates the `core_countrecord` table. Review the generated migration file — it should only create the new table, not touch the old ones.
  - **Deliverable**: Migration file generated
  - **Verify**: `python manage.py showmigrations` shows the new migration as unapplied

- [ ] **1.3** Write the data migration
  - **Do**: Create a new migration file `core/migrations/XXXX_populate_count_record.py` using `RunSQL` + `RunPython`. The migration must:
    1. Copy all rows from `core_blendcountrecord` into `core_countrecord` preserving all field values (including `id` for blend rows — use `INSERT ... SELECT` with explicit column list). Set `counted_by = NULL` for these rows.
    2. Copy all rows from `core_blendcomponentcountrecord` into `core_countrecord` **without specifying id** (let PostgreSQL auto-assign). Capture old→new ID mapping using `RETURNING id` or a RunPython step.
    3. Copy all rows from `prodverse_warehousecountrecord` into `core_countrecord` **without specifying id**. Capture old→new ID mapping.
    4. In a `RunPython` function, iterate `CountCollectionLink` rows. For `record_type='blendcomponent'`, rewrite `count_id_list` using the blendcomponent mapping. For `record_type='warehouse'`, rewrite using the warehouse mapping. Skip/log any IDs that don't map (orphaned references).
    5. Reset the `core_countrecord_id_seq` sequence to `MAX(id) + 1`.
    6. Rename old tables: `core_blendcountrecord` → `core_blendcountrecord_deprecated`, `core_blendcomponentcountrecord` → `core_blendcomponentcountrecord_deprecated`, `prodverse_warehousecountrecord` → `prodverse_warehousecountrecord_deprecated`.
  - **Deliverable**: Data migration file
  - **Requirement**: Data preservation, ID collision avoidance, CountCollectionLink remapping

- [ ] **1.4** Delete old model classes
  - **Do**: Remove `BlendCountRecord` and `BlendComponentCountRecord` from `core/models.py`. Remove `WarehouseCountRecord` from `prodverse/models.py`. Generate the resulting migration (Django will detect the deleted models).
  - **Deliverable**: Old model classes removed, migration generated
  - **Note**: This migration must depend on the data migration from 1.3

## Phase 2: Update Selectors

- [ ] **2.1** Update `inventory_selectors.py`
  - **Do**:
    - Delete `get_count_record_model()` function
    - Replace `count_table_lookup` dict in `get_upcoming_runs_for_items()` with constant `count_table = 'core_countrecord'`
    - Update `get_recently_counted_item_codes()`: replace the two separate queries (`BlendCountRecord` + `BlendComponentCountRecord`) with single `CountRecord.objects.filter(id__in=count_ids)`
    - Update `get_last_counted_dates()`: replace the two separate queries + merge logic with single `CountRecord.objects.filter(...)` query
    - Update `get_latest_count_dates_any()`: same approach — single query
    - Update imports: remove `BlendCountRecord`, `BlendComponentCountRecord`, add `CountRecord`. Remove `WarehouseCountRecord` import from prodverse.
  - **Deliverable**: All selector functions use `CountRecord`
  - **Requirement**: Single model queries

- [ ] **2.2** Update `component_count_selectors.py`
  - **Do**: Change `BlendComponentCountRecord` → `CountRecord` in import and in `get_latest_component_counts()`. Add `.filter(count_type='blendcomponent')` to the query.
  - **Deliverable**: Component count selector uses `CountRecord`

## Phase 3: Update Services

- [ ] **3.1** Update `inventory_services.py`
  - **Do**:
    - Replace `BlendCountRecord` import with `CountRecord`
    - Remove `from prodverse.models import WarehouseCountRecord` if present
    - In `_generate_automated_countlist()`: change `BlendCountRecord.objects.filter(...)` to `CountRecord.objects.filter(count_type='blend', ...)`
    - In `add_count_records()`: change `model = get_count_record_model(record_type)` to use `CountRecord` directly. The `count_type=record_type` is already set on new records.
    - Remove `get_count_record_model` import
  - **Deliverable**: Service layer uses `CountRecord`

- [ ] **3.2** Update `reports_services.py`
  - **Do**:
    - Replace imports: remove `BlendComponentCountRecord`, `BlendCountRecord`. Add `CountRecord`. Remove `WarehouseCountRecord` import.
    - In `generate_count_history_report()`: collapse three-way `if/elif` into `CountRecord.objects.filter(item_code__iexact=item_code).order_by('-counted_date')`
    - In `generate_counts_and_transactions_report()`: same collapse
  - **Deliverable**: Report services use `CountRecord`

- [ ] **3.3** Update `blend_count_services.py`
  - **Do**: Change `count_table` default parameter from `"core_blendcountrecord"` to `"core_countrecord"` in `build_upcoming_blend_runs()`.
  - **Deliverable**: Correct table name for raw SQL

## Phase 4: Update Views and API

- [ ] **4.1** Update `views/web.py`
  - **Do**:
    - In `display_count_report()` (lines 1136-1151): replace three-way `if/elif` with `CountRecord.objects.filter(pk__in=count_ids_list)`
    - In `display_count_records()` (lines 1085-1100): replace `model = get_count_record_model(record_type)` with `CountRecord.objects.filter(count_type=record_type)` for the queryset
    - Remove `get_count_record_model` import from `core.selectors.inventory_selectors` (imported via wildcard, but the function itself will be gone)
    - Verify no other direct references to the three old model names exist in this file
  - **Deliverable**: Views use `CountRecord`

- [ ] **4.2** Update `views/api.py`
  - **Do**:
    - Remove `from core.selectors.inventory_selectors import get_count_record_model` (line 51)
    - In `get_json_containers_from_count()` (line 771): replace `model = get_count_record_model(record_type)` + `model.objects.get(...)` with `CountRecord.objects.get(id=count_record_id)`. Update the `except model.DoesNotExist` to `except CountRecord.DoesNotExist`.
    - In `get_json_container_label_data()` (line 1489): same change
    - In `get_json_all_container_labels_data()` (line 1600): same change
    - Add `from core.models import CountRecord` to imports
  - **Deliverable**: API endpoints use `CountRecord`

## Phase 5: Update WebSocket Consumers

- [ ] **5.1** Update `websockets/count_list/consumer.py`
  - **Do**:
    - Replace imports: remove `BlendComponentCountRecord`, `BlendCountRecord` from `core.models` import. Remove `from prodverse.models import WarehouseCountRecord`. Add `CountRecord` to core.models import.
    - Delete `get_model_for_record_type()` method (lines 390-397)
    - In `save_count()`: replace `model = self.get_model_for_record_type(record_type)` + `record = model.objects.get(id=record_id)` with `record = CountRecord.objects.get(id=record_id)`
    - In `update_on_hand()`: same pattern — `CountRecord.objects.get(id=record_id)`
    - In `delete_count_from_db()`: same — `CountRecord.objects.get(id=record_id)` then `.delete()`
    - In `add_count_to_db()`: replace `model = self.get_model_for_record_type(record_type)` with direct `CountRecord(...)` construction. The `count_type=record_type` assignment already exists.
  - **Deliverable**: Count list consumer uses `CountRecord`

- [ ] **5.2** Update `consumers.py`
  - **Do**: Remove unused imports of `BlendComponentCountRecord`, `BlendCountRecord` from `core.models` and `WarehouseCountRecord` from `prodverse.models`. `CountCollectionConsumer` only manages `CountCollectionLink` — verify it doesn't query count records directly, then just clean up imports.
  - **Deliverable**: Clean imports

## Phase 6: Update Admin and Forms

- [ ] **6.1** Update `admin.py`
  - **Do**: Change `@admin.register(BlendCountRecord)` to `@admin.register(CountRecord)`. Update class name `BlendCountRecordAdmin` → `CountRecordAdmin`. Import `CountRecord` instead of `BlendCountRecord` (currently uses wildcard import, so just verify the class name change works).
  - **Deliverable**: Admin site shows `CountRecord`

- [ ] **6.2** Delete dead form classes from `forms.py`
  - **Do**: Remove `BlendCountRecordForm` (lines 238-279), `BlendComponentCountRecordForm` (lines 281-324), `WarehouseCountRecordForm` (lines 326-367). These are never instantiated anywhere.
  - **Deliverable**: Dead code removed

## Phase 7: Update Raw SQL (ETL Scripts)

- [ ] **7.1** Update `core/table_builds.py`
  - **Do**: Replace `core_blendcountrecord` → `core_countrecord` in the raw SQL on lines 219-224 (component_shortage_WHATIF last_count lookups).
  - **Deliverable**: App-side ETL SQL updated

- [ ] **7.2** Update `local_machine_scripts/.../table_builder.py`
  - **Do**: Replace all raw SQL table references:
    - Lines 295-299: `core_blendcountrecord` → `core_countrecord` (component_shortage_TEMP)
    - Lines 596-604: `core_blendcountrecord` → `core_countrecord` (upcoming_blend_count_TEMP)
    - Lines 647-655: `core_blendcomponentcountrecord` → `core_countrecord` AND add `AND count_type = 'blendcomponent'` filter (upcoming_component_count_TEMP)
    - Lines 810-818: `core_blendcountrecord` → `core_countrecord` (adjustment_statistic_TEMP)
  - **Deliverable**: ETL-side SQL updated
  - **Note**: Must be deployed at the same time as the migration

## Phase 8: Documentation and Cleanup

- [ ] **8.1** Update `CLAUDE.md` and `README.md`
  - **Do**: Replace `core_blendcountrecord` references with `core_countrecord` in the important tables sections of both docs.
  - **Deliverable**: Docs reflect new table name

- [ ] **8.2** (USER ACTION) Run migrations on local dev
  - **Do**: Run `python manage.py migrate` to apply all migrations (schema creation + data migration + old model deletion). Verify:
    - `core_countrecord` table exists with all expected rows
    - `core_blendcountrecord_deprecated`, `core_blendcomponentcountrecord_deprecated`, `prodverse_warehousecountrecord_deprecated` tables exist as backups
    - `CountCollectionLink.count_id_list` values resolve to correct records in `core_countrecord`
  - **Deliverable**: Migration applied successfully on local

- [ ] **8.3** Manual smoke test
  - **Do**: Test the following workflows locally:
    - Open a blend-type count list → verify records display correctly
    - Open a blendcomponent-type count list → verify records display
    - Open a warehouse-type count list → verify records display
    - Edit a counted_quantity on a count record via the count list page → verify WebSocket save works
    - Add a new count record via the count list page → verify it appears
    - Delete a count record → verify it's removed
    - Open the count collection links page → verify all links still navigate correctly
    - Open a count report → verify variance calculations work
    - Hit the container label endpoints → verify JSON returns
    - Check Django admin → verify CountRecord appears and is browsable
  - **Deliverable**: All workflows function identically to pre-migration behavior

- [ ] **8.4** (USER ACTION) Deploy to production
  - **Do**: Coordinate deployment sequence:
    1. Take database backup
    2. `kpk git pull` (gets all code changes)
    3. Run migration on production database
    4. Update ETL table_builder.py on the host machine
    5. Verify ETL cycle completes without errors
    6. Smoke test production
  - **Deliverable**: Production running on unified `CountRecord`

- [ ] **8.5** Drop deprecated tables (post-verification)
  - **Do**: After production has been running cleanly for several days, drop the `_deprecated` backup tables:
    ```sql
    DROP TABLE IF EXISTS core_blendcountrecord_deprecated;
    DROP TABLE IF EXISTS core_blendcomponentcountrecord_deprecated;
    DROP TABLE IF EXISTS prodverse_warehousecountrecord_deprecated;
    ```
  - **Deliverable**: Cleanup complete

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Prepare Unified Model | Not Started | 0/4 |
| 2. Update Selectors | Not Started | 0/2 |
| 3. Update Services | Not Started | 0/3 |
| 4. Update Views and API | Not Started | 0/2 |
| 5. Update WebSocket Consumers | Not Started | 0/2 |
| 6. Update Admin and Forms | Not Started | 0/2 |
| 7. Update Raw SQL (ETL) | Not Started | 0/2 |
| 8. Documentation and Cleanup | Not Started | 0/5 |

**Overall**: 0/22 tasks (0%)

---

**Status**: Draft
