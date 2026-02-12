# Count Table Consolidation Requirements

## Problem Statement

The inventory count system uses three nearly identical database tables (`core_blendcountrecord`, `core_blendcomponentcountrecord`, `prodverse_warehousecountrecord`) to store count records that differ only by their `count_type` value. This triplication forces every layer of the stack — models, forms, selectors, services, consumers, views, and raw SQL — to maintain parallel `if/elif/else` branches for record type routing. It increases maintenance burden, creates divergence risks (e.g., `counted_by` exists only on `WarehouseCountRecord`), and has already produced a latent bug where raw SQL references `core_warehousecountrecord` instead of the actual `prodverse_warehousecountrecord`.

## User Stories

### Developer / Maintainer
- **As a** developer, **I want** a single count record table, **so that** I stop writing three-way branching logic for every count-related feature.
- **As a** developer, **I want** `count_type` to be the sole discriminator for record types, **so that** the polymorphic dispatch pattern (`get_model_for_record_type`) can be eliminated.

### End User (Inventory Counter)
- **As an** inventory counter, **I want** the count list system to work exactly as it does today, **so that** I don't have to learn anything new or re-enter data.

## Acceptance Criteria

### Data Migration
- **WHEN** the migration runs, **THEN** the system **SHALL** rename `core_blendcountrecord` to `core_countrecord`, keeping all existing blend rows and their primary keys intact.
- **WHEN** blendcomponent and warehouse rows are inserted into the consolidated table, **THEN** the system **SHALL** let PostgreSQL auto-assign new IDs from the sequence (avoiding ID collisions with existing blend rows) and build an old-ID → new-ID mapping for each source table.
- **WHEN** a record from `WarehouseCountRecord` has a non-null `counted_by` value, **THEN** that value **SHALL** be preserved in the consolidated table (the `counted_by` field must be added to the unified model).
- **WHEN** migration completes, **THEN** the system **SHALL** use the old-ID → new-ID mappings to rewrite `CountCollectionLink.count_id_list` for every link with `record_type` of `"blendcomponent"` or `"warehouse"`. Blend-type links need no remapping since blend IDs are preserved by the rename.

### Code Behavior (Post-Migration)
- **WHEN** the application queries count records, **THEN** it **SHALL** use a single `CountRecord` model filtered by `count_type` instead of dispatching to separate model classes.
- **WHEN** a WebSocket action specifies `record_type` of `"blend"`, `"blendcomponent"`, or `"warehouse"`, **THEN** the consumer **SHALL** query the single `CountRecord` table filtered by `count_type`.
- **WHEN** raw SQL references count record tables, **THEN** those queries **SHALL** target `core_countrecord` (with appropriate `count_type` filtering where needed).
- **WHEN** the admin site is accessed, **THEN** `CountRecord` **SHALL** appear with the same list display fields as the current `BlendCountRecordAdmin`.

### Backward Compatibility
- **WHEN** the front end sends `recordType` parameters (`"blend"`, `"blendcomponent"`, `"warehouse"`), **THEN** all endpoints **SHALL** continue to accept and correctly route those values.
- **WHEN** existing `CountCollectionLink` records reference a `record_type`, **THEN** those values **SHALL** remain valid and functional.

### No User-Facing Changes
- **WHEN** a user opens any count list page, **THEN** the UI **SHALL** look and behave identically to the current system.
- **WHEN** a user adds, edits, or deletes a count record via WebSocket, **THEN** the real-time updates **SHALL** function as they do today.

## Scope

### In Scope
- Create unified `CountRecord` model in `core` app with all fields from the three existing models
- Rename `core_blendcountrecord` → `core_countrecord` (blend rows keep their PKs, zero remapping needed)
- Insert blendcomponent and warehouse rows into `core_countrecord` with auto-assigned new IDs (avoids PK collisions)
- Build old-ID → new-ID mappings and rewrite `CountCollectionLink.count_id_list` for `blendcomponent` and `warehouse` type links
- Update all Python references: models, forms, selectors, services, views, consumers, admin
- Update all raw SQL in `table_builds.py` and `local_machine_scripts/.../table_builder.py`
- Update `inventory_selectors.py` count table name lookups
- Remove `BlendComponentCountRecord` model and `WarehouseCountRecord` model
- Remove the three separate form classes, replace with single `CountRecordForm`
- Remove `get_model_for_record_type` / `get_count_record_model` dispatch functions

### Out of Scope
- Changing the front-end JavaScript (the `recordType` parameter values stay the same)
- Changing URL patterns or template names
- Changing the `CountCollectionLink` model structure (beyond updating `count_id_list` IDs)
- Adding new features to the count system
- Changing the `record_type` / `count_type` string values (`"blend"`, `"blendcomponent"`, `"warehouse"`)

## Dependencies

- PostgreSQL database access for data migration
- Django migration framework
- Redis (WebSocket layer must remain functional during/after migration)
- ETL table_builder scripts must be updated before next ETL run after migration

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| **PK collisions** — blendcomponent/warehouse IDs overlap with blend IDs | Rename blend table first (preserving its IDs), then INSERT the other two tables' rows without specifying IDs so PostgreSQL auto-assigns from the sequence. Blend-type `CountCollectionLink` entries need zero remapping. |
| **Stale CountCollectionLink references** — `count_id_list` contains old PKs for blendcomponent/warehouse links | Migration builds old-ID → new-ID mapping per source table, then rewrites `count_id_list` for affected `CountCollectionLink` rows only (`record_type` in `('blendcomponent', 'warehouse')`). |
| **ETL scripts run with stale table names** | Deploy ETL table_builder.py updates at the same time as Django migration |
| **Large data volume causes slow migration** | Run during off-hours; migration is a one-time operation |
| **Rollback difficulty** | Full database backup before migration; keep old tables renamed to `_deprecated` suffix until verified |

---

**Status**: Draft
