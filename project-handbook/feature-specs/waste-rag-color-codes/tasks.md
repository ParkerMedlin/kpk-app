# Waste Rag Color Codes Tasks

## Overview

Implementation tasks for waste rag color code display. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Data Layer

- [x] **1.1** Add `waste_rag` field to `BlendContainerClassification`
  - **Do**: Add `WASTE_RAG_CHOICES` list and `waste_rag = models.TextField(blank=True, default='', choices=WASTE_RAG_CHOICES)` to the model in `app/core/models.py:1261`
  - **Deliverable**: Field defined on model
  - **Verify**: `python manage.py makemigrations` succeeds
  - **Requirement**: Data Entry

- [x] **1.2 (USER ACTION)** Run migrations
  - **Do**: Apply migrations to database
  - **Verify**: `python manage.py migrate` succeeds

- [x] **1.3** Add `waste_rag` to form
  - **Do**: Add `waste_rag` to `BlendContainerClassificationForm` fields, with a `Select` widget and `'Waste Rag:'` label in `app/core/forms.py:459`
  - **Deliverable**: Form includes waste_rag field
  - **Requirement**: Data Entry

- [x] **1.4** Add `waste_rag` to serializer
  - **Do**: Add `'waste_rag': classification.waste_rag` to `_serialize_container_classification()` in `app/core/services/operating_supplies_services.py:180`
  - **Deliverable**: API responses include waste_rag
  - **Requirement**: Data Entry

## Phase 2: Admin Frontend

- [x] **2.1** Add "Waste Rag" column to admin table
  - **Do**: Add a `<th>Waste Rag</th>` column header and corresponding `<td data-field="waste_rag">` cell in `app/core/templates/core/lotnumbers/containerclassificationrecords.html`. Update colspan on empty-state row.
  - **Deliverable**: Column visible in table
  - **Requirement**: Data Entry

- [x] **2.2** Update `containerClassificationRecords.js` for waste_rag
  - **Do**: In `app/core/static/core/js/pageModules/containerClassificationRecords.js`:
    - `buildInput()`: Add a case for `waste_rag` that renders a `<select>` with blank + 5 choices (not a text input, not an autofill field)
    - `buildRow()`: Add `waste_rag` cell to generated rows
    - `handleSave()` / `handleAdd()`: Include `waste_rag` in payloads
    - `enterEditMode()` / `exitEditMode()` / `getRowSnapshot()`: Handle `waste_rag` like other fields (snapshot reads from select)
  - **Deliverable**: Waste rag editable as dropdown in admin table
  - **Requirement**: Data Entry — dropdown with 5 choices

## Phase 3: Spec Sheet Display

- [x] **3.1** Add waste rag color logic to spec sheet view
  - **Do**: In `app/prodverse/views.py:224` (`display_specsheet_detail`), after fetching `flush_tote` from the classification record, also fetch `waste_rag`. Define `WASTE_RAG_COLORS` mapping dict. Resolve to `waste_rag_text`, `waste_rag_bg`, `waste_rag_label` context variables. Pass to template.
  - **Deliverable**: Context includes waste rag color data
  - **Requirement**: Core Functionality, Color Mapping

- [x] **3.2** Add waste rag badge to spec sheet template
  - **Do**: In `app/prodverse/templates/prodverse/specsheet.html:185`, add a new row after the Flush Tote row. Display a badge with inline `background-color` and `color` styles from context variables. Fall back to "N/A" badge when no waste_rag is set.
  - **Deliverable**: Colored badge visible on spec sheet
  - **Requirement**: Core Functionality, Color Mapping

## Phase 4: Verification

- [x] **4.1** Manual testing checklist
  - **Do**: Create a testing checklist covering all acceptance criteria
  - **Deliverable**: `tests.md` in feature spec folder
  - **Requirement**: All

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Data Layer | Complete | 4/4 |
| 2. Admin Frontend | Complete | 2/2 |
| 3. Spec Sheet Display | Complete | 2/2 |
| 4. Verification | Complete | 1/1 |

**Overall**: 9/9 tasks (100%)

---

**Status**: Draft
