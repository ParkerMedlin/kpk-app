# Waste Rag Color Codes Design

## Overview

Add a `waste_rag` choices field to `BlendContainerClassification`, expose it through the existing admin CRUD, and display it as a color-coded badge on the spec sheet. No new models, URLs, or services needed — this threads through existing infrastructure.

## Affected Components

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/core/models.py:1261` | Add `waste_rag` TextField with choices to `BlendContainerClassification` |
| `app/core/forms.py:459` | Add `waste_rag` to form fields with Select widget |
| `app/core/services/operating_supplies_services.py:180` | Add `waste_rag` to `_serialize_container_classification()` |
| `app/core/templates/core/lotnumbers/containerclassificationrecords.html` | Add "Waste Rag" column to table |
| `app/core/static/core/js/pageModules/containerClassificationRecords.js` | Handle `waste_rag` as a `<select>` in edit mode, update `buildRow`/`handleSave`/`handleAdd` |
| `app/prodverse/views.py:224` | Fetch `waste_rag` from classification, resolve badge color, pass to context |
| `app/prodverse/templates/prodverse/specsheet.html:185` | Add "Waste Rags" row with colored badge |

### New Files to Create
None.

## Data Model

### Model Changes
```python
# In BlendContainerClassification (app/core/models.py:1261):
WASTE_RAG_CHOICES = [
    ('', ''),
    ('Acids', 'Acids'),
    ('Flammables', 'Flammables'),
    ('Grease/Oil', 'Grease/Oil'),
    ('Soaps', 'Soaps'),
    ('Bleach', 'Bleach'),
]

waste_rag = models.TextField(blank=True, default='', choices=WASTE_RAG_CHOICES)
```

### Color Mapping (hardcoded in view)
```python
WASTE_RAG_COLORS = {
    'Acids': ('#000', '#ffc107'),        # black text on yellow
    'Flammables': ('#fff', '#dc3545'),   # white text on red
    'Grease/Oil': ('#000', '#fd7e14'),   # black text on orange
    'Soaps': ('#000', '#f8f9fa'),        # black text on white
    'Bleach': ('#fff', '#0d6efd'),       # white text on blue
}
```

## Frontend

### Container Classification Admin (`containerClassificationRecords.js`)
- Add `waste_rag` column to the table
- In `buildInput()`: render a `<select>` with the 5 choices + blank option (not a text input, not an autofill field)
- In `buildRow()`: add `waste_rag` cell
- In `handleSave()` / `handleAdd()`: include `waste_rag` in payloads
- In snapshot/exitEditMode: handle `waste_rag` like other fields

### Spec Sheet Template (`specsheet.html`)
- New row after the existing "Flush Tote" row (after line 185)
- Badge styled with inline `background-color` and `color` from the mapping
- Falls back to "N/A" badge (same style as flush_tote) when no waste_rag set

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| No container classification record | Display "N/A" badge |
| `waste_rag` field is blank | Display "N/A" badge |

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| Display waste rag color on spec sheet | `prodverse/views.py` context + `specsheet.html` badge |
| Color mapping (Acids→Yellow, etc.) | `WASTE_RAG_COLORS` dict in view |
| Admin can set waste rag type | `waste_rag` field in model/form + dropdown in JS |
| Dropdown with 5 choices | `WASTE_RAG_CHOICES` on model + `<select>` in JS edit mode |

---

**Status**: Draft
