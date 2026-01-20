# Table Utilities Consolidation Tasks

## Overview

Implementation tasks for consolidating table utilities into `tableObjects.js`. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

Note: This is purely frontend JavaScript refactoring—no database or backend changes required.

## Phase 1: Create tableObjects.js

- [ ] **1.1** Create tableObjects.js with FilterForm
  - **Do**: Create `app/core/static/core/js/objects/tableObjects.js`, move FilterForm class from lookupFormObjects.js
  - **Deliverable**: FilterForm exported from tableObjects.js
  - **Verify**: Import works: `import { FilterForm } from '../objects/tableObjects.js'`
  - **Requirement**: FilterForm acceptance criteria

- [ ] **1.2** Add backwards-compatible re-export
  - **Do**: In lookupFormObjects.js, replace FilterForm class with `export { FilterForm } from './tableObjects.js'`
  - **Deliverable**: Existing imports from lookupFormObjects.js still work
  - **Verify**: containerClassificationRecords.js continues to work without changes
  - **Requirement**: FilterForm backwards compatibility

- [ ] **1.3** Implement initDataTableWithExport()
  - **Do**: Add helper function that wraps DataTables initialization with standard defaults
  - **Deliverable**: Function exported from tableObjects.js
  - **Verify**: `initDataTableWithExport('#testTable')` initializes DataTables with buttons
  - **Requirement**: initDataTableWithExport acceptance criteria

- [ ] **1.4** Implement SortableRows class
  - **Do**: Add SortableRows class wrapping jQuery UI sortable with options for tableSelector, rowSelector, orderColumnIndex, onReorder, getRowId
  - **Deliverable**: Class exported from tableObjects.js
  - **Verify**: Class can be instantiated and makes rows draggable
  - **Requirement**: SortableRows acceptance criteria

## Phase 2: Migrate Existing Pages

- [ ] **2.1** Refactor DeskSchedulePage
  - **Do**: In pageObjects.js, replace inline sortable code with `new SortableRows({...})`
  - **Deliverable**: DeskSchedulePage uses SortableRows, ~25 lines removed
  - **Verify**: Drag-and-drop reordering still works, order saves to backend
  - **Requirement**: SortableRows acceptance criteria

- [ ] **2.2** Refactor CountCollectionLinksPage
  - **Do**: In pageObjects.js, replace inline sortable code with `new SortableRows({...})`
  - **Deliverable**: CountCollectionLinksPage uses SortableRows
  - **Verify**: Drag-and-drop reordering still works, WebSocket order update still fires
  - **Requirement**: SortableRows acceptance criteria

- [ ] **2.3** Update containerClassificationRecords.js import (optional)
  - **Do**: Change import from `'../objects/lookupFormObjects.js'` to `'../objects/tableObjects.js'`
  - **Deliverable**: Direct import from canonical location
  - **Verify**: Page still works
  - **Requirement**: FilterForm acceptance criteria

## Phase 3: Documentation & Integration

- [ ] **3.1** Document InlineEditTable interface
  - **Do**: Add JSDoc comment block for InlineEditTable class stub in tableObjects.js (implementation deferred)
  - **Deliverable**: Interface documented for future implementation
  - **Requirement**: InlineEditTable acceptance criteria (interface only)

- [ ] **3.2** End-to-end verification
  - **Do**: Test all affected pages manually
  - **Verify**:
    - DeskSchedulePage: drag rows, verify order persists after refresh
    - CountCollectionLinksPage: drag rows, verify WebSocket broadcasts order
    - ContainerClassificationRecords: filter works, inline editing works
  - **Requirement**: All acceptance criteria

- [ ] **3.3** Deploy
  - **Do**: `kpk git pull && kpk git collectstatic`
  - **Deliverable**: Changes live on production
  - **Note**: Static file changes require collectstatic

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Create tableObjects.js | Not Started | 0/4 |
| 2. Migrate Existing Pages | Not Started | 0/3 |
| 3. Documentation & Integration | Not Started | 0/3 |

**Overall**: 0/10 tasks (0%)

---

**Status**: Draft
