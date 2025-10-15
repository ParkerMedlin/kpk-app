import base64
import json
import logging
from pathlib import Path

import pytest

pytest.importorskip(
    "playwright.sync_api",
    reason="Playwright is required for browser websocket tests.",
)

pytestmark = [pytest.mark.websockets, pytest.mark.e2e]

logger = logging.getLogger(__name__)


def _to_data_url(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    return f"data:text/javascript;base64,{encoded}"


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASE_SOCKET_PATH = PROJECT_ROOT / "app/static/shared/js/websockets/BaseSocket.js"
STATE_CACHE_PATH = PROJECT_ROOT / "app/static/shared/js/websockets/StateCache.js"
HELPERS_PATH = PROJECT_ROOT / "app/static/shared/js/websockets/helpers.js"
SPEC_SOCKET_PATH = (
    PROJECT_ROOT
    / "app/prodverse/static/prodverse/js/websockets/specSheetSocket.js"
)

BASE_SOCKET_DATA_URL = _to_data_url(BASE_SOCKET_PATH)
STATE_CACHE_DATA_URL = _to_data_url(STATE_CACHE_PATH)
HELPERS_DATA_URL = _to_data_url(HELPERS_PATH)

_spec_socket_source = SPEC_SOCKET_PATH.read_text(encoding="utf-8")
_spec_socket_source = _spec_socket_source.replace(
    "../../../shared/js/websockets/BaseSocket.js", BASE_SOCKET_DATA_URL
)
_spec_socket_source = _spec_socket_source.replace(
    "../../../shared/js/websockets/StateCache.js", STATE_CACHE_DATA_URL
)
_spec_socket_source = _spec_socket_source.replace(
    "../../../shared/js/websockets/helpers.js", HELPERS_DATA_URL
)
SPEC_SOCKET_DATA_URL = (
    "data:text/javascript;base64,"
    + base64.b64encode(_spec_socket_source.encode("utf-8")).decode("ascii")
)

MOCK_WEBSOCKET_SCRIPT = """
(() => {
    class MockWebSocket {
        constructor(url) {
            this.url = url;
            this.readyState = MockWebSocket.CONNECTING;
            this.sentMessages = [];
            this._listeners = new Map([
                ['open', new Set()],
                ['message', new Set()],
                ['close', new Set()],
                ['error', new Set()],
            ]);
            window.__mockSockets.push(this);
        }

        addEventListener(type, handler) {
            const listeners = this._listeners.get(type);
            if (listeners) {
                listeners.add(handler);
            }
        }

        removeEventListener(type, handler) {
            const listeners = this._listeners.get(type);
            if (listeners) {
                listeners.delete(handler);
            }
        }

        send(payload) {
            this.sentMessages.push(payload);
        }

        close(code = 1000, reason = 'client closing') {
            this.readyState = MockWebSocket.CLOSED;
            this._emit('close', { code, reason });
        }

        emit(type, event = {}) {
            if (type === 'open') {
                this.readyState = MockWebSocket.OPEN;
            } else if (type === 'close') {
                this.readyState = MockWebSocket.CLOSED;
            }
            this._emit(type, event);
        }

        _emit(type, event = {}) {
            const listeners = this._listeners.get(type);
            if (!listeners) {
                return;
            }
            const payload = { ...event, target: this };
            for (const listener of Array.from(listeners)) {
                try {
                    listener.call(this, payload);
                } catch (error) {
                    console.error('MockWebSocket listener error', error);
                }
            }
        }
    }

    MockWebSocket.CONNECTING = 0;
    MockWebSocket.OPEN = 1;
    MockWebSocket.CLOSING = 2;
    MockWebSocket.CLOSED = 3;

    window.__mockSockets = [];
    window.WebSocket = MockWebSocket;
})();
"""


def _bootstrap_spec_sheet_socket(page):
    page.add_init_script(MOCK_WEBSOCKET_SCRIPT)
    page.goto("about:blank")
    page.evaluate(
        """async ({ moduleUri }) => {
            const module = await import(moduleUri);
            window.__SpecSheetSocket = module.SpecSheetSocket;
        }""",
        {"moduleUri": SPEC_SOCKET_DATA_URL},
    )


def test_spec_sheet_socket_replays_and_sends(edge_page):
    page = edge_page
    _bootstrap_spec_sheet_socket(page)

    page.evaluate(
        """() => {
            window.__states = [];
            window.__initialState = null;
            window.__socket = new window.__SpecSheetSocket({
                specId: 'PN123_PO1_2025',
                resolveUrl: () => 'ws://test/ws/spec_sheet/PN123_PO1_2025/',
                onSpecSheetUpdate: (state) => window.__states.push(state),
                onInitialState: (state) => window.__initialState = state,
            });
        }"""
    )

    page.evaluate("() => window.__mockSockets[0].emit('open', { type: 'open' })")

    page.evaluate(
        """() => window.__mockSockets[0].emit(
            'message',
            { data: JSON.stringify({
                type: 'initial_state',
                events: [{
                    event: 'spec_sheet_update',
                    data: {
                        checkboxes: { step1: true },
                        signature1: 'Initial Operator',
                        textarea: 'Initial notes'
                    }
                }]
            }) }
        )"""
    )

    initial_state = page.evaluate("() => window.__initialState")
    assert initial_state["checkboxes"]["step1"] is True
    assert initial_state["signature1"] == "Initial Operator"

    page.evaluate(
        """() => window.__mockSockets[0].emit(
            'message',
            { data: JSON.stringify({
                type: 'spec_sheet_update',
                state: {
                    checkboxes: { step1: false, step2: true },
                    signature2: 'QA',
                    textarea: 'Updated notes'
                }
            }) }
        )"""
    )

    states = page.evaluate("() => window.__states")
    assert len(states) == 1
    assert states[0]["checkboxes"]["step2"] is True
    assert states[0]["signature2"] == "QA"

    sent = page.evaluate(
        """() => {
            return window.__socket.broadcastState({
                checkboxes: { step1: true, step2: false },
                signature1: 'Final Operator'
            });
        }"""
    )
    assert sent is True

    sent_payloads = page.evaluate(
        """() => window.__mockSockets[0].sentMessages"""
    )
    assert sent_payloads
    payload = json.loads(sent_payloads[-1])
    assert payload["state"]["checkboxes"]["step1"] is True
    assert payload["state"]["signature1"] == "Final Operator"
    assert "senderToken" in payload
    logger.info(
        "SpecSheetSocket replayed %s, handled %d updates, and sent payload %s",
        initial_state,
        len(states),
        payload,
    )
