# [Feature Name] Design

## Overview

[Brief description of the technical approach. How does this feature fit into the existing system?]

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/views/web.py` | [What changes] |
| `app/core/views/api.py` | [What changes] |
| `app/core/models.py` | [What changes] |

### New Files to Create
| File | Purpose |
|------|---------|
| `app/core/selectors/[feature]_selectors.py` | [Purpose] |
| `app/core/services/[feature]_services.py` | [Purpose] |
| `app/core/templates/core/[feature].html` | [Purpose] |
| `app/core/static/core/js/pageModules/[feature].js` | [Purpose] |

## Data Model

### New Models (if any)
```python
class [ModelName](models.Model):
    """[Description]"""
    field_name = models.FieldType(...)

    class Meta:
        db_table = 'core_[tablename]'
```

### Model Changes (if any)
```python
# In existing model [ModelName]:
new_field = models.FieldType(...)
```

### Unmanaged Tables (if using existing Sage/calculated tables)
- `[table_name]` - [how it's used]

## URL Routes

```python
# In app/core/urls.py
path('[feature-route]/', views.[view_function], name='[feature_name]'),
path('api/[feature-route]/', views.[api_function], name='api_[feature_name]'),
```

## Layer Design

### Selectors (data retrieval)
```python
def get_[feature]_data(filters) -> QuerySet:
    """[What this returns]"""
    pass

def get_[feature]_by_id(id) -> dict:
    """[What this returns]"""
    pass
```

### Services (business logic)
```python
def create_[feature](data: dict) -> [Model]:
    """[What this does, side effects]"""
    pass

def update_[feature](id, data: dict) -> [Model]:
    """[What this does, side effects]"""
    pass
```

### Views
```python
def [feature]_view(request):
    """Renders [template] with [context]"""
    pass

def [feature]_api(request):
    """Returns JSON: [structure]"""
    pass
```

## Frontend

### Template Structure
```
[feature].html
├── extends base.html
├── includes [components]
└── loads [js modules]
```

### JavaScript
```javascript
// pageModules/[feature].js
// - Initializes [what]
// - Event handlers for [what]
// - API calls to [endpoints]
```

### WebSocket (if real-time needed)
```python
# Consumer: app/core/websockets/[feature]/consumer.py
# Group: [feature]_unique_{context}
# Events: [event_type]
```

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| [Condition] | [How handled, user message] |
| [Condition] | [How handled, user message] |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| [From requirements.md] | [Component/function] |
| [From requirements.md] | [Component/function] |

---

**Status**: Draft | Approved
