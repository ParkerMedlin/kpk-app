# Table Utilities Consolidation Tasks

## Overview

Implementation tasks for table utilities consolidation. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Core Module

- [ ] **1.1** Create tableObjects.js with SortableRows class
  - **Do**: Create `app/core/static/core/js/objects/tableObjects.js` with SortableRows class implementing constructor, `_init()`, `_updateOrderValues()`, `_invokeCallback()`, `destroy()`
  - **Deliverable**: SortableRows class that wraps jQuery UI sortable
  - **Verify**: Import works, class instantiates without error
  - **Requirement**: SortableRows acceptance criteria

- [ ] **1.2** Add ColumnFilter class to tableObjects.js
  - **Do**: Implement ColumnFilter with `_createFilterRow()`, `_attachListeners()`, `_applyFilters()`, `clearFilters()`, `destroy()`
  - **Deliverable**: ColumnFilter class with per-column text filtering
  - **Verify**: Filter inputs appear in header, filtering works with AND logic
  - **Requirement**: ColumnFilter acceptance criteria

- [ ] **1.3** Add FormRowTable class to tableObjects.js
  - **Do**: Implement FormRowTable with `_attachAddHandler()`, `_attachChangeHandlers()`, `_attachDeleteHandlers()`, `_setupDirtyTracking()`, `addRow()`, `markClean()`, `destroy()`
  - **Deliverable**: FormRowTable class with inline editing and dirty tracking
  - **Verify**: Add/delete rows works, beforeunload warning fires when dirty
  - **Requirement**: FormRowTable acceptance criteria

- [ ] **1.4** Add enhanceTable() helper function
  - **Do**: Implement composition helper that instantiates requested behaviors
  - **Deliverable**: `enhanceTable(tableSelector, options)` function
  - **Verify**: Can apply multiple behaviors to same table without conflicts
  - **Requirement**: enhanceTable acceptance criteria

## Phase 2: Migrate DeskSchedulePage

- [ ] **2.1** Refactor DeskSchedulePage to use SortableRows
  - **Do**: In `pageObjects.js` DeskSchedulePage class (~lines 2893-3031), replace inline sortable code with `new SortableRows({...})`
  - **Deliverable**: DeskSchedulePage uses SortableRows, sortable code removed
  - **Verify**: Drag-and-drop reordering still works, order persists to database
  - **Requirement**: SortableRows - migrate DeskSchedulePage

- [ ] **2.2** Test DeskSchedulePage functionality
  - **Do**: Verify all existing functionality: drag rows, order updates, tank selection still works
  - **Deliverable**: No regression in DeskSchedulePage behavior
  - **Verify**: Manual test on desk schedule page

## Phase 3: Migrate CountCollectionLinksPage

- [ ] **3.1** Refactor CountCollectionLinksPage to use SortableRows
  - **Do**: In `pageObjects.js` CountCollectionLinksPage class (~lines 3106-3270), replace inline sortable code with `new SortableRows({...})`
  - **Deliverable**: CountCollectionLinksPage uses SortableRows
  - **Verify**: Drag-and-drop reordering works, WebSocket order update still fires
  - **Requirement**: SortableRows - migrate CountCollectionLinksPage

- [ ] **3.2** Test CountCollectionLinksPage functionality
  - **Do**: Verify drag reorder, inline rename editing, delete buttons all still work
  - **Deliverable**: No regression in CountCollectionLinksPage behavior
  - **Verify**: Manual test on count collection links page

## Phase 4: Migrate BlendInstructionEditorPage

- [ ] **4.1** Refactor BlendInstructionEditorPage to use SortableRows
  - **Do**: In `pageObjects.js` BlendInstructionEditorPage class (~lines 3285-3392), replace inline sortable code with `new SortableRows({...})` with `excludeSelector: '#addNewInstructionRow'`
  - **Deliverable**: BlendInstructionEditorPage uses SortableRows
  - **Verify**: Drag-and-drop works, "Add New" row is not draggable, order persists
  - **Requirement**: SortableRows - migrate BlendInstructionEditorPage

- [ ] **4.2** Test BlendInstructionEditorPage functionality
  - **Do**: Verify drag reorder, add new instruction row, form submission all still work
  - **Deliverable**: No regression in BlendInstructionEditorPage behavior
  - **Verify**: Manual test on blend instruction editor page

## Phase 5: CSS and Polish

- [ ] **5.1** Add CSS for column filter inputs
  - **Do**: Add styles for `.column-filter-row input` to appropriate CSS file
  - **Deliverable**: Filter inputs styled consistently with existing form inputs
  - **Verify**: Filter inputs have proper padding, borders, sizing

- [ ] **5.2** Add CSS for drag feedback
  - **Do**: Add/verify `tr.selected` styles for drag visual feedback
  - **Deliverable**: Dragged rows have visual indication
  - **Verify**: Row highlights when dragging

## Phase 6: Integration

- [ ] **6.1** End-to-end verification
  - **Do**: Test all three migrated pages in sequence
  - **Verify**: All acceptance criteria from requirements.md pass
  - **Requirement**: All SortableRows criteria

- [ ] **6.2** Deploy
  - **Do**: Run `kpk git collectstatic` after changes (static JS/CSS files)
  - **Deliverable**: Changes live on production
  - **Verify**: All three pages work in production

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Core Module | Not Started | 0/4 |
| 2. DeskSchedulePage | Not Started | 0/2 |
| 3. CountCollectionLinksPage | Not Started | 0/2 |
| 4. BlendInstructionEditorPage | Not Started | 0/2 |
| 5. CSS and Polish | Not Started | 0/2 |
| 6. Integration | Not Started | 0/2 |

**Overall**: 0/14 tasks (0%)

---

**Status**: Draft
