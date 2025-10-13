# Count List WebSocket Report

Updated October 8, 2025.

## Overview
- Count list edits originate in the browser, travel through `sendCountRecordChange`, and reach Django Channels consumers before rebroadcasting to all viewers.
- Add and delete operations reuse the same message loop; metadata changes ride the `CountCollection` socket so list links and detail pages stay aligned.

## High-Level Flow
1. Browser updates a row, recalculates totals, and sends the payload through `sendCountRecordChange` (`app/core/static/core/js/objects/pageObjects.js:1117`).
2. `CountListConsumer` persists the change then sends a `count_updated` broadcast to the list group (`app/core/consumers.py:49-133`).
3. `CountListWebSocket` listeners merge the payload back into the DOM and refresh containers when the modal is open (`app/core/static/core/js/objects/webSocketObjects.js:273-420`).
4. Add/delete actions follow the same loop via `add_count` / `delete_count`, updating the database and announcing `count_added` / `count_deleted` events.
5. Collection-level metadata edits use `CountCollectionWebSocket` and the `CountCollectionConsumer` broadcast path to keep headers in sync.

## Frontend Touchpoints
- `CountListWebSocket`: manages connection lifecycle and DOM reconciliation; exposes the instance via `window.thisCountListWebSocket`.
- `CountListPage`: wires UI handlers, delegates container work to `ContainerManager`, mirrors broadcast data when cloning rows.
- `ContainerManager`: caches containers, performs synchronous fetches, and relays container actions through the same socket endpoint.
- `AddCountListItemModal`: autocomplete modal that pushes new records with `add_count`, relying on URL parameters for context.
- `CountCollectionWebSocket`: runs on links and detail pages to refresh headers and staff controls in real time.

## Backend Channels and Services
- `CountListConsumer` trusts client payloads for variance and containers, and updates `ItemLocation` when provided (`app/core/consumers.py:49-185`).
- `add_count_to_db` returns the payload shape the frontend expects but assumes a matching `ItemLocation`; missing rows raise exceptions (`app/core/consumers.py:201-265`).
- `delete_count_from_db` trims `CountCollectionLink.count_id_list` without guarding against stale IDs or duplicates.
- `CountCollectionConsumer` manages rename/delete/reorder broadcasts; automated list generation lives in `inventory_services.create_automated_countlist`.

## Pain Points
- Heavy reliance on global instances (`window.thisCountListWebSocket`, `window.countListPage`, `window.containerManager`) makes sequencing brittle.
- `ContainerManager` performs synchronous AJAX calls even though socket payloads already contain container data.
- Duplicate event bindings between `setUpEventListeners` and `_setupSingleRowEventHandlers` risk double submissions for dynamically inserted rows.
- Message schemas vary between actions, forcing defensive code that unwraps payloads differently.
- DOM updates depend on cloning existing nodes and mutating them, complicating UI changes.
- Backend assumes companion records exist; missing `ItemLocation` rows can trigger socket exceptions.

## Standardization Opportunities
- Define and enforce a JSON contract for socket messages, including containers, so synchronous container fetches can be removed.
- Extract reusable client templates for count rows or container rows, letting `addCountRecordToUI` render from data instead of cloning DOM fragments.
- Introduce a controller module that owns shared websocket and page state instead of exposing globals.

## Suggested Next Steps
1. Formalize the message schema and validate it on both the browser and consumer sides.
2. Replace synchronous container fetches with socket-supplied data once the contract is solid.
3. Refactor row rendering to use a template-based approach, enabling future server-side templating options.
4. Wrap websocket setup and shared state in a dedicated module so other scripts import it instead of touching globals.
