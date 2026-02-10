# Waste Rag Color Codes Requirements

## Problem Statement

Production floor staff need to know which color waste rag to use when cleaning up spills or residue from a given blend. The color is determined by the blend's chemical classification (acids, flammables, grease/oil, soaps, bleach). This information should be displayed on the spec sheet so operators can see it at a glance during production.

## User Stories

### Production Operator
- **As a** production operator, **I want to** see the waste rag color on the spec sheet, **so that** I grab the correct rag for the blend I'm running without having to look it up separately.

### Data Administrator
- **As a** data administrator, **I want to** set the waste rag type on container classification records, **so that** the correct color displays on spec sheets.

## Acceptance Criteria

### Core Functionality
- **WHEN** a spec sheet is viewed for an item with a container classification that has a `waste_rag` set, **THEN** the system **SHALL** display the waste rag color as a colored badge.
- **WHEN** the item has no container classification record or `waste_rag` is blank, **THEN** the system **SHALL** display "N/A".

### Color Mapping
- Acids &rarr; Yellow
- Flammables &rarr; Red
- Grease/Oil &rarr; Orange
- Soaps &rarr; White
- Bleach &rarr; Blue

### Data Entry
- **WHEN** editing a container classification record, **THEN** the admin UI **SHALL** include a "Waste Rag Type" dropdown with choices: Acids, Flammables, Grease/Oil, Soaps, Bleach.

## Scope

### In Scope
- Adding `waste_rag` field to `BlendContainerClassification` model (choices-based TextField)
- Hardcoded mapping from `waste_rag` value to badge color
- Displaying the waste rag color badge on the spec sheet page
- Updating the container classification admin form and table

### Out of Scope
- Displaying waste rag colors on any page other than the spec sheet
- Multiple waste rag categories per item (one category only)

## Dependencies

- `BlendContainerClassification` model (existing, `app/core/models.py`)
- `SpecSheetData` model and spec sheet view (existing, `app/prodverse/`)

---

**Status**: Draft
