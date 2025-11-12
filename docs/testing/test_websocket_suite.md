# Websocket Test Suite

## Prerequisites

Install the Python dependencies and the Playwright-managed Edge build once per
machine:

```bash
python -m pip install -r requirements.txt
python -m playwright install --force msedge
```

These commands seed the virtual environment with pytest, fakeredis, Playwright,
and the browser binary needed for the end-to-end check.

## Running the suite

Execute all websocket-focused tests (backend + browser):

```bash
python -m pytest -k websockets
```

To target the Playwright case on its own:

```bash
python -m pytest tests/websockets/e2e -k websockets -rs
```

## Coverage overview

- `tests/websockets/test_base_consumer.py`
  - Confirms Redis payload sanitisation and persistence helpers.
  - Verifies `send_to_group` broadcasts with sender metadata and optional
    Redis logging.
- `tests/websockets/test_count_list_consumer.py`
  - Asserts initial state replay on connect.
  - Validates `update_count` persistence and channel-layer fan-out using an
    in-memory layer.
  - Ensures sender echo suppression when forwarding events.
- `tests/websockets/prodverse/test_carton_print_consumer.py`
  - Covers Redis set snapshots and event log replay for the carton print
    feature.
  - Confirms `carton_print_update` broadcasts persist to Redis and update the
    per-line production set.
  - Verifies sender suppression mirrors the shared mixin behaviour.
- `tests/websockets/prodverse/test_spec_sheet_consumer.py`
  - Validates spec sheet state replay, Redis persistence, and legacy key
    migration.
  - Ensures updates fan out via the channel layer while suppressing sender
    echoes.
- `tests/websockets/core/test_blend_schedule_consumer.py`
  - Seeds Redis snapshots for desk contexts and verifies initial-state replay.
  - Confirms sender suppression and context-aware fan-out (desk vs. aggregate
    routes) for legacy + refactored broadcast paths.
- `tests/websockets/e2e/test_frontend_base_socket.py`
  - Loads `BaseSocket.js` in headless Edge and checks status transitions,
    sender-token suppression, and outbound message hygiene.
- `tests/websockets/e2e/test_carton_print_socket.py`
  - Exercises the new `CartonPrintSocket` module with a mocked browser
    websocket, asserting initial snapshot handling, live updates, and outbound
    toggle payloads.
- `tests/websockets/e2e/test_spec_sheet_socket.py`
  - Exercises `SpecSheetSocket` with a mocked browser websocket, confirming
    initial snapshot hydration, live updates, and outbound state broadcasts.
- `tests/websockets/e2e/test_blend_schedule_socket.py`
  - Exercises the `BlendScheduleSocket` client across add/edit/delete flows:
    new blend rows, lot edits, status toggles, tank changes, desk reorders,
    schedule notes, and desk-to-desk moves.

## Notes

- The Playwright fixture retries Edge in `--headless=new` mode so modern Edge
  builds work without extra flags; if the browser still cannot launch, pytest
  will skip the E2E case with the recorded reason.
- No Node.js tooling is required; everything runs through the Python virtual
  environment seeded via `requirements.txt`.
