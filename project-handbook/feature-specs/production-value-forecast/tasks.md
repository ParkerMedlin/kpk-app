# Production Value Forecast Report Tasks

## Overview

Implementation tasks for production value forecast report. No models/migrations needed (uses existing tables).

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Backend

- [x] **1.1** Add API endpoint
  - **Do**: Create `production_value_forecast_api()` in `app/core/views/api.py`
  - **Logic**: Query `ProductionLineRun` filtered by `start_time`, join to `SoSalesOrderDetail` on `po_number`, calculate revenue
  - **Returns**: JSON with summary stats + run details
  - **Requirement**: Core functionality - time window filtering, PO matching, revenue calculation

- [x] **1.2** Add web view
  - **Do**: Create `production_value_forecast()` in `app/core/views/web.py`
  - **Do**: Simple render function, no context needed
  - **Requirement**: User access to report page

- [x] **1.3** Add URL routes
  - **Do**: Add 2 paths to `app/core/urls.py`
  - **Paths**: `/reports/production-value-forecast/` and `/api/production-value-forecast/`
  - **Verify**: Routes resolve correctly

## Phase 2: Frontend

- [x] **2.1** Create template
  - **Do**: Create `app/core/templates/core/reports/production_value_forecast.html`
  - **Structure**: Control panel (time input, analyze button), KPI summary strip, grouped table, modal (optional)
  - **Style**: Match `sales_order_vs_bom_cost.html` pattern
  - **Requirement**: All UI acceptance criteria

- [x] **2.2** Add inline JavaScript
  - **Do**: Add JS to template for API calls, table rendering, CSV download
  - **Functions**: `runAnalysis()`, `renderTable()`, `renderSummary()`, `downloadCsv()`
  - **Event handlers**: Analyze button, CSV button, line group toggles
  - **Requirement**: User interaction, data display

## Phase 3: Integration

- [ ] **3.1** End-to-end test
  - **Do**: Load page, adjust time horizon, run analysis, verify results, download CSV
  - **Verify**: All acceptance criteria pass
  - **Requirement**: All

- [x] **3.2** Add navigation link
  - **Do**: Add to Quick Find menu and Misc Reports dropdown
  - **Deliverable**: Accessible via Ctrl+K quick find and Reports page dropdown
  - **Completed**: Added to `_MISC_REPORT_DEFINITIONS` in reports_services.py

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Backend | Complete | 3/3 |
| 2. Frontend | Complete | 2/2 |
| 3. Integration | Ready for Testing | 1/2 |

**Overall**: 6/7 tasks (86%)

---

**Status**: Implementation Complete - Ready for End-to-End Testing

## Access Points

Users can access the report via:
1. **Quick Find**: Press Ctrl/Cmd + K, search "production value forecast"
2. **Reports Page**: Navigate to `/core/reports/`, select "Production Value Forecast" from dropdown, click "Generate Report"
3. **Direct URL**: Navigate to `/core/production-value-forecast/`
