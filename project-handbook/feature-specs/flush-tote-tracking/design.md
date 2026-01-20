# Flush Tote Tracking Design

## Overview

Add a flush tote tracking workflow so line personnel and lab technicians can record pH checks, corrective actions, and approvals with real-time visibility. Implement a new `FlushToteReading` table, API, web page, and WebSocket channel so both roles see updates instantly as totes move from creation to approval for discharge.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/models.py` | Add `FlushToteReading` model with fields/choices and validation helpers. |
| `app/core/forms.py` | Form(s) for create/update with role-aware field enablement and pH validation. |
| `app/core/selectors/__init__.py` | Export new selector functions. |
| `app/core/services/__init__.py` | Export new service functions. |
| `app/core/views/web.py` | New web view to render flush tote page with context options. |
| `app/core/views/api.py` | JSON endpoints for list/create/update flush totes. |
| `app/core/urls.py` | Routes for web and API endpoints. |
| `app/websockets/routing.py` | Include flush tote WebSocket routes. |
| `app/core/static/core/js/pageModules/base.js` | If needed, register new page module hook. |
| `app/core/templates/base.html` | Ensure static/js include for new page module (only if global loader needed). |

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/services/flush_tote_services.py` | Business logic for create/update, status transitions, and validation. |
| `app/core/selectors/flush_tote_selectors.py` | Data access for list/detail and option lookups. |
| `app/core/templates/core/flush_totes.html` | Page UI for line personnel + lab tech workflows. |
| `app/core/static/core/js/pageModules/FlushTotes.js` | Front-end logic: form handling, API calls, WebSocket events. |
| `app/core/websockets/flush_totes/consumer.py` | Channels consumer to broadcast tote events. |
| `app/core/websockets/flush_totes/routes.py` | WebSocket URL patterns for flush totes. |

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

Validation rules (service-level and/or `clean()`):
- Initial pH required before final pH can be entered.
- pH values must be numeric; range for approval is 5.1–10.9 inclusive.
- If initial pH outside range, set status to `needs_action` until action text + compliant final pH are provided.
- Approve only when final pH exists and is in range; set status `approved`.

Option sourcing:
- `flush_type` choices populated at runtime from distinct `BlendContainerClassification.flush_tote` values (non-null, non-empty).

## URL Routes

```python
# app/core/urls.py
path("flush-totes/", views.flush_totes_view, name="flush_totes"),
path("api/flush-totes/", views.api_flush_totes, name="api_flush_totes"),
path("api/flush-totes/<int:pk>/", views.api_flush_tote_detail, name="api_flush_tote_detail"),
```

WebSocket:
```python
# app/core/websockets/flush_totes/routes.py
re_path(r"ws/flush_totes/$", FlushToteConsumer.as_asgi()),
re_path(r"ws/flush_totes/(?P<tote_id>\\d+)/$", FlushToteConsumer.as_asgi()),
```
Included in `app/websockets/routing.py`.

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
    - set line_personnel=user when user in line personnel group
    - default status pending
    """

def record_initial_ph(tote: FlushToteReading, ph_value, user) -> FlushToteReading:
    """
    - store lab_technician=user
    - update status to needs_action if out of range
    """

def record_action_and_final_ph(tote, action_text, final_ph, user) -> FlushToteReading:
    """
    - require action_text if status needs_action
    - approve when final pH within range
    """
```

All services emit WebSocket events after save (via publisher helper or consumer group send).

### Views
```python
def flush_totes_view(request):
    """Render page with production line options, flush type list, and initial table data."""

@require_http_methods(["GET", "POST"])
def api_flush_totes(request):
    """GET: list recent totes. POST: create new tote."""

@require_http_methods(["PATCH", "PUT"])
def api_flush_tote_detail(request, pk):
    """Update fields depending on role (initial pH, action, final pH, status)."""
```
Role checks: use existing Django groups “lab technician” and “line personnel” to toggle allowed fields server-side and client-side.

### WebSocket
```python
# Consumer: FlushToteConsumer
# Groups:
#   "flush_totes_all" for list updates
#   "flush_tote_<id>" for focused updates (optional, reuse same consumer)
# Events:
#   tote_created, tote_updated, status_changed
# Payload: serialized tote (id, timestamps, users, pH, status, action_required)
```
Flow: HTTP mutations persist data; service layer also publishes to channel layer; consumer relays to all subscribed clients so their table/form updates live. Redis-backed persistence mirrors existing pattern (`RedisBackedConsumer`).

## Frontend

### Template Structure
```
flush_totes.html
├── extends base.html
├── filters/create form (line personnel) with production_line & flush_type selects
├── table of totes (recent) with status badges and last-updated info
├── inline row edit controls (no modal) similar to container-classification page
│   - row switches to inputs for pH/action fields; line column editable only for creator role
└── loads static/core/js/pageModules/FlushTotes.js
```

### JavaScript
```javascript
// pageModules/FlushTotes.js
// - open WebSocket ws/flush_totes/; subscribe to tote updates
// - inline row edit UX patterned after containerClassificationRecords.js:
//     * click edit toggles inputs in-row for pH/action/status fields
//     * save triggers async POST/PATCH to api/flush-totes/<id>/ (field-level delta)
//     * cancel restores prior snapshot; new row creation inline
// - handle create form submit (POST api/flush-totes/), optimistic row add
// - handle lab tech actions (initial pH, action text, final pH) via PATCH
// - update table rows on websocket events; show status badges/colors
// - basic reconnect + offline banner when websocket drops
```
Uses jQuery + Bootstrap 5 consistent with codebase; leverages existing `apiClient` helpers if available in base.js.

Inline editing reference: mirror patterns from `app/core/templates/core/lotnumbers/containerclassificationrecords.html` and `app/core/static/core/js/pageModules/containerClassificationRecords.js` (row-level edit buttons, snapshot/restore, async save/delete) adapted to Flush Tote fields.

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Missing required fields or non-numeric pH | Return 400 with field errors; show inline messages. |
| Initial pH out of range | Set status `needs_action`, require action text before final pH approval. |
| Final pH still out of range | Keep status `needs_action`; block approval; toast message. |
| Redis/WebSocket unavailable | Allow HTTP save; show reconnect banner; poll fallback (optional short-term). |
| Unauthorized role editing restricted fields | Return 403; client hides/locks disallowed inputs. |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| Auto-fill date/time, require line + flush type | `create_flush_tote_reading` service, create form defaults |
| Initial pH check + action if outside 5.1–10.9 | `record_initial_ph` service, validation, UI status |
| Final pH within range before approval | `record_action_and_final_ph` service; approval_status logic |
| Real-time visibility for both roles | WebSocket consumer + JS live updates |
| Flush type options from BlendContainerClassification | `get_flush_type_options` selector feeding form select |

---

**Status**: Approved
