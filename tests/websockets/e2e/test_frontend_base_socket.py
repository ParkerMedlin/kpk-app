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


BASE_SOCKET_PATH = (
    Path(__file__)
    .resolve()
    .parents[3]
    .joinpath("app/static/shared/js/websockets/BaseSocket.js")
)

BASE_SOCKET_DATA_URL = (
    "data:text/javascript;base64,"
    + base64.b64encode(BASE_SOCKET_PATH.read_text(encoding="utf-8").encode("utf-8")).decode("ascii")
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


def _bootstrap_base_socket(page):
    page.add_init_script(MOCK_WEBSOCKET_SCRIPT)
    page.goto("about:blank")
    page.evaluate(
        """async ({ moduleUri }) => {
            const module = await import(moduleUri);
            window.__BaseSocket = module.BaseSocket;
        }""",
        {"moduleUri": BASE_SOCKET_DATA_URL},
    )


def test_base_socket_sender_suppression_and_status(edge_page):
    page = edge_page
    _bootstrap_base_socket(page)

    page.evaluate(
        """() => {
            window.__statuses = [];
            window.__messages = [];
            window.__socketInstance = new window.__BaseSocket({
                resolveUrl: () => 'ws://test/socket',
                autoConnect: true,
                heartbeatIntervalMs: 0,
                onStatusChange: (status) => window.__statuses.push(status),
                onMessage: (payload) => window.__messages.push(payload),
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
            { data: JSON.stringify({ type: 'count_updated', record_id: 123 }) }
        )"""
    )

    messages = page.evaluate("() => window.__messages")
    assert len(messages) == 1
    assert messages[0]["type"] == "count_updated"
    assert messages[0]["record_id"] == 123

    sender_token = page.evaluate("() => window.__socketInstance.senderToken")
    page.evaluate(
        """({ senderToken }) => window.__mockSockets[0].emit(
            'message',
            { data: JSON.stringify({ type: 'noop', senderToken }) }
        )""",
        {"senderToken": sender_token},
    )

    messages = page.evaluate("() => window.__messages")
    assert len(messages) == 1, "Self-sent message should be suppressed"

    page.evaluate("() => window.__socketInstance.sendJson({ type: 'ping' })")
    sent_payloads = page.evaluate("() => window.__mockSockets[0].sentMessages")
    assert sent_payloads, "Expected BaseSocket to send payload"

    payload = json.loads(sent_payloads[0])
    assert payload["type"] == "ping"
    assert payload["senderToken"] == sender_token

    page.evaluate("() => window.__socketInstance.disconnect()")
    statuses = page.evaluate("() => window.__statuses")
    assert statuses[-1] == "closed"
    logger.info(
        "BaseSocket e2e verified sender suppression and lifecycle transitions: %s",
        statuses,
    )
