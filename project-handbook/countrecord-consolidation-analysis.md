# CountRecord Table Consolidation Analysis

**Date:** 2026-02-16
**Subject:** Should we merge `core_blendcountrecord`, `core_blendcomponentcountrecord`, and `prodverse_warehousecountrecord` into a single table?

## Current State

Three tables with nearly identical schemas store inventory count records:

| Table | App | Unique Fields | Rows (est.) |
|-------|-----|---------------|-------------|
| `core_blendcountrecord` | core | none | bulk of ~12k |
| `core_blendcomponentcountrecord` | core | none | subset of ~12k |
| `prodverse_warehousecountrecord` | prodverse | `counted_by` | subset of ~12k |

All three share 12 identical fields. The only schema difference is `counted_by` on `WarehouseCountRecord`. The `count_type` field already exists on all three tables and functions as a discriminator today.

**Combined total: under 12,000 rows after 3 years of production use.** Even at aggressive growth this table stays trivially small for Postgres.

## Code Duplication Inventory

The three-table split forces duplication across the entire stack:

| Layer | Duplicated Code |
|-------|----------------|
| **Models** | 3 identical model classes (core/models.py, prodverse/models.py) |
| **Forms** | 3 identical ModelForm classes (all dead code, never instantiated) |
| **Dispatcher functions** | 2 identical if/elif dispatchers (`get_count_record_model`, `get_model_for_record_type`) |
| **Selectors** | 6+ functions with parallel queries to 2-3 tables then merge results |
| **Services** | `reports_services.py` has 3-way if/elif chains in 2 functions |
| **Views** | `display_count_report` has 3 identical branches differing only by model class |
| **WebSocket consumer** | Own dispatcher function duplicating the selector one |
| **Raw SQL (ETL)** | `table_builder.py` has separate functions for blend vs component count lookups |
| **Raw SQL (app)** | `get_count_status_rows()` has 2 parallel CTEs for blend and component counts |

### Concrete examples of the pain

**Selectors** - `get_last_counted_dates()` and `get_latest_count_dates_any()` both run the exact same query twice (once per model), then manually merge the dicts in Python. A single table eliminates the merge entirely.

**Reports** - `generate_counts_and_transactions_report()` has a 15-line if/elif/elif block where every branch does the same thing with a different model class.

**Count status SQL** - The 150-line CTE in `get_count_status_rows()` has two parallel CTEs (`latest_blend_count`, `latest_component_count`) that are identical except for the table name. These then get COALESCEd together downstream.

**WebSocket consumer** - Has its own dispatcher function (`get_model_for_record_type`) that is identical to the one in selectors but exists separately because the consumer imports models independently.

## Soft FK Relationships

No hard foreign keys point to these tables. Two tables reference count record IDs loosely:

- **`CountCollectionLink.count_id_list`** - JSONField storing lists of integer IDs. The `record_type` field tells you which table they belong to. After consolidation, IDs just point to one table and `record_type` becomes redundant here (the record itself carries `count_type`).

- **`CountRecordSubmissionLog.record_id`** - TextField storing a count record ID as a string, with `count_type` indicating which table. Same simplification applies.

Both of these get simpler, not harder, after consolidation.

## Pros of Consolidating

### Eliminates structural duplication
Every layer of the stack gets simpler. Two model classes, three form classes, and two dispatcher functions get deleted outright. Selectors that currently run parallel queries and merge results become single queries.

### Simpler queries everywhere
The `get_count_status_rows()` CTE drops from two parallel sub-CTEs to one. `get_last_counted_dates()` becomes a single annotated queryset instead of two queries plus a Python dict merge. Every function that touches count records gets shorter.

### One migration path for schema changes
Adding a field (like `counted_by` was added to warehouse only) currently means deciding which table(s) get it and potentially modifying dispatcher logic. With one table, it's one migration, one model change, done.

### No ID collision risk
`CountCollectionLink.count_id_list` stores raw integer IDs. Today, a blend record and a component record can have the same ID (both tables have independent auto-increment sequences). The system avoids collisions by also storing `record_type`, but this is a fragile design. One table means globally unique IDs.

### Trivial data volume
Under 12k rows after 3 years. Even consolidated, this is a tiny table. No indexing strategy changes needed, no partitioning concerns, no performance implications whatsoever. Postgres handles millions of rows without blinking; 12k is a rounding error.

### Cross-type reporting becomes natural
Any future report that needs to show blend and component counts together (the count status report already does this) works with a single query instead of UNION or parallel queries.

### The `count_type` discriminator already exists
All three tables already have a `count_type` field. The architecture is already designed for a single table - it just wasn't built that way.

## Cons of Consolidating

### Migration requires ID remapping
`BlendComponentCountRecord` and `WarehouseCountRecord` rows need new IDs when inserted into the consolidated table (can't preserve IDs from all three sources). Every `CountCollectionLink.count_id_list` entry and `CountRecordSubmissionLog.record_id` entry for those types needs remapping. This is a one-time cost but must be done carefully.

### Downtime or careful sequencing needed
The migration touches a table that is actively used during count sessions via WebSockets. Needs to be run during off-hours or with the count list feature temporarily disabled. Not a big deal practically, but it's not a zero-downtime migration.

### Touches many files
The consolidation touches ~15-20 files across models, selectors, services, views, API endpoints, WebSocket consumer, ETL scripts, and raw SQL. It's a medium-sized refactor. Each individual change is simple (delete a branch, remove a model, simplify a query) but the surface area is wide.

### Loses implicit type separation
Today, querying `BlendCountRecord.objects.all()` inherently returns only blend records. After consolidation, every query needs a `.filter(count_type='blend')` or equivalent. This is the normal trade-off of single-table inheritance and is the reason the `count_type` field exists, but it's an extra filter to remember.

### Old backups become non-restorable
Existing `pg_dump` backups of the three separate tables produce `INSERT INTO core_blendcountrecord ...` statements. After consolidation, those table names no longer exist, so old backups can't be restored directly. This is mitigated by the compatibility views described below.

### ETL raw SQL needs updating
`table_builder.py` has hardcoded table names in raw SQL strings for `upcoming_blend_count` and `upcoming_component_count` table builds. These need manual SQL string updates. Low risk but can't be caught by the Django ORM migration.

### `WarehouseCountRecord` lives in a different app
It's in `prodverse`, not `core`. Consolidation means either moving it to `core` or the consolidated model straddles apps. The practical answer is just put it in `core` since that's where the other two already live, but it means `prodverse` loses its only count-related model.

## Recommendation

**Do it.** The case is clear-cut.

The data volume makes this a zero-risk migration from a performance standpoint. The schemas are virtually identical (one extra nullable field). The codebase is already architecturally designed for a single table (dispatcher functions, `count_type` discriminator) - the three-table split is legacy friction, not a deliberate design choice.

The cons are all one-time migration costs. The pros are permanent reductions in code duplication and query complexity that pay off every time anyone touches count-related code going forward.

### Backup compatibility via Postgres views

After migration, create views with the old table names pointing at the consolidated table:

```sql
CREATE VIEW core_blendcountrecord AS
  SELECT id, item_code, item_description, expected_quantity, counted_quantity,
         sage_converted_quantity, counted_date, variance, counted, count_type,
         collection_id, comment, containers
  FROM core_countrecord WHERE count_type = 'blend';

CREATE VIEW core_blendcomponentcountrecord AS
  SELECT id, item_code, item_description, expected_quantity, counted_quantity,
         sage_converted_quantity, counted_date, variance, counted, count_type,
         collection_id, comment, containers
  FROM core_countrecord WHERE count_type = 'blendcomponent';

CREATE VIEW prodverse_warehousecountrecord AS
  SELECT id, item_code, item_description, expected_quantity, counted_quantity,
         sage_converted_quantity, counted_date, variance, counted, count_type,
         collection_id, counted_by, comment, containers
  FROM core_countrecord WHERE count_type = 'warehouse';
```

This solves three problems at once:

1. **Old backups restore cleanly.** A `pg_dump` from before the migration produces `INSERT INTO core_blendcountrecord ...` statements. Postgres supports inserts into simple views like these - the rows land in `core_countrecord` with the correct `count_type` automatically.

2. **Safety net for missed references.** Any code path, raw SQL, or ETL script that still references an old table name by accident will keep working instead of crashing. This turns a potential outage into silent correctness while you clean things up.

3. **ETL compatibility.** The hardcoded table names in `table_builder.py` raw SQL (`core_blendcountrecord`, `core_blendcomponentcountrecord`) work against the views without any SQL changes. You can update them at your own pace.

The views can be dropped later once all references are confirmed migrated and old backups age out of relevance.

### Suggested approach
1. Add `counted_by` field to `BlendCountRecord` (or a new `CountRecord` model)
2. Write a data migration that copies rows from the other two tables, capturing an ID mapping
3. Update `CountCollectionLink` and `CountRecordSubmissionLog` references using the mapping
4. Create compatibility views with the old table names
5. Update selectors, services, views, consumer, and ETL SQL to use the single table
6. Delete the old models and dead form classes
7. Drop the views once all old references and backups have aged out
