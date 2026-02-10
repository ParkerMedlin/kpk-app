# Waste Rag Color Codes – Issues

Discovered during manual testing.

---

## Issue 1: Spec sheet shows N/A for waste_rag despite value being set

**Problem:** The spec sheet displays "N/A" for the Waste Rag badge even though the container classification record for that blend item has `waste_rag` set to "Soaps" in the admin.

**Expected Behavior:**
- When a classification record exists with `waste_rag` = "Soaps", the spec sheet should display a colored "Soaps" badge.

**Root Cause Analysis:**

The spec sheet view looks up `BlendContainerClassification` using `specsheet.component_item_code` from the `specsheet_data` ETL table. This field doesn't reliably resolve to the BLEND-* item code that classification records are keyed by.

What happens at runtime:
- The view finds a classification record via `component_item_code` (e.g., a CHEM-* component) that has `flush_tote` set but `waste_rag` = ""
- The user set `waste_rag` on a different classification record, keyed by the BLEND-* item code
- The view never queries the BLEND-* record

```
URL item_code (parent/finished good)
  -> specsheet_data.component_item_code (from ETL "Part Number")
  -> view looks up BlendContainerClassification where item_code = component_item_code
  -> finds record with flush_tote="ABC", waste_rag="" <-- THIS record
  -> ignores record keyed by BLEND-* item, which has waste_rag="Soaps"
```

**Code Locations:**
- `app/prodverse/views.py` lines 224-232 — classification lookup uses `specsheet.component_item_code`
- `app/core/views/api.py` lines 2190-2204 — `validate_blend_item` accepts both BLEND-* and CHEM-* items
- `app/core/models.py` lines 70-86 — `BillOfMaterials` model with `component_item_description` field

**Fix Approach:**
Add a helper function that queries `bill_of_materials` to resolve the BLEND-* component item code for a given parent item, using `component_item_description LIKE 'BLEND%'`. This gives us the canonical BLEND-* item code that classification records are keyed by. Replace the current `specsheet.component_item_code` lookup with this BOM-based resolution.

### Tasks

- [x] 1.1 Add `_get_blend_component_item_code(item_code)` helper to `app/prodverse/views.py` — queries `BillOfMaterials` where `item_code=item_code` and `component_item_description` starts with "BLEND", returns `component_item_code`
- [x] 1.2 Update `display_specsheet_detail` to use `_get_blend_component_item_code(item_code)` instead of `specsheet.component_item_code` for the `BlendContainerClassification` lookup
- [ ] 1.3 Test: Verify spec sheet shows waste_rag badge for a blend with waste_rag set on the BLEND-* classification record
- [ ] 1.4 Test: Verify flush_tote still displays correctly (no regression)
- [ ] 1.5 Test: Verify N/A still shows when no classification exists

---
