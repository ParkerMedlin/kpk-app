# [Feature Name] Tasks

## Overview

Implementation tasks for [feature name]. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Data Layer

- [ ] **1.1** Create/modify models
  - **Do**: [Specific model changes from design.md]
  - **Deliverable**: Models defined, migrations created
  - **Verify**: `python manage.py makemigrations` succeeds
  - **Requirement**: [Req reference]

- [ ] **1.2** Run migrations
  - **Do**: Apply migrations to database
  - **Deliverable**: Tables created/modified
  - **Verify**: `python manage.py migrate` succeeds

- [ ] **1.3** Create selectors
  - **Do**: [Specific selector functions from design.md]
  - **Deliverable**: `app/core/selectors/[feature]_selectors.py`
  - **Verify**: Functions return expected data
  - **Requirement**: [Req reference]

## Phase 2: Business Logic

- [ ] **2.1** Create services
  - **Do**: [Specific service functions from design.md]
  - **Deliverable**: `app/core/services/[feature]_services.py`
  - **Verify**: Services perform expected operations
  - **Requirement**: [Req reference]

- [ ] **2.2** Add error handling
  - **Do**: Handle [specific error cases from design.md]
  - **Deliverable**: Try/except blocks, validation, user-friendly messages
  - **Requirement**: [Req reference]

## Phase 3: API/Views

- [ ] **3.1** Create views
  - **Do**: [Specific view functions from design.md]
  - **Deliverable**: Functions in `app/core/views/web.py` or `api.py`
  - **Requirement**: [Req reference]

- [ ] **3.2** Add URL routes
  - **Do**: Add paths to `app/core/urls.py`
  - **Deliverable**: Routes accessible
  - **Verify**: URLs resolve correctly

## Phase 4: Frontend

- [ ] **4.1** Create template
  - **Do**: [Template structure from design.md]
  - **Deliverable**: `app/core/templates/core/[feature].html`
  - **Verify**: Page renders with correct layout
  - **Requirement**: [Req reference]

- [ ] **4.2** Create JavaScript module
  - **Do**: [JS functionality from design.md]
  - **Deliverable**: `app/core/static/core/js/pageModules/[feature].js`
  - **Verify**: Interactive elements work
  - **Requirement**: [Req reference]

- [ ] **4.3** Add navigation link (if needed)
  - **Do**: Add link to appropriate navbar section
  - **Deliverable**: Link in `templates/navbars/`
  - **Verify**: Navigation works

## Phase 5: WebSocket (if applicable)

- [ ] **5.1** Create consumer
  - **Do**: [Consumer from design.md]
  - **Deliverable**: `app/core/websockets/[feature]/consumer.py`
  - **Requirement**: [Req reference]

- [ ] **5.2** Add WebSocket routes
  - **Do**: Register in `app/websockets/routing.py`
  - **Deliverable**: WebSocket endpoint accessible

- [ ] **5.3** Create client-side WebSocket
  - **Do**: [Client socket from design.md]
  - **Deliverable**: `app/core/static/core/js/websockets/[feature]Socket.js`
  - **Verify**: Real-time updates work

## Phase 6: Integration

- [ ] **6.1** End-to-end test
  - **Do**: Test complete user workflow
  - **Verify**: All acceptance criteria from requirements.md pass
  - **Requirement**: All

- [ ] **6.2** Deploy check
  - **Do**: Verify deployment steps needed
  - **Note**: Python changes auto-reload; static files need `kpk git collectstatic`

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Data Layer | Not Started | 0/3 |
| 2. Business Logic | Not Started | 0/2 |
| 3. API/Views | Not Started | 0/2 |
| 4. Frontend | Not Started | 0/3 |
| 5. WebSocket | Not Started | 0/3 |
| 6. Integration | Not Started | 0/2 |

**Overall**: 0/15 tasks (0%)

---

**Status**: Draft | Approved | In Progress | Complete
