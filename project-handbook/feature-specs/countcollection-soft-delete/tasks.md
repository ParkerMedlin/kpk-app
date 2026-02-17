# Count Collection Soft Delete Tasks

## Overview

Implementation tasks for count collection soft delete. Work through sequentially, marking complete as you go.

**Requirements**: See `requirements.md`
**Design**: See `design.md`

## Phase 1: Data Layer

- [ ] **1.1** Add `is_hidden` field to CountCollectionLink (USER ACTION: run migration)
  - **Do**: Add `is_hidden = models.BooleanField(default=False)` to `CountCollectionLink` in `app/core/models.py`. Run `makemigrations`.
  - **Deliverable**: New migration file
  - **Verify**: `python manage.py makemigrations` succeeds
  - **Requirement**: AC-1

- [ ] **1.2** Update `get_count_status_rows` SQL to include hidden-collection flag
  - **Do**: In `app/core/selectors/inventory_selectors.py`, modify the `get_count_status_rows` SQL to LEFT JOIN `core_countcollectionlink` on `collection_id` and return `is_hidden_collection` boolean for each row. Join from both `latest_blend_count` and `latest_component_count` CTEs to check if the selected count record's collection is hidden.
  - **Deliverable**: Updated SQL query returning `is_hidden_collection` in each row dict
  - **Requirement**: AC-6

## Phase 2: WebSocket Layer

- [ ] **2.1** Replace delete with hide in consumer
  - **Do**: In `app/core/consumers.py`:
    - Rename `delete_collection` method → `hide_collection`
    - Replace `delete_collection_link` DB method: instead of `.delete()`, set `is_hidden=True` and `.save(update_fields=['is_hidden'])`
    - Rename method to `hide_collection_link`
    - Change event type from `collection_deleted` to `collection_hidden`
    - Update `receive()` routing: `'hide_collection'` action maps to `self.hide_collection(data)`
    - Add `collection_hidden` event handler (forward with `forward_to_sender=True`)
  - **Deliverable**: Hide action works via WebSocket, broadcasts `collection_hidden`
  - **Requirement**: AC-1

- [ ] **2.2** Add restore action to consumer
  - **Do**: In `app/core/consumers.py`:
    - Add `restore_collection` method: get collection_id from data, call `restore_collection_link`, broadcast `collection_restored` event with collection metadata (name, record_type, link_order)
    - Add `restore_collection_link` DB method: set `is_hidden=False`, save, return dict with collection_name, record_type, link_order
    - Add `collection_restored` event handler (forward with `forward_to_sender=True`)
    - Update `receive()` routing: `'restore_collection'` action maps to `self.restore_collection(data)`
  - **Deliverable**: Restore action works via WebSocket, broadcasts `collection_restored`
  - **Requirement**: AC-4

- [ ] **2.3** Update WebSocket JS client
  - **Do**: In `app/core/static/core/js/objects/webSocketObjects.js`:
    - Rename `deleteCollection()` → `hideCollection()` (sends `action: 'hide_collection'`)
    - Add `restoreCollection(collectionId)` method (sends `action: 'restore_collection'`)
    - Add `collection_hidden` and `collection_restored` to callback map in constructor
    - Route `collection_hidden` to `removeCollectionUI` in `initEventListeners` (same visual effect as old delete)
    - Route `collection_restored` to `addCollectionUI` in `initEventListeners`
  - **Deliverable**: JS WebSocket client supports hide/restore actions and events
  - **Requirement**: AC-1, AC-4

## Phase 3: Views & Routes

- [ ] **3.1** Filter active collection links to exclude hidden
  - **Do**: In `app/core/views/web.py` `display_count_collection_links`, change `.objects.all()` to `.objects.filter(is_hidden=False)`.
  - **Deliverable**: Active page only shows non-hidden collections
  - **Requirement**: AC-1

- [ ] **3.2** Add hidden collection links view
  - **Do**: In `app/core/views/web.py`, add `display_hidden_collection_links` view with `@login_required` and `@staff_member_required` decorators. Query `CountCollectionLink.objects.filter(is_hidden=True).order_by('-created_at')`. Render `hiddencountcollectionlinks.html`.
  - **Deliverable**: Staff-only view returning hidden collections
  - **Requirement**: AC-3

- [ ] **3.3** Pass `is_hidden` into count list view context
  - **Do**: In `app/core/views/web.py` `display_count_list`, after fetching `count_list_data`, look up the CountCollectionLink by `count_list_id` and add `is_hidden` to the template context.
  - **Deliverable**: Count list template has access to `is_hidden` boolean
  - **Requirement**: AC-2, AC-3

- [ ] **3.4** Add URL routes and clean up old delete route
  - **Do**: In `app/core/urls.py`:
    - Add `path('hidden-count-collection-links/', web.display_hidden_collection_links, name='hidden-count-collection-links')`
    - Remove `path('delete-count-collection-links/', ...)` route
  - **Deliverable**: New route accessible, old delete route removed
  - **Requirement**: AC-3, AC-5

- [ ] **3.5** Remove `delete_count_collection_links` service function
  - **Do**: In `app/core/services/inventory_services.py`, remove the `delete_count_collection_links` function (lines 1267-1288). It is no longer called — the hide action goes through WebSocket now.
  - **Deliverable**: Dead code removed
  - **Requirement**: AC-1

## Phase 4: Frontend — Active Collections Page

- [ ] **4.1** Update collection links template for hide action
  - **Do**: In `app/core/templates/core/inventorycounts/countcollectionlinks.html`:
    - Replace `fa-trash-alt` icon with `fa-eye-slash`
    - Replace `deleteCountLinkButton` class with `hideCountLinkButton`
    - Replace `btn-outline-danger` with `btn-outline-secondary`
    - Add staff-only link to hidden collections page (between create buttons and table):
      ```html
      {% if user.is_staff %}
      <div class="text-center my-2">
          <a href="{% url 'hidden-count-collection-links' %}" class="btn btn-outline-secondary btn-sm">
              <i class="fa-solid fa-eye-slash"></i> View Hidden Collections
          </a>
      </div>
      {% endif %}
      ```
  - **Deliverable**: Hide button and navigation link visible
  - **Requirement**: AC-1, AC-5

- [ ] **4.2** Update collection links JS for hide action
  - **Do**: In `app/core/static/core/js/pageModules/countcollectionlinks.js`, update button selector from `.deleteCountLinkButton` to `.hideCountLinkButton`. The `CountCollectionLinksPage` object likely references this class — find and update. The WebSocket call changes from `deleteCollection()` to `hideCollection()`.
  - **Deliverable**: Clicking hide button sends `hide_collection` via WebSocket
  - **Requirement**: AC-1

## Phase 5: Frontend — Count List Page (Soft Transition)

- [ ] **5.1** Add archived banner to count list template
  - **Do**: In `app/core/templates/core/inventorycounts/countlist.html`, add a dismissible alert banner below the header when `is_hidden` is true:
    ```html
    {% if is_hidden %}
    <div id="archivedBanner" class="alert alert-warning alert-dismissible fade show" role="alert">
        This count list has been archived.
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endif %}
    ```
  - **Deliverable**: Banner shows on archived count lists
  - **Requirement**: AC-2

- [ ] **5.2** Add read-only mode to count list template
  - **Do**: In `app/core/templates/core/inventorycounts/countlist.html`, when `is_hidden` is true:
    - Add `disabled` attribute to all count entry buttons (`button.containers`)
    - Add `readonly` to comment textareas
    - Add `disabled` to location selectors and counted checkboxes
    - Hide the "Add Item" button row
    - Hide the discard button cells
    - Hide the qty refresh buttons
  - **Deliverable**: Archived count lists are read-only
  - **Requirement**: AC-3

- [ ] **5.3** Replace deletion modal with banner in count list JS
  - **Do**: In `app/core/static/core/js/pageModules/countList.js`:
    - Replace the `onCollectionDeleted` callback: instead of showing a blocking modal and disconnecting the WebSocket, show a dismissible Bootstrap alert banner (inject into DOM above the table)
    - Update the event name check from `collection_deleted` to `collection_hidden`
    - Do NOT call `thisCountListWebSocket.disconnect()` — user keeps their WebSocket connection
    - Remove or keep the modal creation code (it becomes dead code — remove it)
  - **Deliverable**: Active users see a banner, not a modal, and can keep editing
  - **Requirement**: AC-2

## Phase 6: Frontend — Hidden Collections Page

- [ ] **6.1** Create hidden collections template
  - **Do**: Create `app/core/templates/core/inventorycounts/hiddencountcollectionlinks.html`:
    - Extends `base.html`
    - Title: "Hidden Count Collections"
    - Back link to active collection links page
    - Table with columns: Collection Name (clickable link to count list), Created Date, Restore button
    - Each collection name links to `/core/count-list/display/?listId={id}&recordType={type}`
    - Restore button: `<i class="fa-solid fa-rotate-left btn btn-outline-success restoreCountLinkButton" collectionlinkitemid="{{ item.id }}"></i>`
    - Empty state message when no hidden collections
    - Loads `hiddenCountCollectionLinks.js`
  - **Deliverable**: Hidden collections page renders with restore buttons and clickable links
  - **Requirement**: AC-3, AC-4

- [ ] **6.2** Create hidden collections JS page module
  - **Do**: Create `app/core/static/core/js/pageModules/hiddenCountCollectionLinks.js`:
    - Import and instantiate `CountCollectionWebSocket` with callbacks
    - On `.restoreCountLinkButton` click: get `collectionlinkitemid`, call `ws.restoreCollection(id)`
    - On `collection_restored` event: remove the row from the hidden table
    - On `collection_hidden` event: add a row to the hidden table (real-time update when another user hides a collection)
  - **Deliverable**: Restore buttons work, real-time updates on the hidden page
  - **Requirement**: AC-3, AC-4

## Phase 7: Count Status Report

- [ ] **7.1** Update count status template with hidden indicator
  - **Do**: In `app/core/templates/core/inventorycounts/count_status.html`:
    - In each `<tr>`, check `item.is_hidden_collection`
    - When true, add `<i class="fa-solid fa-eye-slash text-muted" title="From archived collection"></i>` next to the item code
  - **Deliverable**: Archived-collection records are visually flagged
  - **Requirement**: AC-6

## Phase 8: Cleanup

- [ ] **8.1** Verify `CountCollectionLinksPage` object references
  - **Do**: Check `app/core/static/core/js/objects/pageObjects.js` for references to `deleteCountLinkButton` class and `deleteCollection` method. Update any references to match the new `hideCountLinkButton` class and `hideCollection` method.
  - **Deliverable**: No broken JS references
  - **Requirement**: AC-1

---

## Progress

| Phase | Status | Tasks Complete |
|-------|--------|----------------|
| 1. Data Layer | Not Started | 0/2 |
| 2. WebSocket Layer | Not Started | 0/3 |
| 3. Views & Routes | Not Started | 0/5 |
| 4. Active Collections Page | Not Started | 0/2 |
| 5. Count List Page | Not Started | 0/3 |
| 6. Hidden Collections Page | Not Started | 0/2 |
| 7. Count Status Report | Not Started | 0/1 |
| 8. Cleanup | Not Started | 0/1 |

**Overall**: 0/19 tasks (0%)

---

**Status**: Draft
