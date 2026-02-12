# Count Status Report Tasks

## Overview

Implementation tasks for count status report. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Data Layer (Selectors)

- [ ] **1.1** Add `get_latest_transactions_for_items()` selector
  - **Do**: In `app/core/selectors/inventory_selectors.py`, add function that takes a list of item_codes and returns a dict mapping each item_code to `{transactioncode, transactiondate, transactionqty}` for its most recent transaction. Use raw SQL with subquery for `MAX(transactiondate)` per item, filtered to codes `('BI', 'BR', 'II', 'IA')`. Pattern after existing `get_latest_transaction_dates()` but include `transactionqty`.
  - **Deliverable**: Working selector function
  - **Requirement**: Latest transaction fields per item

- [ ] **1.2** Add `get_latest_count_details()` selector
  - **Do**: In `app/core/selectors/inventory_selectors.py`, add function that takes a list of item_codes and returns a dict mapping each item_code to `{counted_date, counted, counted_quantity, variance}`. Query both `BlendCountRecord` and `BlendComponentCountRecord` using Django ORM subqueries to get the row with `MAX(counted_date)` per item_code (where `counted=True`). Merge results, preferring the more recent date when an item exists in both tables.
  - **Deliverable**: Working selector function
  - **Requirement**: Latest count fields per item

## Phase 2: Business Logic (Service)

- [ ] **2.1** Add `build_count_status_display()` service
  - **Do**: In `app/core/services/inventory_services.py`, add function that accepts `record_type=None`. Calls `get_ci_items_for_audit_group(record_type)`, extracts item_codes, calls both new selectors, assembles list of dicts with keys: `item_code`, `item_description`, `transaction_code`, `transaction_date`, `transaction_qty`, `counted_date`, `counted`, `counted_quantity`, `variance`. Returns list sorted by item_code.
  - **Deliverable**: Working service function
  - **Requirement**: Combined dataset for report

## Phase 3: Views & Routes

- [ ] **3.1** Add `display_count_status()` view
  - **Do**: In `app/core/views/web.py`, add view function. Reads `recordType` query param (`'blend'`, `'blendcomponent'`, or absent for all). Calls `build_count_status_display(record_type)`. Renders `core/inventorycounts/count_status.html` with context `items` and `record_type`.
  - **Deliverable**: View function
  - **Requirement**: Page renders with data

- [ ] **3.2** Add URL route
  - **Do**: In `app/core/urls.py`, add `path('count-status/', web.display_count_status, name='count-status')` after the count-records route.
  - **Deliverable**: Route accessible at `/core/count-status/`

## Phase 4: Frontend

- [ ] **4.1** Create template
  - **Do**: Create `app/core/templates/core/inventorycounts/count_status.html`. Extends `base.html`. Includes `datatableprerequisites.html`. Filter form with recordType select (All/Blend/Component) + Apply/Reset buttons. Table `#countStatusTable` with columns: Item Code, Description, Last Txn Code, Last Txn Date, Last Txn Qty, Last Counted Date, Counted, Counted Qty, Variance. Use `{% empty %}` for no-data message. Display "--" for null values.
  - **Deliverable**: Template file
  - **Requirement**: All display acceptance criteria

- [ ] **4.2** Create JavaScript module
  - **Do**: Create `app/core/static/core/js/pageModules/countStatus.js`. Initialize DataTable on `#countStatusTable` with sorting, search, and export buttons (CSV/Excel). No additional event handlers needed.
  - **Deliverable**: JS module file
  - **Requirement**: DataTables integration

- [ ] **4.3** Add navigation link
  - **Do**: In `app/templates/navbars/office-navbar-items.html`, add "Count Status Report" link in the Inventory dropdown after "Uncounted Items Report", pointing to `/core/count-status/`.
  - **Deliverable**: Nav link visible in Inventory menu

## Phase 5: Manual Testing

- [ ] **5.1** Verify end-to-end
  - **Do**: Test the following:
    - Navigate to `http://localhost:8000/core/count-status/` - table loads with all audit-group items
    - Verify transaction columns populate for items with history, show "--" for items without
    - Verify count columns populate correctly, show "--" for items without counts
    - Test `?recordType=blend` filter shows only BLEND items
    - Test `?recordType=blendcomponent` filter shows only CHEM/DYE/FRAGRANCE items
    - Verify DataTable sorting, search, and export buttons work
    - Verify nav link appears in Inventory dropdown
  - **Requirement**: All acceptance criteria

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Data Layer | Not Started | 0/2 |
| 2. Business Logic | Not Started | 0/1 |
| 3. Views & Routes | Not Started | 0/2 |
| 4. Frontend | Not Started | 0/3 |
| 5. Manual Testing | Not Started | 0/1 |

**Overall**: 0/9 tasks (0%)

---

**Status**: Draft
