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
CARTON_SOCKET_PATH = (
    PROJECT_ROOT
    / "app/prodverse/static/prodverse/js/websockets/cartonPrintSocket.js"
)

BASE_SOCKET_DATA_URL = _to_data_url(BASE_SOCKET_PATH)
STATE_CACHE_DATA_URL = _to_data_url(STATE_CACHE_PATH)
HELPERS_DATA_URL = _to_data_url(HELPERS_PATH)

_carton_socket_source = CARTON_SOCKET_PATH.read_text(encoding="utf-8")
_carton_socket_source = _carton_socket_source.replace(
    "../../../shared/js/websockets/BaseSocket.js", BASE_SOCKET_DATA_URL
)
_carton_socket_source = _carton_socket_source.replace(
    "../../../shared/js/websockets/StateCache.js", STATE_CACHE_DATA_URL
)
_carton_socket_source = _carton_socket_source.replace(
    "../../../shared/js/websockets/helpers.js", HELPERS_DATA_URL
)
CARTON_SOCKET_DATA_URL = (
    "data:text/javascript;base64,"
    + base64.b64encode(_carton_socket_source.encode("utf-8")).decode("ascii")
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


def _bootstrap_carton_socket(page):
    page.add_init_script(MOCK_WEBSOCKET_SCRIPT)
    page.goto("about:blank")
    page.evaluate(
        """async ({ moduleUri }) => {
            const module = await import(moduleUri);
            window.__CartonPrintSocket = module.CartonPrintSocket;
        }""",
        {"moduleUri": CARTON_SOCKET_DATA_URL},
    )


def test_carton_print_socket_replays_and_sends(edge_page):
    page = edge_page
    _bootstrap_carton_socket(page)

    page.evaluate(
        """() => {
            window.__statuses = [];
            window.__updates = [];
            window.__cartonSocket = new window.__CartonPrintSocket({
                prodLine: 'HX',
                resolveUrl: () => 'ws://test/ws/carton-print/HX/',
                onStatusChange: (status) => window.__statuses.push(status),
                onCartonPrintUpdate: (payload) => window.__updates.push(payload),
            });
        }"""
    )

    page.evaluate("() => window.__mockSockets[0].emit('open', { type: 'open' })")
    statuses = page.evaluate("() => window.__statuses")
    assert statuses[0] == "connecting"
    assert "connected" in statuses

    page.evaluate(
        """() => window.__mockSockets[0].emit(
            'message',
            { data: JSON.stringify({
                type: 'initial_state',
                events: [{
                    event: 'carton_print_update',
                    data: { itemCode: 'PN123', isPrinted: true }
                }]
            }) }
        )"""
    )

    updates = page.evaluate("() => window.__updates")
    assert updates
    assert updates[0]["itemCode"] == "PN123"
    assert updates[0]["isPrinted"] is True

    page.evaluate(
        """() => window.__mockSockets[0].emit(
            'message',
            { data: JSON.stringify({
                type: 'carton_print_update',
                itemCode: 'PN999',
                isPrinted: false
            }) }
        )"""
    )

    updates = page.evaluate("() => window.__updates")
    assert len(updates) == 2
    assert updates[1]["itemCode"] == "PN999"

    sent = page.evaluate(
        """() => window.__cartonSocket.toggleItem('PN777', true)"""
    )
    assert sent is True

    sent_payloads = page.evaluate(
        """() => window.__mockSockets[0].sentMessages"""
    )
    assert sent_payloads
    payload = json.loads(sent_payloads[-1])
    assert payload["itemCode"] == "PN777"
    assert payload["isPrinted"] is True
    assert "senderToken" in payload
    logger.info(
        "CartonPrintSocket e2e handled %d updates before sending payload %s",
        len(updates),
        payload,
    )
