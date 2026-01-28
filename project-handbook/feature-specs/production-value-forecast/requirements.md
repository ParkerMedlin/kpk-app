# Production Value Forecast Report Requirements

## Problem Statement

Accounting needs to predict production flow on a weekly basis to forecast cash flow and revenue. Currently, there's no automated way to translate the production schedule into projected dollar values based on matching sales orders. This report will project revenue from scheduled production runs over an adjustable time horizon (default 40 work hours).

## User Stories

### Accounting Manager
- **As an** accounting manager, **I want to** see projected revenue from the next 40 hours of production, **so that** I can forecast weekly cash flow
- **As an** accounting manager, **I want to** adjust the time horizon (e.g., 20 hours, 80 hours), **so that** I can model different scenarios
- **As an** accounting manager, **I want to** see revenue breakdown by production line, **so that** I understand which lines drive the most value
- **As an** accounting manager, **I want to** download the forecast as CSV, **so that** I can integrate it into financial reports

### Production Manager
- **As a** production manager, **I want to** see which production runs match to sales orders, **so that** I can prioritize high-value orders
- **As a** production manager, **I want to** see aggregate and per-line summaries, **so that** I can balance capacity across lines

## Acceptance Criteria

### Core Functionality
- **WHEN** the user loads the report, **THEN** the system **SHALL** default to a 40-hour rolling forecast from the current time
- **WHEN** the user adjusts the "Next Hours" input, **THEN** the system **SHALL** recalculate the forecast for that time window
- **WHEN** calculating the forecast, **THEN** the system **SHALL** match `prodmerge_run_data.po_number` to `so_salesorderdetail.salesorderno`
- **WHEN** a production run matches a sales order, **THEN** the system **SHALL** calculate projected value as `item_run_qty × unitprice`
- **WHEN** a production run does NOT match a sales order, **THEN** the system **SHALL** skip that run (exclude from totals)
- **WHEN** displaying results, **THEN** the system **SHALL** show total projected value, number of runs, and value by production line
- **WHEN** displaying the detail table, **THEN** the system **SHALL** group rows by production line with collapsible sections

### Time Calculations
- **WHEN** filtering production runs, **THEN** the system **SHALL** use `start_time` (in hours) to determine if the run falls within the forecast window
- **WHEN** calculating cumulative time, **THEN** the system **SHALL** treat `run_time` as hours (e.g., 0.2 hours = 12 minutes)

### User Experience
- **WHEN** the user clicks "Analyze Production Schedule", **THEN** the UI **SHALL** disable the button and show "Analyzing..." text
- **WHEN** the analysis completes, **THEN** the UI **SHALL** display summary KPIs and populate the detail table
- **WHEN** the user clicks "Download CSV", **THEN** the system **SHALL** export all forecast data including line, item, qty, price, and extended value
- **WHEN** the user clicks a production line header, **THEN** the system **SHALL** expand/collapse that line's detail rows

### Error Handling
- **WHEN** no production runs fall within the forecast window, **THEN** the system **SHALL** display "No production scheduled in the next X hours"
- **WHEN** the API request fails, **THEN** the UI **SHALL** show a clear error message and re-enable the Analyze button

## Scope

### In Scope
- Rolling time horizon forecast (default 40 hours, user-adjustable)
- Match production runs to sales orders via `po_number`
- Calculate projected revenue (qty × price)
- Summary KPIs: total value, run count, value by line
- Detail table with production runs grouped by line
- CSV download of forecast data
- Similar UI/UX pattern to existing `sales_order_vs_bom_cost.html` report

### Out of Scope
- Historical production value tracking (this is forward-looking only)
- Cost-based margin analysis (revenue only, not profitability)
- Multi-week calendar view (rolling hours only, not calendar weeks)
- Integration with accounting software export formats (CSV is sufficient)
- Production schedule editing (read-only view)
- Work calendar integration (assumes continuous work hours, doesn't skip nights/weekends)

## Dependencies

- **Database tables**:
  - `prodmerge_run_data` (production schedule with `start_time`, `run_time`, `po_number`, `item_run_qty`, `prod_line`)
  - `so_salesorderdetail` (sales orders with `salesorderno`, `unitprice`, `itemcode`)

- **Existing patterns**:
  - Report page structure similar to `sales_order_vs_bom_cost.html`
  - API endpoint pattern in `core/views/api.py`
  - Bootstrap 5 + jQuery frontend

- **ETL workers**:
  - Assumes `prodmerge_run_data` table is kept current by existing data_sync ETL processes

---

**Status**: Draft
