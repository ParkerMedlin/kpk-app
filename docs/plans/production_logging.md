# Production Logging Project — Scratchpad

## Goal
Capture production run data (currently lost when schedule rows are deleted) into a kpk app database table, enabling efficiency/capacity tracking.

## Current Workflow
1. Sales orders imported from Sage → production schedule Excel (`.xlsb`)
2. Schedule is organized by **line** (each Excel tab = a line, e.g., "Horix Line", "LET/KIT")
3. When production completes, paper forms come back:
   - **Production Ticket**: work order, product #, description, cases produced, line, employees
   - **Production Worksheet**: start/stop times, # employees, total run time, holdover, scrap, downtime log, total production
4. Scheduler runs **Logger macro** → logs row to `Production Schedule Log.xlsb`, then deletes the schedule row
5. Production accounting enters qty into Sage via BM_production_entry

## Schedule Row Structure
Two leading flag columns (A, B) then:
| Col | Header     | Example Data                    |
|-----|------------|---------------------------------|
| A   | (flag)     | B (blended)                    |
| B   | (flag)     | P (carton printed)              |
| C   | P/N        | 088308                          |
| D   | PO #       | 246318                          |
| E   | Product    | Screen Cleaner/Protector        |
| F   | Blend      | 607534 pump sprayer             |
| G   | Case/Size  | 88300.B  /  6-8oz               |
| H   | Qty        | 100                             |
| I   | Bottle     | White oval pvc 8oz              |
| J   | Cap        | 607534 pump                     |
| K   | Runtime    | 0.28                            |
| L   | Carton     | 604096                          |
| M   | ▲          |(blindsticker required) yes or no|
| N   | Pallet     | 48x40                           |
| O   | PO Due     | 2/1                             |

*Note: column mapping is approximate — need to verify exact positions.*

## Logger Macro — What It Does Today
1. User selects the **Qty cell** in the schedule
2. InputBox prompts for **produced qty** (defaults to scheduled qty)
3. Captures entire source row values (cols A through Q+)
4. Opens `Production Schedule Log.xlsb`
5. Inserts new row at TOP of either "Horix" or "Lines" sheet (reverse-chron)
6. Writes: all schedule columns + produced qty + run date (Now) + line name (sheet tab name)
7. Saves log, optionally closes it
8. For Horix: opens relevant shipping workbook (Splash/West/SB/Mercury)
9. Deletes source row (or reduces qty if partial run on non-Horix)

### What the macro captures today
- All schedule fields (product, PO, blend, bottle, cap, runtime, etc.)
- Produced qty (user input)
- Run date (timestamp of macro execution)
- Line name (from sheet tab)
- Difference qty (scheduled - produced, for partials)

### What the macro does NOT capture (from the paper production worksheet)
- Start time / end time (multiple pairs possible)
- Number of employees
- Total run time (calculated from times)
- Beginning holdover
- Ending holdover
- Downtime entries (minutes, reason, # employees present)
- Scrap
- Comments

## The Gap
The production worksheet has all the efficiency data (timing, labor, downtime, scrap) but it stays on paper. The Logger macro only captures schedule data + produced qty.

## Proposed Pipeline
1. **New Django model** (`core_productionhistory`) — stores schedule data + production worksheet fields
2. **New DRF API endpoint** — `POST /api/production-history/` — receives production data
3. **Extend Logger macro** — after capturing produced qty, also prompt for worksheet fields, then POST to kpk app endpoint
4. Continue logging to Excel as fallback/legacy (or phase out later)

## Decisions
- **V1 fields from macro (user-input):** total runtime (minutes), # employees, produced qty, notes
- **V1 fields from schedule (auto-captured):** all schedule row data (P/N, PO#, product, blend, case/size, bottle, cap, runtime estimate, carton, pallet, PO due, line name)
- **No start/end times** — just total runtime in minutes
- **No form numbers** — skip ticket/worksheet numbers to reduce friction
- **Auth:** None (LAN-only, no auth required)
- **Downtime, scrap, holdover:** Deferred to v2

## Resolved
- Horix shipping workbook interaction stays as-is, fires AFTER the production data POST (same as other lines)

## Implementation

### 1. Django Model — `core_productionhistory`
**File:** `app/core/models.py`

Fields:
- `id` — AutoField (default)
- `item_code` — CharField (P/N from schedule)
- `po_number` — CharField (PO # from schedule)
- `product_description` — CharField (Product from schedule)
- `blend` — CharField (Blend from schedule, blank ok)
- `case_size` — CharField (Case/Size from schedule)
- `scheduled_qty` — IntegerField (Qty from schedule)
- `produced_qty` — IntegerField (user input)
- `bottle` — CharField (Bottle from schedule)
- `cap` — CharField (Cap from schedule)
- `runtime_estimate` — DecimalField (Runtime from schedule, the pre-calculated estimate)
- `carton` — CharField (Carton from schedule)
- `pallet` — CharField (Pallet from schedule)
- `po_due_date` — CharField (PO Due from schedule, kept as string since format varies)
- `line_name` — CharField (sheet tab name)
- `run_date` — DateField (date of production run)
- `runtime_minutes` — IntegerField (actual total runtime from paper worksheet)
- `num_employees` — IntegerField
- `notes` — TextField (blank ok)
- `created_at` — DateTimeField (auto_now_add)

Meta: `db_table = 'core_productionhistory'`, `ordering = ['-run_date', '-created_at']`

### 2. API Endpoint — `POST /api/production-history/create/`
**Files:** `app/core/views/api.py`, `app/core/urls.py`

- `@csrf_exempt` + `@require_POST` (no login_required — LAN only, macro has no session)
- Parse JSON payload
- Validate required fields: item_code, po_number, produced_qty, line_name, run_date
- Call service function → create record → return JSON response
- Service function in `app/core/services/` (new file or existing)

### 3. Service Layer
**File:** `app/core/services/production_history_services.py` (new)

- `create_production_history(**kwargs) -> Dict` — creates model instance, returns serialized dict
- `_serialize_production_history(record) -> Dict` — model-to-dict helper

### 4. VBA Macro Changes
**File:** Production schedule `.xlsb` macro module

New flow (inserted between produced qty prompt and Excel log write):
1. After existing produced qty input, add InputBox prompts for: runtime_minutes, num_employees, notes
2. Build JSON payload from schedule row data + user inputs
3. POST to `http://192.168.178.169/core/api/production-history/create/`
4. Log success/failure to Immediate window (non-blocking — don't halt the macro if POST fails)
5. Continue with existing Excel log + delete flow unchanged

### Execution Order
1. Model + migration
2. Service layer
3. API view + URL route
4. Test endpoint with curl
5. VBA macro update
