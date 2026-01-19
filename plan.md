# Flush Tote Indicator Implementation Plan

## Overview
Add a flush tote indicator to the specsheet page showing which flush tote the production team should use when running the current product.

## Prerequisites (✓ Complete)
- `flush_tote` column added to `BlendContainerClassification` model in `core/models.py`
- Database values populated

## Implementation Steps

### 1. Update View (`app/prodverse/views.py`)

In `display_specsheet_detail()` function (around line 223), add lookup for flush tote:

```python
# Add import at top of file
from core.models import BillOfMaterials, CiItem, ImItemWarehouse, BlendContainerClassification

# Inside the try block, after getting specsheet data (around line 222):
# Fetch flush tote classification
flush_tote = None
try:
    container_classification = BlendContainerClassification.objects.filter(
        item_code__iexact=specsheet.component_item_code
    ).first()
    if container_classification:
        flush_tote = container_classification.flush_tote
except BlendContainerClassification.DoesNotExist:
    pass

# Add to context dict (around line 278):
'flush_tote': flush_tote,
```

**Note**: The lookup uses `component_item_code` from the specsheet since `BlendContainerClassification` tracks blend item codes, not finished goods.

### 2. Update Template (`app/prodverse/templates/prodverse/specsheet.html`)

Add the flush tote indicator near the "Show Flush Part Numbers" button (around line 143-145). Place it prominently so production staff can see it at a glance:

```html
<div class="noPrint" id="flushButtonContainer" style="text-align: center; margin-bottom: 1rem;">
    {% if flush_tote %}
    <div class="alert alert-info" style="display: inline-block; margin-right: 1rem; padding: 0.5rem 1rem;">
        <strong>Flush Tote:</strong> {{ flush_tote }}
    </div>
    {% endif %}
    <button class="btn btn-secondary" onclick="document.getElementById('flushPartsDialog').showModal()">Show Flush Part Numbers</button>
</div>
```

## UI Considerations
- Uses Bootstrap alert styling for visibility
- Inline display next to existing button
- Only shows when flush_tote has a value
- Marked `noPrint` since it's operational guidance, not documentation

## Files Modified
1. `app/prodverse/views.py` - Add BlendContainerClassification import and flush_tote lookup
2. `app/prodverse/templates/prodverse/specsheet.html` - Add flush tote display element

## Testing
1. Load a specsheet for an item that has a `BlendContainerClassification` record with `flush_tote` populated
2. Verify the flush tote indicator displays correctly
3. Load a specsheet for an item without a classification record - verify no indicator shows (graceful handling)
