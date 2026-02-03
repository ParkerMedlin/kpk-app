# Audit Group Inline Edit — Troubleshooting

## Problem Summary

**Reported symptom:** Submitting an inline edit on the audit group page returns a 403 Forbidden — "CSRF token missing or incorrect" at `/core/api/audit-group/1314/`. A secondary console error appears: `buttonObjects.js:323 Cannot read properties of null (reading 'addEventListener')`.

**Expected behavior:** Clicking Save on an inline-edited row should POST the change and update the row.

**Conditions:** Reproduces every time, on every row.

---

## Investigation

### Code Path Traced

```
Edit button click → enterEditMode() → Save button click → handleSave()
  → persistRow() → fetch POST to /core/api/audit-group/<id>/
  → Django CSRF middleware rejects (no token) → 403 Forbidden
```

### Findings

**Issue 1 — CSRF token not available on the page**

The `persistRow()` function in `itemsByAuditGroup.js` (line 113) correctly sends `X-CSRFToken: getCsrfToken()` in the fetch headers. The `getCsrfToken()` function (lines 8-19) tries two sources:

1. A hidden input: `document.querySelector('input[name="csrfmiddlewaretoken"]')`
2. The `csrftoken` cookie

Neither source exists on this page. The template `itemsbyauditgroup.html` has no `{% csrf_token %}` tag, and `base.html` doesn't include one either. Django only sets the `csrftoken` cookie when a template renders `{% csrf_token %}`, so the cookie fallback also returns empty string.

The working reference implementation — `containerclassificationrecords.html` — solves this with a hidden form at line 21-23:

```html
<form id="container-classification-csrf" style="display:none;" aria-hidden="true">
    {% csrf_token %}
</form>
```

This pattern makes the token available both as a DOM input and triggers Django to set the cookie.

**Issue 2 — BlendComponentFilterButton instantiated with null**

In `itemsByAuditGroup.js` line 137:

```js
new BlendComponentFilterButton(document.getElementById('upcomingRunsFilterCheckbox'));
```

The `#upcomingRunsFilterCheckbox` element only exists when `record_type == 'blendcomponent'` (template line 24). For all other record types, `getElementById` returns `null`, which is passed to `BlendComponentFilterButton`, causing the error at `buttonObjects.js:323` when it tries to call `button.addEventListener('click', ...)` on `null`.

The constructor does have a try/catch (lines 320-324) so the error is caught and logged — it doesn't break the page, but it's noisy.

### Code Locations

| File | Lines | Role |
|------|-------|------|
| `app/core/static/core/js/pageModules/itemsByAuditGroup.js` | 8-19 | `getCsrfToken()` — looks for token in DOM input then cookie |
| `app/core/static/core/js/pageModules/itemsByAuditGroup.js` | 113 | `persistRow()` — sends `X-CSRFToken` header with empty string |
| `app/core/static/core/js/pageModules/itemsByAuditGroup.js` | 137 | `BlendComponentFilterButton` instantiated with potentially null element |
| `app/core/templates/core/inventorycounts/itemsbyauditgroup.html` | 1-98 | Template — no `{% csrf_token %}` anywhere |
| `app/core/templates/core/lotnumbers/containerclassificationrecords.html` | 21-23 | Reference pattern — hidden form with `{% csrf_token %}` |
| `app/core/static/core/js/objects/buttonObjects.js` | 318-324 | `BlendComponentFilterButton` constructor — calls `addEventListener` on the passed element |
| `app/core/services/inventory_services.py` | 282-302 | `update_audit_group_api` — `@require_POST`, no `@csrf_exempt` (correct) |

---

## Fix Tasks

### Task 1: Add hidden CSRF form to itemsbyauditgroup.html

- **File**: `app/core/templates/core/inventorycounts/itemsbyauditgroup.html`
- **Function/Section**: `{% block content %}`, right after the opening `<div class='text-center'>` (before line 20)
- **Do**: Add a hidden form containing `{% csrf_token %}`, following the same pattern as `containerclassificationrecords.html` line 21-23:
  ```html
  <form style="display:none;" aria-hidden="true">
      {% csrf_token %}
  </form>
  ```
- **Why**: This renders a hidden `<input name="csrfmiddlewaretoken">` into the DOM, which `getCsrfToken()` will find on its first lookup. It also causes Django to set the `csrftoken` cookie as a fallback.
- **Watch out**: No side effects. The form is inert (no action, no submit handler).

### Task 2: Guard BlendComponentFilterButton instantiation against null

- **File**: `app/core/static/core/js/pageModules/itemsByAuditGroup.js`
- **Function/Section**: `$(document).ready()` callback, line 137
- **Do**: Wrap the instantiation in a null check. Change:
  ```js
  new BlendComponentFilterButton(document.getElementById('upcomingRunsFilterCheckbox'));
  ```
  to:
  ```js
  const upcomingRunsFilter = document.getElementById('upcomingRunsFilterCheckbox');
  if (upcomingRunsFilter) new BlendComponentFilterButton(upcomingRunsFilter);
  ```
- **Why**: The checkbox only exists for `blendcomponent` record type. For other record types, passing `null` to the constructor triggers a caught-but-noisy console error.
- **Watch out**: No functional change — the constructor's try/catch already swallows the error. This just eliminates the console noise.

---

## Verification

After all tasks are complete, verify:

- [ ] Navigate to the audit group page for any record type (e.g., `http://localhost:8000/core/items-by-audit-group/?recordType=blendcomponent`)
- [ ] Click the edit pencil on any row, change the audit group or counting unit, click Save — row should update without error
- [ ] Check browser console — no CSRF errors, no `addEventListener` null errors
- [ ] Test with a non-blendcomponent record type to confirm the BlendComponentFilterButton guard works
- [ ] Test creating a new audit group record (row with no `data-id`) if that flow exists

---

**Status**: Draft
