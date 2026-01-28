# Production Value Forecast Report Design

## Overview

Read-only report page. Query `prodmerge_run_data` filtered by rolling time window, join to `so_salesorderdetail` on `po_number = salesorderno`, calculate revenue projections. Pattern matches `sales_order_vs_bom_cost.html` structure.

## Affected Components

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/templates/core/reports/production_value_forecast.html` | Report UI with time horizon input, KPIs, grouped table |
| `app/core/views/api.py` | Add `production_value_forecast_api()` function |
| `app/core/views/web.py` | Add `production_value_forecast()` view |

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/urls.py` | Add 2 routes: web view + API endpoint |

## Data Model

No new models. Uses existing unmanaged tables:
- `prodmerge_run_data` (ProductionLineRun model) - production schedule
- `so_salesorderdetail` (SoSalesOrderDetail model) - sales orders

## URL Routes

```python
# In app/core/urls.py
path('reports/production-value-forecast/', views.production_value_forecast, name='production_value_forecast'),
path('api/production-value-forecast/', views.production_value_forecast_api, name='api_production_value_forecast'),
```

## Layer Design

### API View (in views/api.py)
```python
@require_http_methods(["GET"])
def production_value_forecast_api(request):
    """
    GET params: next_hours (default 40)
    Returns JSON: {
        'summary': {totalValue, runCount, lineBreakdown},
        'runs': [{po_number, item_code, prod_line, start_time, run_time, qty, unitprice, extendedValue, salesOrderNo}],
        'elapsedMs': timing
    }
    """
    # Query logic inline (no selector needed for simple join)
```

### Query Logic
```python
# Get current time as hours since epoch reference
# Filter: ProductionLineRun.objects.filter(start_time__lt=current + next_hours)
# Join: SoSalesOrderDetail.objects.filter(salesorderno=po_number)
# Calculate: item_run_qty × unitprice
# Group by: prod_line for summary stats
```

### Web View (in views/web.py)
```python
@login_required
def production_value_forecast(request):
    """Renders template with empty state"""
    return render(request, 'core/reports/production_value_forecast.html')
```

## Frontend

### Template Structure
- Extends `base.html`
- Control panel: time horizon input (default 40), Analyze button, Download CSV button
- Summary KPIs: Total Value, Run Count, Value by Line
- Table: grouped by `prod_line`, collapsible sections
- Columns: PO #, Item, Description, Qty, Unit Price, Extended Value, SO #

### JavaScript (inline in template)
- Click handler: Analyze button → fetch API → render results
- Click handler: Download CSV → generate from cached data
- Click handler: Line headers → toggle collapse
- Functions: `formatCurrency()`, `renderTable()`, `renderSummary()`

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| No runs in time window | Show "No production scheduled in the next X hours" placeholder |
| API fetch failure | Alert message, re-enable Analyze button |
| Unmatched PO number | Skip row (exclude from totals) |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| 40-hour default, adjustable | Input field default=40, passed as GET param |
| Match po_number to salesorderno | Query joins ProductionLineRun + SoSalesOrderDetail |
| Calculate qty × price | `item_run_qty × unitprice` in query/loop |
| Show total + per-line breakdown | Summary object groups by prod_line |
| Collapsible line sections | CSS + click handlers on line headers |
| CSV download | Client-side CSV generation from cached results |

---

**Status**: Draft
