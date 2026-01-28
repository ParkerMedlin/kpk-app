---
name: plan-datatable
description: Plans DataTable implementation for a page. Ensures datatableprerequisites partial is included, creates pageModule JS file if needed, and determines feature configuration (export buttons, column ordering, etc).
---

# Plan DataTable Implementation

A structured approach for adding DataTable functionality to an HTML template.

## Checklist

### 1. Identify the Target Table

- Read the template file to find the `<table>` element
- Note the table's `id` attribute (create one if missing)
- Document columns and their data types (text, numbers, dates, etc.)

### 2. Include DataTable Prerequisites

```html
{% include 'core/partials/datatableprerequisites.html' %}
```

### 3. Create or Update PageModule JS File

Location: `app/core/static/core/js/pageModules/{pageName}.js`

Naming convention: Match the template name in camelCase (e.g., `startronreport.html` → `startronReport.js`)

**Basic template:**
```javascript
$(document).ready(function(){
    $('#tableId').DataTable({
        paging: false,
        dom: 'Bfrtip',
        buttons: ['copy', 'csv', 'excel', 'print']
    });
});
```

### 4. Link the PageModule

Add to template (use `{% block belowdeckscripts %}` if available):
```html
<script type="module" src="{% static 'core/js/pageModules/{pageName}.js' %}"></script>
```

**Important**: this needs to go AFTER `{% include 'core/partials/datatableprerequisites.html' %}` 

### 5. Determine Feature Configuration

Ask user about these options:

| Feature | Options | Default |
|---------|---------|---------|
| **Paging** | `true` / `false` | `false` for small tables |
| **Export buttons** | `['copy', 'csv', 'excel', 'print']` | All four |
| **Column ordering** | `columnDefs: [{ orderable: false, targets: [n] }]` | All orderable |
| **Default sort** | `order: [[colIndex, 'asc']]` | First column |
| **Search** | Built into dom `f` | Enabled |

### 6. Add data-order to Date Columns

**REQUIRED for all date columns.** DataTables sorts alphabetically by default, so dates like "Jan 15, 2025" won't sort correctly. Add the `data-order` attribute with ISO format (`Y-m-d`) to enable proper chronological sorting.

**Pattern:**
```html
<td data-order="{{ item.date|date:'Y-m-d' }}">{{ item.date|date:'M j, Y' }}</td>
```

**Implementation steps for date columns:**
1. Identify all `<td>` cells that display date values in the template
2. Add `data-order="{{ variable|date:'Y-m-d' }}"` to each date `<td>`
3. The display format inside the cell can remain whatever the user prefers
4. The `data-order` value must use `Y-m-d` format (e.g., `2025-01-15`)

**Examples:**
```html
<!-- Before -->
<td>{{ record.created_at|date:'M j, Y' }}</td>
<td>{{ shipment.ship_date }}</td>

<!-- After -->
<td data-order="{{ record.created_at|date:'Y-m-d' }}">{{ record.created_at|date:'M j, Y' }}</td>
<td data-order="{{ shipment.ship_date|date:'Y-m-d' }}">{{ shipment.ship_date }}</td>
```

## Questions to Ask User

1. Which template needs DataTable functionality?
2. Does it already have a table with an id, or does one need to be added?
3. Should paging be enabled? (default: no for <100 rows)
4. Which export buttons? (default: copy, csv, excel, print)
5. Any columns that should NOT be sortable?
6. Which columns contain dates? (these will require `data-order` attributes)

## Implementation Steps

1. Read the target template
2. Verify table has an `id` attribute
3. Check if datatableprerequisites partial or block scripts exists
4. Check if pageModule JS file exists at expected path
5. **Identify all date columns** in the table and note which `<td>` cells need `data-order` attributes
6. Present plan to user with specific changes needed
7. After approval, make edits:
   - Add prerequisites (partial or block scripts)
   - Create/update pageModule JS
   - Link pageModule in template
   - **Add `data-order="{{ var|date:'Y-m-d' }}"` to every date column's `<td>` element**

## Reference Files

- Partial: `app/core/templates/core/partials/datatableprerequisites.html`
- Example pageModules:
  - `app/core/static/core/js/pageModules/startronReport.js` (basic)
  - `app/core/static/core/js/pageModules/upcomingRunsReport.js` (with columnDefs)
  - `app/core/static/core/js/pageModules/inventoryCountsReport.js` (with date ordering)
