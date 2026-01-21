# Flush Tote Tracking Design

## Overview

Add a flush tote tracking workflow so lab technicians can record pH checks, corrective actions, and approvals. Implement a `FlushToteReading` table, API, and two web pages: a single-instance entry form for lab techs and an admin table view for staff to review/edit historical records.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/models.py` | Add `FlushToteReading` model with fields/choices and validation helpers. |
| `app/core/selectors/__init__.py` | Export new selector functions. |
| `app/core/services/__init__.py` | Export new service functions. |
| `app/core/views/web.py` | Web views for entry form and admin records page. |
| `app/core/views/api.py` | JSON endpoints for list/create/update flush totes. |
| `app/core/urls.py` | Routes for web and API endpoints. |
| `app/templates/navbars/admin-navbar-items.html` | Nav link for admin records page. |

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/services/flush_tote_services.py` | Business logic for create/update, status transitions, and validation. |
| `app/core/selectors/flush_tote_selectors.py` | Data access for list/detail and option lookups. |
| `app/core/templates/core/flush_totes.html` | Admin table view with inline editing (staff only). |
| `app/core/templates/core/flush_tote_entry.html` | Single-instance entry form for lab technicians. |
| `app/core/static/core/js/pageModules/FlushTotes.js` | Front-end logic for admin table: inline edits, API calls. |
| `app/core/static/core/js/pageModules/FlushToteEntry.js` | Front-end logic for entry form: validation, submission. |

## Data Model

### New Models
```python
class FlushToteReading(models.Model):
    """Tracks testing/approval of a production flush tote."""
    STATUS_PENDING = "pending"
    STATUS_NEEDS_ACTION = "needs_action"
    STATUS_APPROVED = "approved"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_NEEDS_ACTION, "Needs Action"),
        (STATUS_APPROVED, "Approved"),
    ]

    PRODUCTION_LINE_CHOICES = [
        ("JB Line", "JB Line"),
        ("INLINE", "INLINE"),
        ("PD Line", "PD Line"),
    ]

    date = models.DateTimeField(auto_now_add=True)
    production_line = models.CharField(max_length=50, choices=PRODUCTION_LINE_CHOICES)
    flush_type = models.CharField(max_length=255)  # options fed from BlendContainerClassification.flush_tote uniques
    initial_pH = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    action_required = models.TextField(blank=True, default="")
    final_pH = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    approval_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    lab_technician = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="flush_totes_tested")
    line_personnel = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="flush_totes_created")

    class Meta:
        db_table = "core_flush_tote_reading"
        ordering = ("-date",)
```

Validation rules (service-level):
- pH values must be numeric; range for approval is 5.1–10.9 inclusive.
- If initial pH outside range, set status to `needs_action` until action text + compliant final pH are provided.
- Approve only when final pH exists and is in range; set status `approved`.

Option sourcing:
- `flush_type` choices populated at runtime from distinct `BlendContainerClassification.flush_tote` values (non-null, non-empty).

## URL Routes

```python
# app/core/urls.py
path("flush-tote-entry/", views.flush_tote_entry_view, name="flush_tote_entry"),
path("flush-tote-records/", views.flush_tote_records_view, name="flush_tote_records"),
path("api/flush-totes/", views.flush_tote_list_api, name="flush_tote_list_api"),
path("api/flush-totes/<int:pk>/", views.flush_tote_detail_api, name="flush_tote_detail_api"),
```

## Layer Design

### Selectors (data retrieval)
```python
def list_flush_totes(limit=200) -> QuerySet:
    """Recent totes ordered newest-first for table view."""

def get_flush_tote(pk: int) -> FlushToteReading:
    """Fetch single tote or raise DoesNotExist."""

def get_flush_type_options() -> List[str]:
    """Distinct non-null `flush_tote` values from BlendContainerClassification."""
```

### Services (business logic)
```python
def create_flush_tote_reading(data, user) -> FlushToteReading:
    """
    - set lab_technician=user
    - compute approval_status based on pH values
    - default status pending if no pH, needs_action if out of range, approved if in range
    """

def update_flush_tote_reading(tote: FlushToteReading, data, user) -> FlushToteReading:
    """
    - update fields from data
    - recompute approval_status based on pH values
    - set lab_technician=user if updating pH fields
    """
```

### Views
```python
def flush_tote_entry_view(request):
    """Render single-instance entry form for lab technicians."""

def flush_tote_records_view(request):
    """Render admin table with all records and inline editing (staff only)."""

@require_http_methods(["GET", "POST"])
def flush_tote_list_api(request):
    """GET: list recent totes. POST: create new tote."""

@require_http_methods(["PATCH", "PUT"])
def flush_tote_detail_api(request, pk):
    """Update fields for a tote."""
```

Access control:
- Entry form: lab technician group or staff
- Records page: staff only
- API: lab technician group or staff

## Frontend

### Entry Form (flush_tote_entry.html)
```
flush_tote_entry.html
├── extends base.html
├── single form with all fields:
│   - production_line (select)
│   - flush_type (select)
│   - line_personnel_name (text input - lab tech enters who brought the tote)
│   - initial_pH (number input)
│   - action_required (textarea, shown/required when pH out of range)
│   - final_pH (number input)
├── client-side validation for pH range with visual feedback
├── submit creates record and shows success/reset for next entry
└── loads static/core/js/pageModules/FlushToteEntry.js
```

### Admin Records (flush_totes.html)
```
flush_totes.html
├── extends base.html
├── search/filter controls
├── table of totes with status badges
├── inline row edit controls (no modal) similar to container-classification page
└── loads static/core/js/pageModules/FlushTotes.js
```

### JavaScript
```javascript
// pageModules/FlushToteEntry.js
// - form validation: pH range check, required fields
// - show/hide action_required field based on pH value
// - async POST to api/flush-totes/
// - success: show toast, reset form for next entry

// pageModules/FlushTotes.js (admin table)
// - inline row edit UX patterned after containerClassificationRecords.js
// - search/filter functionality
// - async PATCH to api/flush-totes/<id>/
```

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Missing required fields or non-numeric pH | Return 400 with field errors; show inline messages. |
| Initial pH out of range | Set status `needs_action`, require action text before final pH approval. |
| Final pH still out of range | Keep status `needs_action`; block approval; toast message. |
| Unauthorized access | Return 403; redirect to login or show permission error. |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| Auto-fill date/time, require line + flush type + line personnel | `create_flush_tote_reading` service, entry form validation |
| Initial pH check + action if outside 5.1–10.9 | Service validation, UI feedback |
| Final pH within range before approval | Service approval_status logic |
| Single-session entry for lab techs | Entry form page design |
| Admin review/edit capability | Records page with inline editing |
| Flush type options from BlendContainerClassification | `get_flush_type_options` selector feeding form select |

---

**Status**: Approved (Revised)
