# Uncounted Items Report - Tasks

## Overview

Implementation tasks for the Uncounted Items Report feature. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Data Layer

- [x] **1.1** Add `created_at` field to CountCollectionLink
  - **Do**: Add `created_at = models.DateTimeField(auto_now_add=True, null=True)` to CountCollectionLink model
  - **Deliverable**: Field added in `app/core/models.py`
  - **Verify**: `python manage.py makemigrations` succeeds
  - **Requirement**: US-1 (need date-based countlist filtering)

- [x] **1.2** Run migration (USER ACTION)
  - **Do**: User runs `python manage.py migrate` in the app container
  - **Deliverable**: Column added to `core_countcollectionlink` table
  - **Verify**: Migration completes successfully

- [x] **1.3** Create `get_recently_counted_item_codes()` selector
  - **Do**: Add function to `app/core/selectors/inventory_selectors.py` that:
    1. Queries CountCollectionLinks where `created_at >= cutoff` (or `created_at IS NULL` treated as old)
    2. Extracts all IDs from `count_id_list` JSON arrays
    3. Queries BlendCountRecord and BlendComponentCountRecord by those IDs
    4. Returns set of unique item codes
  - **Deliverable**: Function in `inventory_selectors.py`
  - **Requirement**: US-1

- [x] **1.4** Create `get_all_active_item_codes()` selector
  - **Do**: Add function to `inventory_selectors.py` that returns CiItem queryset filtered by item_type:
    - `None`/`'all'`: All items
    - `'blend'`: itemcode starts with 'BLEND-'
    - `'component'`: itemcode starts with 'CHEM-', 'DYE-', or 'FRAGRANCE-'
    - `'warehouse'`: Everything else
  - **Deliverable**: Function in `inventory_selectors.py`
  - **Requirement**: US-2

- [x] **1.5** Create `get_last_counted_dates()` selector
  - **Do**: Add function to `inventory_selectors.py` that returns `{item_code: last_counted_date}` dict
    - Search both BlendCountRecord and BlendComponentCountRecord
    - Use max `counted_date` for each item
    - Return None for items never counted
  - **Deliverable**: Function in `inventory_selectors.py`
  - **Requirement**: AC (display last counted date)

## Phase 2: Business Logic

- [x] **2.1** Create `build_uncounted_items_display()` service
  - **Do**: Add function to `app/core/services/inventory_services.py` that:
    1. Calls `get_recently_counted_item_codes(days)`
    2. Calls `get_all_active_item_codes(item_type)`
    3. Filters to uncounted items
    4. Applies search filter if provided
    5. Enriches with audit group data (join to AuditGroup)
    6. Enriches with last counted dates
    7. Returns list of dicts with: item_code, item_description, item_type, audit_group, audit_group_id, last_counted_date
  - **Deliverable**: Function in `inventory_services.py`
  - **Verify**: Returns correct uncounted items with all fields populated
  - **Requirement**: US-1, US-2, AC

- [x] **2.2** Create `create_countlist_from_item_codes()` service
  - **Do**: Add function to `inventory_services.py` that:
    1. Determines record_type from item codes (blend vs component)
    2. Creates count records for each item (or gets existing)
    3. Creates CountCollectionLink with those record IDs
    4. Broadcasts WebSocket event
    5. Returns the new CountCollectionLink
  - **Deliverable**: Function in `inventory_services.py`
  - **Verify**: Creates valid countlist, broadcasts update
  - **Requirement**: US-3

## Phase 3: API/Views

- [x] **3.1** Create `display_uncounted_items()` view
  - **Do**: Add view to `app/core/views/web.py` that:
    1. Reads GET params: days (default 3), itemType, search
    2. Calls `build_uncounted_items_display()`
    3. Passes context to template including audit_group_choices for dropdown
  - **Deliverable**: Function in `web.py`
  - **Verify**: Page renders with correct data
  - **Requirement**: US-1, US-2

- [x] **3.2** Create `api_create_countlist_from_items()` API view
  - **Do**: Add view to `app/core/views/api.py` that:
    1. Accepts POST with `item_codes` list
    2. Calls `create_countlist_from_item_codes()`
    3. Returns JSON with collection_id for redirect
  - **Deliverable**: Function in `api.py`
  - **Verify**: Returns valid collection_id
  - **Requirement**: US-3

- [x] **3.3** Add URL routes
  - **Do**: Add to `app/core/urls.py`:
    - `path('uncounted-items/', views.display_uncounted_items, name='uncounted_items')`
    - `path('api/countlist/from-items/', views.api_create_countlist_from_items, name='api_create_countlist_from_items')`
  - **Deliverable**: Routes in `urls.py`
  - **Verify**: URLs resolve correctly

## Phase 4: Frontend

- [x] **4.1** Create template
  - **Do**: Create `app/core/templates/core/inventorycounts/uncounted_items.html` with:
    - Filter bar (days input, item type dropdown, search, reset button)
    - DataTable with columns: checkbox, item code, description, item type, audit group (editable), last counted
    - Action bar with "Create Countlist" button
    - Include datatableprerequisites partial
  - **Deliverable**: Template file
  - **Verify**: Page renders with correct layout
  - **Requirement**: AC (display columns)

- [ ] **4.2** Create JavaScript module
  - **Do**: Create `app/core/static/core/js/pageModules/uncountedItems.js` with:
    - DataTable initialization with export buttons
    - Inline audit group editing (click cell -> dropdown -> AJAX save via existing endpoint)
    - Checkbox selection for bulk operations
    - "Create Countlist" button handler (POST selected items -> redirect to new countlist)
  - **Deliverable**: JS module file
  - **Verify**: All interactive elements work
  - **Requirement**: AC (inline editing), US-3

- [ ] **4.3** Add navigation link
  - **Do**: Add link to inventory counts navbar section
  - **Deliverable**: Link in appropriate navbar partial
  - **Verify**: Navigation works

## Phase 5: Integration

- [ ] **5.1** End-to-end test
  - **Do**: Test complete workflows:
    1. View uncounted items with default filters
    2. Change days parameter, verify list updates
    3. Filter by item type, verify filtering
    4. Search by item code/description
    5. Edit audit group inline, verify save
    6. Select items and create countlist, verify redirect
  - **Verify**: All acceptance criteria from requirements.md pass
  - **Requirement**: All

- [ ] **5.2** Deploy (USER ACTION)
  - **Do**: User deploys to production:
    1. `kpk git pull`
    2. Run migration in production container
    3. `kpk git collectstatic` for static files
  - **Note**: Python changes auto-reload; static files need collectstatic

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Data Layer | Complete | 5/5 |
| 2. Business Logic | Complete | 2/2 |
| 3. API/Views | Complete | 3/3 |
| 4. Frontend | In Progress | 1/3 |
| 5. Integration | Not Started | 0/2 |

**Overall**: 11/15 tasks (73%)

---

**Status**: Draft
