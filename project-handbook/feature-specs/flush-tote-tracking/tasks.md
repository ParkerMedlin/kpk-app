# Flush Tote Tracking Tasks

## Overview

Implementation tasks for the flush tote testing/approval workflow. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`  
**Design**: See `design.md`

## Phase 1: Data Layer

- [ ] **1.1** Create `FlushToteReading` model and migration  
  - **Do**: Add model (fields, choices, meta) and validators from design; include pH range constants and status choices.  
  - **Deliverable**: Model in `app/core/models.py`; new migration file.  
  - **Verify**: `python manage.py makemigrations` succeeds.  
  - **Requirement**: Core Functionality – auto date, required line & flush type, pH tracking.

- [ ] **1.2** Apply migrations  
  - **Do**: Run database migrate locally.  
  - **Deliverable**: Table `core_flush_tote_reading` created.  
  - **Verify**: `python manage.py migrate` succeeds.

- [ ] **1.3** Create selectors  
  - **Do**: Implement `list_flush_totes`, `get_flush_tote`, `get_flush_type_options` in `app/core/selectors/flush_totes.py`; export via `__init__.py`.  
  - **Deliverable**: Selector module returning recent totes and option lists.  
  - **Verify**: Functions return expected QuerySets/options in shell.  
  - **Requirement**: Core Functionality – surface flush type options; real-time list view data.

## Phase 2: Business Logic

- [ ] **2.1** Implement services for tote lifecycle  
  - **Do**: Add `create_flush_tote`, `record_initial_ph`, `record_action_and_final_ph` in `app/core/services/flush_totes.py`; set line/lab users, status transitions, WebSocket publish hooks.  
  - **Deliverable**: Service module with unit-level validation and status logic.  
  - **Verify**: Service functions update records correctly in Django shell.  
  - **Requirement**: Core Functionality – pH workflow, role handling, status changes.

- [ ] **2.2** Add validation/error handling  
  - **Do**: Enforce numeric pH, initial-before-final, action required when out of range, approval only when final pH within 5.1–10.9; raise friendly errors.  
  - **Deliverable**: Validation paths in services/forms; tests or manual checks.  
  - **Requirement**: Error Handling – reject bad input, block approval until compliant.

## Phase 3: API/Views

- [ ] **3.1** Add web view  
  - **Do**: Create `flush_totes_view` in `app/core/views/web.py` to render page with options + initial data.  
  - **Deliverable**: View returns template context for production lines, flush types, current totes.  
  - **Requirement**: UX – page available to both roles.

- [ ] **3.2** Add API endpoints  
  - **Do**: Implement list/create (`api_flush_totes`) and update (`api_flush_tote_detail`) in `app/core/views/api.py` using services; enforce role-based editable fields.  
  - **Deliverable**: JSON endpoints for POST/PATCH.  
  - **Verify**: Requests return expected payload/status codes.  
  - **Requirement**: Core Functionality – create/update via async calls; Error Handling responses.

- [ ] **3.3** Wire URL routes  
  - **Do**: Add paths for web + API in `app/core/urls.py`.  
  - **Deliverable**: Routes resolve (`flush-totes/`, `api/flush-totes/`, `api/flush-totes/<id>/`).  
  - **Verify**: `python manage.py show_urls` or manual reverse succeeds.

## Phase 4: Frontend

- [ ] **4.1** Build template with inline row forms  
  - **Do**: Create `app/core/templates/core/flush_totes.html` modeled after container classification page; inline edit controls per row (no modal); role-based enablement; status badges.  
  - **Deliverable**: Rendered page shows table and create form.  
  - **Verify**: Page loads and rows switch to editable inputs.

- [ ] **4.2** Implement JS page module  
  - **Do**: Add `app/core/static/core/js/pageModules/FlushTotes.js` to handle inline edits, async POST/PATCH to API, optimistic updates, reconnect banner; reuse patterns from `containerClassificationRecords.js`.  
  - **Deliverable**: Interactive page with client-side validation, toast/errors.  
  - **Verify**: Creating/editing rows works without reload.

- [ ] **4.3** Add navigation entry (if needed)  
  - **Do**: Link page from appropriate navbar/menu.  
  - **Deliverable**: Nav link to `flush-totes/`.  
  - **Verify**: Link appears for permitted roles.

## Phase 5: WebSocket

- [ ] **5.1** Create consumer and routes  
  - **Do**: Add `FlushToteConsumer` in `app/core/websockets/flush_totes/consumer.py` and `routes.py`; hook to RedisBackedConsumer pattern.  
  - **Deliverable**: Consumer broadcasting tote_created/updated/status_changed.  
  - **Requirement**: Core Functionality – real-time updates.

- [ ] **5.2** Register WebSocket URLs  
  - **Do**: Include flush tote routes in `app/websockets/routing.py`.  
  - **Deliverable**: `ws/flush_totes/` (and optional per-id) endpoints active.  
  - **Verify**: `daphne`/`runserver` accepts connection.

- [ ] **5.3** Wire client WebSocket handling  
  - **Do**: In `FlushTotes.js`, open socket, handle reconnect, merge incoming tote payloads into table rows.  
  - **Deliverable**: Live updates reflected across open clients.  
  - **Verify**: Two browser sessions reflect updates instantly.

## Phase 6: Integration

- [ ] **6.1** End-to-end verification  
  - **Do**: Manually walk acceptance criteria: create tote, record out-of-range initial pH, add action + final pH, see approval + WebSocket updates.  
  - **Verify**: All acceptance criteria pass.

- [ ] **6.2** Deployment checklist  
  - **Do**: Note collectstatic if JS/template added; confirm Channels/Redis config unchanged.  
  - **Deliverable**: Ready-to-deploy notes.

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Data Layer | Not Started | 0/3 |
| 2. Business Logic | Not Started | 0/2 |
| 3. API/Views | Not Started | 0/3 |
| 4. Frontend | Not Started | 0/3 |
| 5. WebSocket | Not Started | 0/3 |
| 6. Integration | Not Started | 0/2 |

**Overall**: 0/16 tasks (0%)

---

**Status**: Draft
