# Websocket Migration Test Requirements

This document defines the expectations for extending the websocket regression
suite as we migrate each legacy feature onto the new backend/Frontend
architecture.

## Scope

- Applies to all Django Channels consumers that emit websocket traffic (`core`,
  `prodverse`, and any future app).
- Applies to the shared frontend helpers (`BaseSocket`, `StateCache`, URL
  utilities) and each feature-specific client that consumes them.
- Supplements the existing suite (`tests/websockets/`); additions go in the same
  tree unless a feature requires a new top-level module.

## Baseline prerequisites

Every environment that runs the suite must:

1. Install Python dependencies via `python -m pip install -r requirements.txt`.
2. Install Playwright’s managed Edge build via
   `python -m playwright install --force msedge`.

CI jobs must provide the same steps before executing `python -m pytest -k websockets`.

## Backend consumer coverage requirements

For each migrated consumer:

1. **Sanitisation & persistence**
   - Patch out database calls (use `monkeypatch` + `fakeredis`) so the test can
     run without hitting Postgres.
   - Assert that `persist_event` (or `RedisBackedConsumer.persist_event`) records
     clean JSON payloads in Redis under the expected key.
   - Check that bad data (e.g., decimals/datetimes) is serialised via
     `json_default`.
2. **Group routing**
   - Inject an in-memory channel layer (`channels.layers.InMemoryChannelLayer`).
   - Call the consumer method directly (`update_*`, `delete_*`, etc.).
   - Intercept `channel_layer.group_send` and assert:
     - Correct group name format.
     - Expected payload shape (including presence/absence of sender metadata).
     - Optional persistence flags (`persist=True`) where required.
3. **Initial state replay**
   - Seed Redis (`fakeredis`) with the expected snapshot format.
   - Drive the consumer’s `connect` or `_send_initial_state` and confirm that
     clients receive the `initial_state` payload.
4. **Error handling**
   - For consumers that emit error messages (e.g., `_send_initial_state_error`),
     add tests that simulate failure modes and assert the proper group send or
     channel close code.

Each feature should live in its own test module (e.g.,
`tests/websockets/count_collection/test_consumer.py`) once migrated to keep
scopes clear.

## Frontend client coverage requirements

For each migrated JavaScript client:

1. **Unit-style tests (optional)**
   - If the client has logic that can be isolated (e.g., helper functions for
     payload shaping), add Jest/Vitest-style tests in
     `app/static/**/*.test.js` once a JS test runner is introduced.
2. **Playwright scenario**
   - Build a minimal HTML fixture that loads the client module and any required
     DOM scaffolding.
   - Mock the `WebSocket` global (similar to `tests/websockets/e2e/test_frontend_base_socket.py`).
   - Verify:
     - Reconnection/backoff paths (`BaseSocket` integration).
     - Sender suppression (messages with matching `senderToken` are dropped).
     - StateCache usage (initial snapshot and subsequent `recordEvent` calls).
     - Any UI side effects (DOM updates, indicator classes) via the fixture.
   - Place tests under `tests/websockets/e2e/<feature>_spec.py`.

When the client talks to a real backend endpoint in production, keep Playwright
tests mocked—do not spin up Daphne/Redis in the browser suite unless we have a
deterministic fixture.

## Extending shared helpers

- Update `tests/websockets/test_base_consumer.py` whenever
  `app/websockets/base_consumer.py` gains new behaviour (e.g., additional
  redis operations or new mixin methods).
- Add Playwright coverage for any new shared JS helper exported from
  `app/static/shared/js/websockets/*`.

## Documentation updates

When adding tests:

1. Append a short summary to `docs/testing/test_websocket_suite.md` that lists
   the new modules.
2. Note any additional prerequisites (new env vars, service containers, etc.).

## Lessons learned (Carton Print regression fixes)

- Keep async tests as native coroutines decorated with `@pytest.mark.asyncio`; do not wrap them in `asyncio.run()` or `async_to_sync` helpers, otherwise pytest-asyncio cannot coordinate the shared loop during full-suite runs.
- Explicitly re-scope Playwright fixtures to module scope and restore any temporary Windows event loop policies after the browser session exits. A lingering Proactor policy from a session-scoped fixture caused the remaining websocket tests to inherit an active loop and raise `RuntimeError: asyncio.run() cannot be called from a running event loop`.
- When you see "coroutine was never awaited" or "loop already running" errors in the websocket suite, inspect fixtures that mutate the loop policy before adjusting the tests—they are often the real source of the conflict.
- For form-centric features like spec sheets, persist the sanitised state snapshot as a single `spec_sheet_update` event (limit to the most recent entry) so consumers and the new `SpecSheetSocket` can hydrate clients consistently.
- Blend schedule sockets now share the Redis-backed event log: broadcast helpers must persist every update for each affected area (`Desk_1`, `LET_Desk`, global `all`), and the consumer deduplicates broadcasts with a short deque so legacy + scoped groups do not double-deliver events.
- Frontend migration surfaced heavy DOM coupling; the `BlendScheduleSocket` wraps the legacy UI helpers but routes transport concerns through `BaseSocket`. When wiring new modules, ensure `window.initializeBlendScheduleTooltips`, `bootstrap.Tooltip`, and lightweight jQuery shims are present in test fixtures to keep DOM-side effects deterministic.

## CI integration

- Ensure the CI job installs Playwright assets (run the install command above).
- Run `python -m pytest -k websockets --maxfail=1 --disable-warnings` as part of
  the main test pipeline.
- Consider adding a nightly job that exercises the entire suite plus any heavy
  browser fixtures if runtime becomes a concern.
