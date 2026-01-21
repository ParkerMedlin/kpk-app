# Flush Tote Tracking Tasks

## Overview

Implementation tasks for the flush tote testing/approval workflow. Work through sequentially, marking complete as you go.
Use existing naming conventions: `flush_tote_services.py`, `flush_tote_selectors.py`, `flush_tote_list_api` / `flush_tote_detail_api`, and snake_case function names throughout.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Data Layer

- [x] **1.1** Create `FlushToteReading` model and migration
  - **Do**: Add model (fields, choices, meta) and validators from design; include pH range constants and status choices.
  - **Deliverable**: Model in `app/core/models.py`; new migration file.
  - **Verify**: `python manage.py makemigrations` succeeds.
  - **Requirement**: Core Functionality – auto date, required line & flush type, pH tracking.

- [x] **1.2** Apply migrations (this will be delegated to user, do not do this yourself)
  - **Do**: prompt user to execute the migrations

- [x] **1.3** Create selectors
  - **Do**: Implement `list_flush_totes`, `get_flush_tote`, `get_flush_type_options` in `app/core/selectors/flush_tote_selectors.py`; export via `__init__.py`.
  - **Deliverable**: Selector module returning recent totes and option lists.
  - **Verify**: Functions return expected QuerySets/options in shell.
  - **Requirement**: Core Functionality – surface flush type options; real-time list view data.

## Phase 2: Business Logic

- [x] **2.1** Implement services for tote lifecycle
  - **Do**: Add `create_flush_tote_reading`, `record_initial_ph`, `record_action_and_final_ph` in `app/core/services/flush_tote_services.py`; set line/lab users, status transitions.
  - **Deliverable**: Service module with unit-level validation and status logic.
  - **Verify**: Service functions update records correctly in Django shell.
  - **Requirement**: Core Functionality – pH workflow, role handling, status changes.

- [x] **2.2** Add validation/error handling
  - **Do**: Enforce numeric pH, initial-before-final, action required when out of range, approval only when final pH within 5.1–10.9; raise friendly errors.
  - **Deliverable**: Validation paths in services/forms; tests or manual checks.
  - **Requirement**: Error Handling – reject bad input, block approval until compliant.

## Phase 3: API/Views

- [x] **3.1** Add web view
  - **Do**: Create `flush_totes_view` in `app/core/views/web.py` to render page with options + initial data.
  - **Deliverable**: View returns template context for production lines, flush types, current totes.
  - **Requirement**: UX – page available to authorized users.

- [x] **3.2** Add API endpoints
  - **Do**: Implement list/create (`flush_tote_list_api`) and update (`flush_tote_detail_api`) in `app/core/views/api.py` using services.
  - **Deliverable**: JSON endpoints for POST/PATCH.
  - **Verify**: Requests return expected payload/status codes.
  - **Requirement**: Core Functionality – create/update via async calls; Error Handling responses.

- [x] **3.3** Wire URL routes
  - **Do**: Add paths for web + API in `app/core/urls.py`.
  - **Deliverable**: Routes resolve (`flush-totes/`, `api/flush-totes/`, `api/flush-totes/<id>/`).
  - **Verify**: `python manage.py show_urls` or manual reverse succeeds.

## Phase 4: Frontend

- [x] **4.1** Build template with inline row forms
  - **Do**: Create `app/core/templates/core/flush_totes.html` modeled after container classification page; inline edit controls per row (no modal); status badges.
  - **Deliverable**: Rendered page shows table and create form.
  - **Verify**: Page loads and rows switch to editable inputs.

- [x] **4.2** Implement JS page module
  - **Do**: Add `app/core/static/core/js/pageModules/FlushTotes.js` to handle inline edits, async POST/PATCH to API, optimistic updates; reuse patterns from `containerClassificationRecords.js`.
  - **Deliverable**: Interactive page with client-side validation, toast/errors.
  - **Verify**: Creating/editing rows works without reload.

- [x] **4.3** Add navigation entry
  - **Do**: Link page from admin navbar menu.
  - **Deliverable**: Nav link to `flush-totes/`.
  - **Verify**: Link appears for staff users.

## ~~Phase 5: WebSocket~~ (Removed)

_WebSocket functionality removed from scope per revised requirements._

## Phase 6: Integration

- [x] **6.1** End-to-end verification
  - **Do**: Manually walk acceptance criteria: create tote via entry form, verify pH validation, confirm approval status logic.
  - **Verify**: All acceptance criteria pass.

- [x] **6.2** Deployment checklist
  - **Do**: Note collectstatic if JS/template added.
  - **Deliverable**: Ready-to-deploy notes.

---

## Phase 7: Change Order – UI Restructure

_Added to address revised user story: lab tech single-form entry + admin records page._

- [x] **7.1** Create lab tech entry form template
  - **Do**: Create `app/core/templates/core/flush_tote_entry.html` with single form containing all fields (production_line, flush_type, line_personnel name as text, initial_pH, action_required, final_pH).
  - **Deliverable**: Form page at `/flush-tote-entry/`.
  - **Requirement**: Single-session entry for lab technicians.

- [ ] **7.2** Create entry form JS module
  - **Do**: Create `app/core/static/core/js/pageModules/FlushToteEntry.js` with form validation, pH range feedback, async POST, success toast + form reset.
  - **Deliverable**: Interactive form with client-side validation.
  - **Verify**: Submitting form creates record and resets for next entry.

- [ ] **7.3** Add entry form view
  - **Do**: Add `flush_tote_entry_view` in `app/core/views/web.py`; restrict to lab technician group or staff.
  - **Deliverable**: View renders entry form template with options context.

- [ ] **7.4** Refactor existing page as admin records view
  - **Do**: Update `flush_totes.html` to be admin-only records table; remove create form (lab entry moved to separate page); remove line personnel role checks; add search/filter.
  - **Deliverable**: Staff-only records page at `/flush-tote-records/`.

- [ ] **7.5** Update FlushTotes.js for admin table
  - **Do**: Remove WebSocket code and reconnect banner; simplify to inline edit only; add search/filter support.
  - **Deliverable**: Clean admin table JS without WebSocket dependencies.

- [ ] **7.6** Update URL routes
  - **Do**: Change routes in `app/core/urls.py`: `/flush-tote-entry/` → entry view, `/flush-tote-records/` → records view; keep API routes unchanged.
  - **Deliverable**: New URL structure active.

- [ ] **7.7** Update navigation links
  - **Do**: In `app/templates/navbars/admin-navbar-items.html`, update link to point to `/flush-tote-records/`; add lab entry link to appropriate lab technician nav if applicable.
  - **Deliverable**: Nav links point to correct pages.

- [ ] **7.8** Update services for simplified flow
  - **Do**: Review `flush_tote_services.py`; ensure `create_flush_tote_reading` sets `lab_technician` (not `line_personnel` FK) and accepts `line_personnel_name` as text if model uses FK; adjust as needed for single-submit flow.
  - **Deliverable**: Services support entry form use case.

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Data Layer | Complete | 3/3 |
| 2. Business Logic | Complete | 2/2 |
| 3. API/Views | Complete | 3/3 |
| 4. Frontend | Complete | 3/3 |
| 5. WebSocket | Removed | N/A |
| 6. Integration | Not Started | 2/2 |
| 7. Change Order | Not Started | 0/8 |

**Overall**: 11/21 tasks (52%)

---

**Status**: In Progress
