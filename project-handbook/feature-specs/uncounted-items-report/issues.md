# Uncounted Items Report – Issues

Discovered during testing of the uncounted items report feature.

---

## Issue 1: Item Type Filter Shows Wrong Type in Display

**Problem:** When the "Item Type" dropdown is set to "Blends", the returned items all display "Warehouse" in the Item Type column, not "Blend". The filter correctly limits the results to blend items, but the display type is misclassified.

**Expected Behavior:**
- When filtering by "Blends": Items should display "Blend" in the Item Type column
- When filtering by "Components": Items should display "Component" in the Item Type column
- When filtering by "Warehouse": Items should display "Warehouse" in the Item Type column
- When filtering by "All": Items should display their correct type based on their category

**Root Cause Analysis:**

The issue stems from an inconsistency between how items are **filtered** vs. how they are **classified for display**:

1. **SQL Filtering** (`get_relevant_ci_item_itemcodes` in `inventory_selectors.py:168-346`):
   - Filters by `itemcodedesc` (the item **description** field)
   - Example: `WHERE (itemcodedesc like 'BLEND%')`

2. **Display Classification** (`_classify_item_code` in `inventory_services.py:420-431`):
   - Classifies by `itemcode` (the item **code** field)
   - Example: `if upper_code.startswith('BLEND-'):`

3. **The Mismatch**:
   - An item might have description `"BLEND - Special Mix"` (matching the SQL filter)
   - But have code `"100501K"` (not starting with 'BLEND-')
   - Result: Filtered as a blend, but displayed as "Warehouse"

The entire codebase uses `itemcodedesc` for item type classification:
- `forms.py:502` - `itemcodedesc__istartswith='BLEND'`
- `api.py:1143` - `itemcodedesc__startswith='BLEND'`
- `inventory_selectors.py:357` - `itemcodedesc__istartswith='BLEND'`

But `_classify_item_code` uses `itemcode`, which is inconsistent.

```
Data Flow:

  User selects "Blends"
         ↓
  item_type='blend' → filter_string='blends'
         ↓
  SQL: WHERE itemcodedesc like 'BLEND%'
         ↓
  Returns items where DESCRIPTION starts with BLEND
         ↓
  _classify_item_code(item_code)
         ↓
  Checks if CODE starts with 'BLEND-'
         ↓
  CODE doesn't match → returns 'warehouse'
         ↓
  Display shows "Warehouse" ← WRONG!
```

**Code Locations:**
- `inventory_selectors.py` lines 197-206 — SQL filter for 'blends' uses `itemcodedesc like 'BLEND%'`
- `inventory_services.py` lines 420-431 — `_classify_item_code()` checks `itemcode` prefix
- `inventory_services.py` lines 335-336 — Calls `_classify_item_code(item_code)` in display builder

**Fix Approach:**

The cleanest fix has two parts:

1. **When a filter is applied** (`item_type` is 'blend', 'component', or 'warehouse'):
   - We already know the type from the filter parameter
   - Pass this through to avoid re-classification
   - All items returned by that filter ARE that type (by definition of the SQL filter)

2. **When no filter is applied** (`item_type` is None/all):
   - Need to classify each item individually
   - Create `_classify_by_description(description)` to match how SQL filters work
   - Use description-based classification for consistency

This approach:
- Preserves the existing `_classify_item_code` for its use in `create_countlist_from_item_codes` (which needs code-based classification for record table selection)
- Fixes the display issue without breaking other functionality
- Matches the codebase convention of filtering by description

### Tasks

- [x] 1.1 Create `_classify_by_description(description)` helper function
  - **Do**: Add function to `inventory_services.py` that classifies by description prefix (BLEND%, CHEM%/DYE%/FRAGRANCE%, else warehouse)
  - **Deliverable**: New helper function that mirrors SQL filter logic

- [x] 1.2 Update `build_uncounted_items_display` to pass known item_type when filtered
  - **Do**: When `item_type` parameter is set (not None), use that value directly for `display_type` instead of calling `_classify_item_code`
  - **Deliverable**: Filtered items display correct type

- [x] 1.3 Update `build_uncounted_items_display` to use description-based classification when unfiltered
  - **Do**: When `item_type` is None (showing all), call `_classify_by_description(item_desc)` instead of `_classify_item_code(item_code)`
  - **Deliverable**: Unfiltered view shows correct types

- [ ] 1.4 Test: Filter by "Blends" shows "Blend" in Item Type column
- [ ] 1.5 Test: Filter by "Components" shows "Component" in Item Type column
- [ ] 1.6 Test: Filter by "Warehouse" shows "Warehouse" in Item Type column
- [ ] 1.7 Test: Filter by "All" shows correct type for each item
- [ ] 1.8 Test: "Create Countlist" still works correctly (uses code-based classification)

---

## Issue 2: Query Excludes Items Already in Audit Groups

**Problem:** The uncounted items report returns far fewer items than expected (~10 blends instead of 300+, ~1 component instead of 200+). Most items are being filtered out.

**Expected Behavior:**
- Filtering by "Blends": Should return all blend items not counted within X days (~300+ items)
- Filtering by "Components": Should return all component items not counted within X days (~200+ items)
- Items should be included regardless of whether they're assigned to an audit group

**Root Cause Analysis:**

The `get_relevant_ci_item_itemcodes` function was designed for a **different purpose** — it's used when adding items TO audit groups, so it excludes items that are already in audit groups. But for the uncounted items report, we want ALL items regardless of audit group membership.

The problematic SQL clause appears in every branch of `get_relevant_ci_item_itemcodes`:

```sql
AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)
```

This excludes any item that has a record in `core_auditgroup`. Since most blends and components ARE assigned to audit groups (for normal counting workflows), they get filtered out of the uncounted items report.

```
Expected flow:
  "Show me blends not counted in 3 days"
         ↓
  Return ALL blends, minus recently counted ones
         ↓
  ~300 results

Actual flow:
  "Show me blends not counted in 3 days"
         ↓
  Return blends NOT IN audit groups, minus recently counted ones
         ↓
  ~10 results (only orphaned items)
```

**Code Locations:**
- `inventory_selectors.py` line 192 — `AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)` (blends_and_components)
- `inventory_selectors.py` line 202 — Same exclusion (blends)
- `inventory_selectors.py` line 214 — Same exclusion (components)
- `inventory_selectors.py` line 273 — Same exclusion (non_blend)
- `inventory_selectors.py` line 336 — Same exclusion (all/else branch)

**Fix Approach:**

Add an optional parameter to `get_relevant_ci_item_itemcodes` to control whether audit group items are excluded:

```python
def get_relevant_ci_item_itemcodes(filter_string, exclude_audit_group_items=True):
```

- Default `True` preserves backward compatibility for existing callers (audit group management views)
- Pass `False` from `build_uncounted_items_display` to include all items
- Conditionally include/exclude the `NOT IN (SELECT item_code FROM core_auditgroup)` clause based on parameter

### Tasks

- [x] 2.1 Add `exclude_audit_group_items` parameter to `get_relevant_ci_item_itemcodes`
  - **Do**: Add optional parameter `exclude_audit_group_items=True` to function signature in `inventory_selectors.py`
  - **Deliverable**: Parameter added with default preserving existing behavior

- [x] 2.2 Conditionally apply audit group exclusion in SQL queries
  - **Do**: For each SQL branch, only include `AND ci.itemcode NOT IN (SELECT item_code FROM core_auditgroup)` when `exclude_audit_group_items=True`
  - **Deliverable**: SQL queries respect the parameter

- [x] 2.3 Update `build_uncounted_items_display` to pass `exclude_audit_group_items=False`
  - **Do**: Change call in `inventory_services.py` to `get_relevant_ci_item_itemcodes(filter_string, exclude_audit_group_items=False)`
  - **Deliverable**: Uncounted items report includes all items

- [ ] 2.4 Test: Filter by "Blends" returns expected count (~300+ items)
- [ ] 2.5 Test: Filter by "Components" returns expected count (~200+ items)
- [ ] 2.6 Test: Filter by "All" returns items from all categories
- [ ] 2.7 Test: Existing audit group management views still work (items in groups excluded)

---

## Issue 3: Add Latest Countlist Date Column

**Problem:** The report only shows "Last Counted" which filters by `counted=True`. Users need to see when an item was last included in ANY countlist, regardless of whether it was marked as counted.

**Expected Behavior:**
- New column "Latest Countlist Date" shows the most recent count record date for each item
- This date is independent of the `counted` boolean flag
- "Last Valid Count" (renamed from "Last Counted") continues showing only confirmed counts (`counted=True`)

**Root Cause Analysis:**

The existing `get_last_counted_dates` selector filters by `counted=True`:

```python
BlendCountRecord.objects
    .filter(item_code__in=item_codes, counted_date__isnull=False, counted=True)
```

This means items that were on a countlist but not yet confirmed as counted don't show any date.

**Fix Approach:**

Create a new selector `get_latest_count_dates_any` that queries both `BlendCountRecord` and `BlendComponentCountRecord` without the `counted=True` filter.

**Code Locations:**
- `inventory_selectors.py` lines 499-529 — New `get_latest_count_dates_any()` function
- `inventory_services.py` line 36 — Import added
- `inventory_services.py` line 332 — Call to new function
- `inventory_services.py` line 350 — Added `latest_count_date` to display dict
- `uncounted_items.html` lines 55-56 — Column headers renamed/added
- `uncounted_items.html` lines 77-83 — New column data cell

### Tasks

- [x] 3.1 Create `get_latest_count_dates_any` selector function
  - **Do**: Add function to `inventory_selectors.py` that queries both count tables without `counted=True` filter
  - **Deliverable**: New selector returns latest count date regardless of counted flag

- [x] 3.2 Import and call new selector in service
  - **Do**: Import `get_latest_count_dates_any` in `inventory_services.py`, call it in `build_uncounted_items_display`, add `latest_count_date` to display items
  - **Deliverable**: Service provides both date fields

- [x] 3.3 Update template with new column
  - **Do**: Add "Latest Countlist Date" column header and data cell, rename "Last Counted" to "Last Valid Count", update colspan
  - **Deliverable**: Report displays both date columns

---

## Progress

| Issue | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Item Type Filter Shows Wrong Type | In Progress | 3/8 |
| 2. Query Excludes Items in Audit Groups | In Progress | 3/7 |
| 3. Add Latest Countlist Date Column | Complete | 3/3 |

**Overall**: 9/18 tasks (50%)

---

**Status**: In Progress
