# Waste Rag Color Codes - Manual Test Checklist

## Setup
- [ ] Use or create an item with a `SpecSheetData` record and a related `BlendContainerClassification` record (matching `component_item_code` to classification `item_code`).
- [ ] Ensure you can access the container classification admin table and the spec sheet view for the item.

## Admin Data Entry (Container Classification)
- [ ] Open the container classification admin table and locate the target record.
- [ ] Verify the "Waste Rag" column is visible.
- [ ] Enter edit mode for the row and confirm a dropdown is shown (not a text input).
- [ ] Verify the dropdown choices are exactly: Acids, Flammables, Grease/Oil, Soaps, Bleach (plus a blank option).
- [ ] Save with each choice (one at a time), refresh, and confirm the value persists.
- [ ] Clear the value (blank) and save; confirm it persists as blank.

## Spec Sheet Display
- [ ] Open the spec sheet for the item and locate the "Waste Rag" row (after "Flush Tote").
- [ ] With `waste_rag` blank, confirm the badge shows "N/A".
- [ ] Set `waste_rag` to Acids, refresh spec sheet, confirm badge text and color:
  - Text: "Acids"; Background: Yellow; Text color: Black
- [ ] Set `waste_rag` to Flammables, refresh spec sheet, confirm badge text and color:
  - Text: "Flammables"; Background: Red; Text color: White
- [ ] Set `waste_rag` to Grease/Oil, refresh spec sheet, confirm badge text and color:
  - Text: "Grease/Oil"; Background: Orange; Text color: Black
- [ ] Set `waste_rag` to Soaps, refresh spec sheet, confirm badge text and color:
  - Text: "Soaps"; Background: White; Text color: Black
- [ ] Set `waste_rag` to Bleach, refresh spec sheet, confirm badge text and color:
  - Text: "Bleach"; Background: Blue; Text color: White

## No Classification Record
- [ ] Use an item whose spec sheet has no matching container classification record.
- [ ] Confirm the spec sheet "Waste Rag" badge shows "N/A".

## Regression Check
- [ ] Verify "Flush Tote" still renders correctly and remains unchanged.
