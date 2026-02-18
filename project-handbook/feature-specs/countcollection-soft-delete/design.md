# Count Collection Soft Delete Design

## Overview

Replace the hard-delete of CountCollectionLink with an `is_hidden` boolean field. Hiding a collection removes it from the active list but preserves the record and its associated count data. A new staff-only page lists hidden collections with restore and read-only viewing capabilities. All hide/restore actions broadcast via WebSocket so every connected client updates in real time.

## Affected Components

### Existing Files to Modify

| File | Changes |
|------|---------|
| `app/core/models.py` | Add `is_hidden` field to CountCollectionLink |
| `app/core/consumers.py` | Rename `delete_collection` → `hide_collection`, add `restore_collection` action, change DB operation from `.delete()` to `is_hidden=True` |
| `app/core/views/web.py` | Filter active links to `is_hidden=False`, add `display_hidden_collection_links` view (staff only), pass `is_hidden` flag into count list context |
| `app/core/services/inventory_services.py` | Remove `delete_count_collection_links` function (replaced by WebSocket hide) |
| `app/core/selectors/inventory_selectors.py` | Modify `get_count_status_rows` SQL to join CountCollectionLink and return `is_hidden` flag |
| `app/core/urls.py` | Add route for hidden collections page, remove `delete-count-collection-links/` route |
| `app/core/templates/core/inventorycounts/countcollectionlinks.html` | Replace trash icon semantics with hide, add staff-only link to hidden collections page |
| `app/core/templates/core/inventorycounts/countlist.html` | Add archived banner, support read-only mode when `is_hidden=True` |
| `app/core/templates/core/inventorycounts/count_status.html` | Add visual indicator column/badge for hidden-collection records |
| `app/core/static/core/js/objects/webSocketObjects.js` | Rename `deleteCollection` → `hideCollection`, add `restoreCollection` method, rename UI handler to `removeCollectionUI` (unchanged logic), add `collection_hidden`/`collection_restored` event types |
| `app/core/static/core/js/pageModules/countcollectionlinks.js` | Update button class and handler for hide action |
| `app/core/static/core/js/pageModules/countList.js` | Replace deletion modal with dismissible banner, keep WebSocket connected |

### New Files to Create

| File | Purpose |
|------|---------|
| `app/core/templates/core/inventorycounts/hiddencountcollectionlinks.html` | Staff-only page listing hidden collections with restore buttons and links to read-only count views |
| `app/core/static/core/js/pageModules/hiddenCountCollectionLinks.js` | Page module for hidden collections page: restore button handlers, WebSocket event handling |

## Data Model

### Model Changes

```python
# In CountCollectionLink:
is_hidden = models.BooleanField(default=False)
```

No new models needed. No changes to BlendCountRecord, BlendComponentCountRecord, or WarehouseCountRecord.

### Migration

One migration: add `is_hidden` boolean field with `default=False` to `core_countcollectionlink`. All existing rows get `is_hidden=False` (no data loss, no backfill needed).

## URL Routes

```python
# New route
path('hidden-count-collection-links/', web.display_hidden_collection_links, name='hidden-count-collection-links'),

# Remove this route (action now handled via WebSocket)
# path('delete-count-collection-links/', inventory_services.delete_count_collection_links, ...)
```

## Layer Design

### Views (web.py)

**Modified — `display_count_collection_links`:**
```python
def display_count_collection_links(request):
    count_collection_links = CountCollectionLink.objects.filter(is_hidden=False).order_by('link_order')
    # ... rest unchanged
```

**New — `display_hidden_collection_links`:**
```python
@login_required
@staff_member_required
def display_hidden_collection_links(request):
    hidden_links = CountCollectionLink.objects.filter(is_hidden=True).order_by('-created_at')
    return render(request, 'core/inventorycounts/hiddencountcollectionlinks.html', {
        'hidden_collection_links': hidden_links,
    })
```

**Modified — `display_count_list`:**
```python
def display_count_list(request):
    # After fetching count_list data, also check if collection is hidden
    count_list_link = CountCollectionLink.objects.get(pk=count_list_id)
    context['is_hidden'] = count_list_link.is_hidden
    # ... rest unchanged
```

### Consumer (consumers.py)

**Renamed action — `hide_collection` (was `delete_collection`):**
```python
async def hide_collection(self, data):
    collection_id = data['collection_id']
    await self.hide_collection_link(collection_id)
    event_payload = {
        'type': 'collection_hidden',
        'collection_id': collection_id,
        'sender_channel_name': self.channel_name
    }
    await self.channel_layer.group_send(self.group_name, event_payload)
    await persist_event(self.redis_key, 'collection_hidden', {'collection_id': collection_id})
```

**New action — `restore_collection`:**
```python
async def restore_collection(self, data):
    collection_id = data['collection_id']
    collection_data = await self.restore_collection_link(collection_id)
    event_payload = {
        'type': 'collection_restored',
        'collection_id': collection_id,
        'collection_name': collection_data['collection_name'],
        'record_type': collection_data['record_type'],
        'link_order': collection_data['link_order'],
        'sender_channel_name': self.channel_name
    }
    await self.channel_layer.group_send(self.group_name, event_payload)
    await persist_event(self.redis_key, 'collection_restored', {...})
```

**New DB operations:**
```python
@database_sync_to_async
def hide_collection_link(self, collection_id):
    collection = CountCollectionLink.objects.get(id=collection_id)
    collection.is_hidden = True
    collection.save(update_fields=['is_hidden'])

@database_sync_to_async
def restore_collection_link(self, collection_id):
    collection = CountCollectionLink.objects.get(id=collection_id)
    collection.is_hidden = False
    collection.save(update_fields=['is_hidden'])
    return {
        'collection_name': collection.collection_name,
        'record_type': collection.record_type,
        'link_order': collection.link_order,
    }
```

**New event handlers:**
```python
async def collection_hidden(self, event):
    await self._forward_collection_event(event, forward_to_sender=True)

async def collection_restored(self, event):
    await self._forward_collection_event(event, forward_to_sender=True)
```

**Action routing update in `receive`:**
```python
elif action == 'hide_collection':
    await self.hide_collection(data)
elif action == 'restore_collection':
    await self.restore_collection(data)
```

### Selectors (inventory_selectors.py)

**Modified — `get_count_status_rows`:**

Add a CTE that identifies which items have their latest count record in a hidden collection:

```sql
hidden_collection_items AS (
    SELECT DISTINCT b.item_code
    FROM core_blendcountrecord b
    INNER JOIN core_countcollectionlink ccl
        ON ccl.collection_id = b.collection_id
        AND ccl.is_hidden = TRUE
    -- similar UNION for component records
)
```

Then add `is_hidden_collection` boolean to the final SELECT:
```sql
SELECT rr.*,
    CASE WHEN hci.item_code IS NOT NULL THEN TRUE ELSE FALSE END AS is_hidden_collection
FROM report_rows rr
LEFT JOIN hidden_collection_items hci ON hci.item_code = rr.item_code
```

The service function `build_count_status_display` passes this through unchanged. The template uses `item.is_hidden_collection` for the visual indicator.

## Frontend

### Template — `countcollectionlinks.html`

Changes:
- Replace `fa-trash-alt` + `deleteCountLinkButton` class with `fa-eye-slash` + `hideCountLinkButton` class
- Add staff-only link to hidden collections page (after the create buttons block):
```html
{% if user.is_staff %}
    <div class="text-center my-2">
        <a href="{% url 'hidden-count-collection-links' %}" class="btn btn-outline-secondary btn-sm">
            <i class="fa-solid fa-eye-slash"></i> View Hidden Collections
        </a>
    </div>
{% endif %}
```

### Template — `hiddencountcollectionlinks.html` (new)

Structure:
```
hiddencountcollectionlinks.html
├── extends base.html
├── Table of hidden collections
│   ├── Collection name (clickable link to read-only count list view)
│   ├── Created date
│   └── Restore button (sends WebSocket message)
└── loads hiddenCountCollectionLinks.js
```

Each collection row links to `/core/count-list/display/?listId={id}&recordType={type}` — the same count list view, but the template will detect `is_hidden=True` and render read-only.

### Template — `countlist.html`

Changes:
- Add archived banner at top (conditionally shown when `is_hidden` context var is true):
```html
{% if is_hidden %}
<div id="archivedBanner" class="alert alert-warning alert-dismissible fade show" role="alert">
    This count list has been archived.
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
{% endif %}
```
- When `is_hidden` is true: disable all input fields, hide the "Add Item" button, hide discard buttons, make the form read-only. This is handled by adding a CSS class to the table and conditional template logic.

### Template — `count_status.html`

Add visual indicator for hidden-collection rows. Approach: add an `<i class="fa-solid fa-eye-slash text-muted">` icon next to the item code when `item.is_hidden_collection` is true.

### JavaScript — `webSocketObjects.js`

```javascript
// Rename method
hideCollection(collectionId) {
    this.socket.send(JSON.stringify({
        action: 'hide_collection',
        collection_id: collectionId
    }));
}

// New method
restoreCollection(collectionId) {
    this.socket.send(JSON.stringify({
        action: 'restore_collection',
        collection_id: collectionId
    }));
}
```

Add `collection_hidden` and `collection_restored` to callback map and event routing. `collection_hidden` calls `removeCollectionUI` (same visual effect as old delete). `collection_restored` calls `addCollectionUI` (reuses existing logic to insert a row).

Keep `deleteCollection` temporarily as an alias for `hideCollection` to avoid breaking anything during transition, remove once all callers are updated.

### JavaScript — `countcollectionlinks.js`

- Change button class selector from `.deleteCountLinkButton` to `.hideCountLinkButton`
- Call `hideCollection()` instead of `deleteCollection()` on WebSocket

### JavaScript — `countList.js`

Replace the deletion modal behavior:
- On `collection_hidden` event matching this list's ID: show a dismissible Bootstrap alert banner instead of a blocking modal
- Do NOT disconnect the CountListWebSocket — user can continue entering counts
- Do NOT redirect the user — they stay on the page until they navigate away

### JavaScript — `hiddenCountCollectionLinks.js` (new)

```javascript
// Page module for hidden collections page
// - Connects to CountCollectionWebSocket (global context)
// - Restore button click → ws.restoreCollection(id)
// - On collection_restored event → remove row from table
// - On collection_hidden event → add row to table (real-time update if another staff member hides a collection)
```

## WebSocket Event Summary

| Event | Replaces | Broadcast To | Active Links Page | Count List Page | Hidden Links Page |
|-------|----------|--------------|-------------------|-----------------|-------------------|
| `collection_hidden` | `collection_deleted` | Global group | Remove row | Show banner | Add row |
| `collection_restored` | (new) | Global group | Add row | N/A | Remove row |

Both events use `forward_to_sender=True` so the originating client also updates its UI.

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Hide non-existent collection | Consumer catches `ObjectDoesNotExist`, logs warning, no broadcast |
| Restore non-existent collection | Consumer catches `ObjectDoesNotExist`, logs warning, no broadcast |
| Non-staff user accesses hidden page | `@staff_member_required` decorator returns 302 to login |
| Non-staff user sends restore WebSocket action | Consumer ignores (no user auth check on WebSocket currently — matches existing pattern for delete) |

Note: The existing system does not enforce staff-only on WebSocket actions (delete is available to anyone who can reach the page). This design maintains that pattern. The staff restriction is enforced at the view/template layer — only staff see the hide button and hidden collections page.

## Requirements Traceability

| Requirement | Addressed By |
|-------------|--------------|
| AC-1: Hide replaces delete | `is_hidden` field, consumer `hide_collection` action, `collection_hidden` event |
| AC-2: Active user soft transition | `countList.js` banner, keep WebSocket connected, no redirect |
| AC-3: Hidden collections page | `display_hidden_collection_links` view, `hiddencountcollectionlinks.html` template, clickable links to read-only count list |
| AC-4: Restore action | Consumer `restore_collection` action, `collection_restored` event, staff-only UI |
| AC-5: Navigation | Staff-only "View Hidden Collections" link on `countcollectionlinks.html` |
| AC-6: Count status report | Modified SQL in `get_count_status_rows`, `is_hidden_collection` flag, icon in template |

---

**Status**: Draft
