# WebSocket Implementation Guide for KPK App

## Overview

Our real-time features are built on top of Django Channels with Redis-backed
state persistence and a shared JavaScript client toolkit. The Count List
refactor established the reference implementation; Count Collection and the
remaining websocket features should follow the same patterns as they migrate to
the new layout.

This document captures the architecture, conventions, and quality gates that
every websocket feature must respect moving forward.

## Shared Architecture Snapshot

- **Backend base module**: `app/websockets/base_consumer.py` centralises Redis
  utilities, payload sanitisation, and the `RedisBackedConsumer` mixin used by
  every Channels consumer.
- **Feature packages**: each feature lives under its app namespace, e.g.
  `app/core/websockets/count_list/consumer.py`,
  `app/prodverse/websockets/carton_print/consumer.py`, or
  `app/prodverse/websockets/pull_status/consumer.py`. Packages export their routes via
  a local `routes.py` so the ASGI loader stays flat.
- **Routing aggregator**: `app/websockets/routing.py` imports every feature’s
  `websocket_routes` list and exposes a single `websocket_routes` iterable for
  `app/asgi.py`.
- **Frontend shared modules**:
  `app/static/shared/js/websockets/{BaseSocket.js,StateCache.js,helpers.js}`
  contain transport logic, state snapshots, and URL utilities.
- **Frontend feature clients**: app-specific bundles live under
  `app/<django_app>/static/<django_app>/js/websockets/` with an `index.js`
  barrel that re-exports public clients.
- **Regression tests**: `tests/websockets/` (pytest + Playwright) exercise both
  the backend consumers and the shared frontend helpers; see
  `docs/testing/test_websocket_suite.md`.

## Backend Consumers

### Redis-backed base layer

`RedisBackedConsumer` wraps Channels’ `AsyncWebsocketConsumer` lifecycle with
Redis persistence helpers:

- `persist_event(event_type, payload, limit=STATE_EVENT_LIMIT)` stores the most
  recent events (default cap: 25) under `self.redis_key`.
- `load_state()` returns the persisted events; pair it with
  `sanitize_events(...)` before sending them to the client.
- `send_to_group(message_type, payload, *, persist=False, persist_event_type=None)`
  wraps `channel_layer.group_send`, injects `sender_channel_name` for server-side
  echo suppression, and optionally logs the event to Redis.
- `is_sender(event)` compares the inbound event’s `sender_channel_name` with the
  current connection so you can drop self-broadcasts.

Always set `self.group_name` and `self.redis_key` in `connect`. Count List
illustrates the pattern:

```python
class CountListConsumer(RedisBackedConsumer, AsyncWebsocketConsumer):
    async def connect(self):
        self.count_list_id = self.scope["url_route"]["kwargs"]["count_list_id"]
        self.group_name = f"count_list_unique_{self.count_list_id}"
        self.redis_key = f"count_list:{self.count_list_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._send_initial_state()

    async def _send_initial_state(self):
        events = await self.load_state()
        sanitized = sanitize_events(events)
        if sanitized:
            await self.send_json(
                {"type": "initial_state", "events": sanitized},
                dumps_kwargs={"default": json_default},
            )
```

### Feature package layout

When migrating a legacy consumer:

1. Create `app/<django_app>/websockets/<feature>/__init__.py`.
2. Move the consumer to `consumer.py`, importing helpers from
   `app.websockets.base_consumer`.
3. Add a `routes.py` that exports a `websocket_routes` list using Django’s
   `re_path` helpers.
4. Update `app/websockets/routing.py` to include the new feature’s routes.

Keep persistence key formats consistent across features (e.g.,
`f"{feature_name}:{identifier}"`) so tests can assert against predictable keys.

### Routing conventions

- Use permissive patterns (`(?P<count_list_id>.+)`) to allow UUIDs and composite
  IDs.
- Mirror a “collection + detail” signature when the feature supports both:
  include a trailing slash in routes and provide a wildcard route for optional
  contexts.
- Only expose routes through `app/websockets/routing.websocket_routes`; the ASGI
  application must import from there rather than per-feature modules.

### State persistence & sanitisation

Persist payloads in event form:

```python
await self.send_to_group(
    "count_updated",
    {"record_id": record_id, "data": data},
    persist=True,
)
```

Downstream callers must run `sanitize_payload` / `sanitize_events` to convert
datetimes, decimals, and nested structures into JSON-safe primitives. Avoid
storing full ORM instances or querysets in Redis; convert them to dicts first.

## Frontend Clients

### Shared toolkit

- `BaseSocket` handles connection lifecycle, exponential backoff, heartbeats,
  `sendIfOpen`, and sender-token filtering. Subclasses override `handleMessage`
  or hook the `onMessage` callback.
- `StateCache` mirrors the Redis snapshot semantics (FIFO window of events plus
  last-known state). Use it to replay the `initial_state` message before
  processing live events.
- `helpers.js` exports:
  - `buildWebSocketUrl(path, identifier)` for consistent endpoint generation.
  - `extractUniqueIdFromUrl(url)` for parsing composite IDs.
  - `sanitizeForJson`, `debounce`, `safeJsonParse`, and UI helpers such as
    `updateConnectionIndicator`.

### Implementing a feature client

1. Add `<Feature>Socket.js` under the appropriate `app/<app>/static/.../js/websockets/`
   directory.
2. Extend `BaseSocket`, wiring `resolveUrl` to `buildWebSocketUrl(...)` or a
   feature-specific resolver.
3. Instantiate `StateCache` to record both initial snapshots and live events.
4. Dispatch payloads to UI handlers (DOM updates, store writes, etc.).
5. Export the class from the app-level `index.js` barrel so existing page
   objects can `import { FeatureSocket } from './websockets'`.

The Count List client demonstrates these steps in
`app/core/static/core/js/websockets/countListSocket.js`: it resolves list IDs
from URL or query params, relies on `BaseSocket` for retries/heartbeats, caches
events via `StateCache`, and fans out type-specific UI updates through
`_dispatchEvent`.

### Bundling considerations

Static builds must include `app/static/shared/js/websockets/**/*` and the
feature modules under each app namespace. When adding new clients, confirm the
pipeline (Webpack/Django collectstatic) serves the shared modules or adjust
import paths accordingly.

## Identifiers, Groups, and URLs

- Derive connection identifiers from URL context or query parameters. Prefer
  explicit path segments (e.g., `/ws/count_list/{count_list_id}/`).
- Use `buildWebSocketUrl` on the frontend to enforce consistent escaping and
  trailing slash behaviour.
- Backend consumers should mirror the identifier in both `group_name` and
  `redis_key`. Example:
  - Group: `count_list_unique_{count_list_id}`
  - Redis key: `count_list:{count_list_id}`
- Reject missing or “undefined” identifiers in `connect`, closing with an
  application-specific code and logging the incident.

## Sender suppression & message hygiene

- Backend: `send_to_group` injects `sender_channel_name` automatically. Every
  event handler must call `self.is_sender(event)` and return early to avoid
  rebroadcasting to the same client.
- Frontend: `BaseSocket` issues a unique `senderToken` per client and filters
  inbound messages that carry the same token.
- Always strip bookkeeping fields (`senderToken`, `sender_channel_name`) before
  storing data in UI caches or passing it to business logic.

## Testing requirements

Run `python -m pytest -k websockets` to execute the full regression suite. The
current coverage includes:

- `tests/websockets/test_base_consumer.py`: Redis sanitation, persistence, and
  `send_to_group` behaviour.
- `tests/websockets/test_count_list_consumer.py`: Count List connect/update
  flows with `InMemoryChannelLayer` fan-out checks.
- `tests/websockets/e2e/test_frontend_base_socket.py`: headless Edge scenario
  that loads `BaseSocket.js`, validates status transitions, sender-token
  suppression, and outbound message hygiene.

Future migrations must add equivalent tests for each feature. See
`docs/testing/test_websocket_suite.md` for prerequisites and
`docs/testing/websocket_migration_test_PRD.md` for the detailed test
requirements (backend, frontend, and Playwright expectations).

## Migration checklist

1. **Backend**
   - Create the feature package and move the consumer under
     `app/<app>/websockets/<feature>/`.
   - Adopt `RedisBackedConsumer`, update `group_name`/`redis_key`, and persist
     events via `send_to_group(..., persist=True)`.
   - Expose routes in `routes.py` and aggregate them in
     `app/websockets/routing.py`.
2. **Frontend**
   - Build a `<Feature>Socket` class that extends `BaseSocket` and hydrates a
     `StateCache`.
   - Update the app-level `index.js` barrel and replace legacy imports in page
     objects.
3. **Tests**
   - Add unit coverage mirroring Count List’s patterns (Redis sanitisation,
     group routing, initial-state replay).
   - Extend the Playwright suite with a fixture-driven spec for the new client.
4. **Documentation**
   - Append the feature to `docs/testing/test_websocket_suite.md` and adjust
     this guide if new patterns emerge.

## Additional best practices

- **Logging**: continue using the `logger` per module; include identifiers in
  log messages for easier tracing.
- **Error handling**: wrap JSON parsing and serialization calls, logging errors
  and clearing Redis state if snapshots become invalid.
- **Debounce/throttle**: leverage `helpers.debounce` on high-frequency UI
  interactions to avoid flooding the websocket.
- **Authentication & permissions**: validate user access in `connect` (and
  reuse existing mixins when present) to prevent leaking data.
- **Graceful shutdown**: call `channel_layer.group_discard` in `disconnect` and
  raise `StopConsumer` to free server resources.

By applying these conventions consistently we ensure each websocket feature
shares the same resilience, observability, and test coverage that now protects
the Count List implementation.
