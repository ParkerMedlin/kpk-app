# Uncounted Items Report – Change Orders

## Overview

Change orders for the uncounted items report feature after initial implementation.

**Parent**: See `tasks.md` for completed Phase 1–4 work.

---

## Phase 6: Use get_relevant_ci_item_itemcodes for Item Source

_Replace the custom `get_all_active_item_codes` selector with the existing `get_relevant_ci_item_itemcodes` function, which properly filters by quantity on hand, excludes items already in audit groups, and uses the established filter patterns._

**Analysis:** The initial implementation created a new `get_all_active_item_codes` function that queried CiItem directly. However, `get_relevant_ci_item_itemcodes` already exists and has the proper business logic:
- Joins with IM_ItemWarehouse for quantity on hand filtering
- Excludes items already in audit groups
- Excludes specific item codes ('030143', '030182')
- Excludes items starting with '/'
- Only returns items with positive quantity on hand

The existing function only had filters for 'blends_and_components', 'blends', and 'non_blend'. A 'components' filter was added for CHEM/DYE/FRAGRANCE items only.

**No changes needed in:**
- `web.py` - Uses service function, no changes to interface
- `api.py` - Uses service function, no changes to interface
- Template/JS - No changes to data format returned by service

### Selector Changes

- [x] **6.1** Add 'components' filter to get_relevant_ci_item_itemcodes
  - **Do**: Add new `elif filter_string == 'components'` branch to `inventory_selectors.py:get_relevant_ci_item_itemcodes()` for CHEM/DYE/FRAGRANCE items
  - **Deliverable**: Filter works for component-only queries

### Service Changes

- [x] **6.2** Update build_uncounted_items_display to use get_relevant_ci_item_itemcodes
  - **Do**: Replace `get_all_active_item_codes(item_type)` call with `get_relevant_ci_item_itemcodes(filter_string)` in `inventory_services.py`. Map item_type values: 'blend'->'blends', 'component'->'components', 'warehouse'->'non_blend', None/all->None
  - **Deliverable**: Service uses correct item source with proper filtering

- [x] **6.3** Remove unused get_all_active_item_codes function
  - **Do**: Delete function from `inventory_selectors.py` and remove from import in `inventory_services.py`
  - **Deliverable**: No dead code

### Testing

- [ ] **6.4** Test: Verify items with zero quantity excluded
- [ ] **6.5** Test: Verify items already in audit groups excluded
- [ ] **6.6** Test: Verify each filter type (all, blends, components, warehouse) returns correct items

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 6. Use get_relevant_ci_item_itemcodes | In Progress | 3/6 |

**Overall**: 3/6 tasks (50%)

---

**Status**: In Progress
