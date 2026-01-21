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

**For date columns:** Add `data-order` attribute for proper sorting:
```html
<td data-order="{{ item.date|date:'Y-m-d' }}">{{ item.date }}</td>
```

## Questions to Ask User

1. Which template needs DataTable functionality?
2. Does it already have a table with an id, or does one need to be added?
3. Should paging be enabled? (default: no for <100 rows)
4. Which export buttons? (default: copy, csv, excel, print)
5. Any columns that should NOT be sortable?
6. Any columns with dates that need `data-order` attributes?

## Implementation Steps

1. Read the target template
2. Verify table has an `id` attribute
3. Check if datatableprerequisites partial or block scripts exists
4. Check if pageModule JS file exists at expected path
5. Present plan to user with specific changes needed
6. After approval, make edits:
   - Add prerequisites (partial or block scripts)
   - Create/update pageModule JS
   - Link pageModule in template
   - Add `data-order` attributes to date columns if needed

## Reference Files

- Partial: `app/core/templates/core/partials/datatableprerequisites.html`
- Example pageModules:
  - `app/core/static/core/js/pageModules/startronReport.js` (basic)
  - `app/core/static/core/js/pageModules/upcomingRunsReport.js` (with columnDefs)
  - `app/core/static/core/js/pageModules/inventoryCountsReport.js` (with date ordering)
