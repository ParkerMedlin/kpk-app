import base64
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
BLEND_SOCKET_PATH = (
    PROJECT_ROOT / "app/core/static/core/js/websockets/blendScheduleSocket.js"
)

BASE_SOCKET_DATA_URL = _to_data_url(BASE_SOCKET_PATH)
STATE_CACHE_DATA_URL = _to_data_url(STATE_CACHE_PATH)
HELPERS_DATA_URL = _to_data_url(HELPERS_PATH)

_blend_socket_source = BLEND_SOCKET_PATH.read_text(encoding="utf-8")
_blend_socket_source = _blend_socket_source.replace(
    "../../../shared/js/websockets/BaseSocket.js", BASE_SOCKET_DATA_URL
)
_blend_socket_source = _blend_socket_source.replace(
    "../../../shared/js/websockets/StateCache.js", STATE_CACHE_DATA_URL
)
_blend_socket_source = _blend_socket_source.replace(
    "../../../shared/js/websockets/helpers.js", HELPERS_DATA_URL
)
BLEND_SOCKET_DATA_URL = (
    "data:text/javascript;base64,"
    + base64.b64encode(_blend_socket_source.encode("utf-8")).decode("ascii")
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


def _bootstrap_blend_socket(page):
    page.add_init_script(MOCK_WEBSOCKET_SCRIPT)
    page.add_init_script(
        """
        () => {
            window.bootstrap = {
                Tooltip: class {
                    constructor() {}
                    static getInstance() { return null; }
                    dispose() {}
                }
            };
            window.initializeBlendScheduleTooltips = () => {};
            window.$ = function(selector) {
                const toArray = (input) => {
                    if (!input) return [];
                    if (Array.isArray(input)) return input.filter(Boolean);
                    if (input instanceof NodeList) return Array.from(input);
                    if (input instanceof HTMLElement || input === window || input === document) {
                        return [input];
                    }
                    return Array.from(document.querySelectorAll(input));
                };

                const elements = toArray(selector);

                const api = {
                    elements,
                    length: elements.length,
                    get(index) {
                        return elements[index];
                    },
                    each(callback) {
                        elements.forEach((el, idx) => callback.call(el, idx, el));
                        return api;
                    },
                    val(value) {
                        if (value === undefined) {
                            return elements[0] ? elements[0].value : undefined;
                        }
                        elements.forEach((el) => {
                            if ('value' in el) {
                                el.value = value;
                            }
                        });
                        return api;
                    },
                    data(key, value) {
                        if (!elements[0]) {
                            return value === undefined ? undefined : api;
                        }
                        if (!elements[0].dataset) {
                            elements[0].dataset = {};
                        }
                        if (value === undefined) {
                            return elements[0].dataset[key];
                        }
                        elements.forEach((el) => {
                            if (!el.dataset) {
                                el.dataset = {};
                            }
                            if (value === null) {
                                delete el.dataset[key];
                            } else {
                                el.dataset[key] = value;
                            }
                        });
                        return api;
                    },
                    css(property, value) {
                        if (value === undefined) {
                            return elements[0] ? getComputedStyle(elements[0])[property] : undefined;
                        }
                        elements.forEach((el) => {
                            if (el && el.style) {
                                el.style[property] = value;
                            }
                        });
                        return api;
                    },
                    attr(name, value) {
                        if (!elements[0]) {
                            return value === undefined ? undefined : api;
                        }
                        if (value === undefined) {
                            return elements[0].getAttribute(name);
                        }
                        elements.forEach((el) => {
                            if (value === null) {
                                el.removeAttribute(name);
                            } else {
                                el.setAttribute(name, value);
                            }
                        });
                        return api;
                    },
                    text(value) {
                        if (value === undefined) {
                            return elements[0] ? elements[0].textContent : undefined;
                        }
                        elements.forEach((el) => {
                            el.textContent = value;
                        });
                        return api;
                    },
                    html(value) {
                        if (value === undefined) {
                            return elements[0] ? elements[0].innerHTML : undefined;
                        }
                        elements.forEach((el) => {
                            el.innerHTML = value;
                        });
                        return api;
                    },
                    closest(selector) {
                        if (!elements[0]) {
                            return window.$([]);
                        }
                        const result = elements[0].closest(selector);
                        return window.$(result ? [result] : []);
                    },
                    find(selector) {
                        const found = elements.reduce((acc, el) => {
                            if (el) {
                                acc.push(...el.querySelectorAll(selector));
                            }
                            return acc;
                        }, []);
                        return window.$(found);
                    },
                    on() { return api; },
                    off() { return api; }
                };

                return api;
            };
            window.jQuery = window.$;
            window.$.ajax = function(options = {}) {
                if (typeof options.success === 'function') {
                    options.success({ result: 'ok' });
                }
                return Promise.resolve({ result: 'ok' });
            };
        }
    """
    )
    page.set_content(
        """
        <html>
            <body>
                <div id="connectionStatusIndicator"><span></span></div>
                <div id="deskContainer">
                    <table id="deskScheduleTable" data-blend-area="Desk_1">
                        <tbody>
                            <tr data-blend-id="template-desk" class="tableBodyRow Desk_1" style="display:none;">
                                <td>0</td>
                                <td>ITEM</td>
                                <td>Description</td>
                                <td class="lot-number-cell" lot-number="TEMPLATE">TEMPLATE</td>
                                <td class="quantity-cell">0.0 gal</td>
                                <td class="blend-sheet-status-cell">
                                    <span class="blend-sheet-status"
                                          data-print-history="[]"
                                          data-has-been-printed="false"><em>Not Printed</em></span>
                                </td>
                                <td>
                                    <div class="tank-select-wrapper">
                                        <span class="current-tank-display">No Tank</span>
                                        <select class="blendTankSelection tankSelect">
                                            <option value="">No Tank</option>
                                            <option value="TK-1">TK-1</option>
                                        </select>
                                    </div>
                                </td>
                                <td>
                                    <button class="editLotButton" data-lot-id="template"></button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div id="desk1Container">
                    <table id="desk1ScheduleTable" data-blend-area="Desk_1">
                        <tbody>
                            <tr data-blend-id="template-all-desk1" class="tableBodyRow Desk_1" style="display:none;">
                                <td>0</td>
                                <td>ITEM</td>
                                <td>Description</td>
                                <td class="lot-number-cell" lot-number="TEMPLATE">TEMPLATE</td>
                                <td class="quantity-cell">0.0 gal</td>
                                <td class="blend-sheet-status-cell">
                                    <span class="blend-sheet-status"
                                          data-print-history="[]"
                                          data-has-been-printed="false"><em>Not Printed</em></span>
                                </td>
                                <td>
                                    <div class="tank-select-wrapper">
                                        <span class="current-tank-display">No Tank</span>
                                        <select class="blendTankSelection tankSelect">
                                            <option value="">No Tank</option>
                                            <option value="TK-1">TK-1</option>
                                        </select>
                                    </div>
                                </td>
                                <td>
                                    <button class="editLotButton" data-lot-id="template"></button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div id="desk2Container">
                    <table id="desk2ScheduleTable" data-blend-area="Desk_2">
                        <tbody>
                            <tr data-blend-id="template-all-desk2" class="tableBodyRow Desk_2" style="display:none;">
                                <td>0</td>
                                <td>ITEM</td>
                                <td>Description</td>
                                <td class="lot-number-cell" lot-number="TEMPLATE">TEMPLATE</td>
                                <td class="quantity-cell">0.0 gal</td>
                                <td class="blend-sheet-status-cell">
                                    <span class="blend-sheet-status"
                                          data-print-history="[]"
                                          data-has-been-printed="false"><em>Not Printed</em></span>
                                </td>
                                <td>
                                    <div class="tank-select-wrapper">
                                        <span class="current-tank-display">No Tank</span>
                                        <select class="blendTankSelection tankSelect">
                                            <option value="">No Tank</option>
                                            <option value="TK-1">TK-1</option>
                                        </select>
                                    </div>
                                </td>
                                <td>
                                    <button class="editLotButton" data-lot-id="template"></button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </body>
        </html>
        """
    )
    page.evaluate(MOCK_WEBSOCKET_SCRIPT)
    page.evaluate(
        """async ({ moduleUri }) => {
            const module = await import(moduleUri);
            window.__BlendScheduleSocket = module.BlendScheduleSocket;
        }""",
        {"moduleUri": BLEND_SOCKET_DATA_URL},
    )


def _open_socket(page, index):
    page.evaluate(
        """
        (idx) => {
            if (!Array.isArray(window.__mockSockets) || !window.__mockSockets[idx]) {
                throw new Error(`Mock websocket ${idx} not initialised`);
            }
            window.__mockSockets[idx].emit('open', { type: 'open' });
        }
        """,
        index,
    )


def _emit_to_all(page, message):
    page.evaluate(
        """
        (msg) => {
            if (!Array.isArray(window.__mockSockets)) {
                throw new Error('Mock sockets not initialised');
            }
            const payload = JSON.stringify(msg);
            window.__mockSockets.forEach((socket) => {
                socket.emit('message', { data: payload });
            });
        }
        """,
        message,
    )


def _get_row_details(page, table_selector):
    return page.evaluate(
        """
        (selector) => {
            const nodes = Array.from(
                document.querySelectorAll(`${selector} tbody tr`)
            );
            return nodes.map((row) => {
                const id = row.getAttribute('data-blend-id');
                const orderCell = row.querySelector('td:first-child');
                const lotCell =
                    row.querySelector('.lot-number-cell') ||
                    row.querySelector('[lot-number]');
                return {
                    id,
                    order: orderCell ? orderCell.textContent.trim() : null,
                    lot: lotCell ? lotCell.getAttribute('lot-number') : null,
                };
            });
        }
        """,
        table_selector,
    )


def test_blend_schedule_socket_covers_workflow(edge_page):
    page = edge_page
    _bootstrap_blend_socket(page)

    page.evaluate(
        """() => {
            window.__statuses = [];
            window.__blendSocket = new window.__BlendScheduleSocket({
                context: 'Desk_1',
                resolveUrl: () => 'ws://test/ws/blend_schedule/Desk_1/',
                onStatusChange: (status) => window.__statuses.push(status),
            });
            window.__blendSocket.getCurrentPageArea = () => 'Desk_1';
        }"""
    )
    _open_socket(page, 0)

    statuses = page.evaluate("() => window.__statuses")
    assert statuses[0] == "connecting"
    assert "connected" in statuses

    page.evaluate(
        """() => {
            window.__desk2Socket = new window.__BlendScheduleSocket({
                context: 'Desk_2',
                resolveUrl: () => 'ws://test/ws/blend_schedule/Desk_2/',
            });
            window.__desk2Socket.getCurrentPageArea = () => 'Desk_2';
        }"""
    )
    _open_socket(page, 1)

    base_add_payload = {
        "type": "blend_schedule_update",
        "update_type": "new_blend_added",
        "data": {
            "blend_id": 3039,
            "blend_area": "Desk_1",
            "lot_number": "J252036",
            "item_code": "602037",
            "item_description": "BLEND-MILDEW STAIN RMVR KPK",
            "quantity": 450.0,
            "order": 2,
            "tank": "",
            "has_been_printed": False,
            "last_print_event_str": "<em>Not Printed</em>",
            "print_history_json": "[]",
            "was_edited_after_last_print": False,
            "row_classes": "tableBodyRow Desk_1",
            "hourshort": 999.0,
            "line": "Desk_1",
            "run_date": "2025-10-15",
            "lot_num_record_id": 11680,
        },
    }
    _emit_to_all(page, base_add_payload)

    page.wait_for_function(
        "() => !!document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"3039\"]')"
    )

    lot_number = page.evaluate(
        "() => document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"3039\"] .lot-number-cell').getAttribute('lot-number')"
    )
    assert lot_number == "J252036"

    lot_update_payload = {
        "type": "blend_schedule_update",
        "update_type": "lot_updated",
        "data": {
            "blend_id": 3039,
            "blend_area": "Desk_1",
            "lot_number": "J252036",
            "item_code": "602037",
            "item_description": "UPDATED DESCRIPTION",
            "quantity": 625.5,
            "order": 2,
            "has_been_printed": False,
            "last_print_event_str": "<em>Not Printed</em>",
            "print_history_json": "[]",
            "was_edited_after_last_print": True,
            "line": "Desk_1",
        },
    }
    _emit_to_all(page, lot_update_payload)

    quantity_display = page.evaluate(
        "() => document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"3039\"] .quantity-cell').textContent.trim()"
    )
    assert quantity_display == "625.5 gal"

    status_payload = {
        "type": "blend_schedule_update",
        "update_type": "blend_status_changed",
        "data": {
            "blend_id": 3039,
            "blend_area": "Desk_1",
            "lot_number": "J252036",
            "has_been_printed": True,
            "last_print_event_str": "Printed Oct 15",
            "print_history_json": "[]",
            "was_edited_after_last_print": False,
        },
    }
    _emit_to_all(page, status_payload)

    status_html = page.evaluate(
        "() => document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"3039\"] .blend-sheet-status').innerHTML"
    )
    assert "Printed Oct 15" in status_html

    tank_payload = {
        "type": "blend_schedule_update",
        "update_type": "tank_updated",
        "data": {
            "blend_id": 3039,
            "blend_area": "Desk_1",
            "lot_number": "J252036",
            "old_tank": "",
            "new_tank": "TK-1",
            "item_code": "602037",
            "item_description": "UPDATED DESCRIPTION",
        },
    }
    _emit_to_all(page, tank_payload)

    tank_value = page.evaluate(
        "() => document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"3039\"] .tankSelect').value"
    )
    assert tank_value == "TK-1"

    second_add_payload = {
        "type": "blend_schedule_update",
        "update_type": "new_blend_added",
        "data": {
            "blend_id": 3040,
            "blend_area": "Desk_1",
            "lot_number": "J252037",
            "item_code": "602038",
            "item_description": "SECOND BLEND",
            "quantity": 100.0,
            "order": 3,
            "tank": "",
            "has_been_printed": False,
            "last_print_event_str": "<em>Not Printed</em>",
            "print_history_json": "[]",
            "was_edited_after_last_print": False,
            "row_classes": "tableBodyRow Desk_1",
            "line": "Desk_1",
            "run_date": "2025-10-16",
        },
    }
    _emit_to_all(page, second_add_payload)

    page.wait_for_function(
        "() => !!document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"3040\"]')"
    )

    reorder_payload = {
        "type": "blend_schedule_update",
        "update_type": "schedule_reordered",
        "data": {
            "blend_area": "Desk_1",
            "reordered_items": [
                {"blend_id": 3040, "new_order": 1},
                {"blend_id": 3039, "new_order": 2},
            ],
            "total_reordered": 2,
            "update_source": "manual_sort",
        },
    }
    _emit_to_all(page, reorder_payload)

    rows_after_reorder = _get_row_details(page, "#deskScheduleTable")
    filtered_rows = [
        row
        for row in rows_after_reorder
        if row["id"] and not row["id"].startswith("template")
    ]
    assert filtered_rows, "Expected desk schedule rows after reorder payload"
    assert len(filtered_rows) >= 2
    assert filtered_rows[0]["id"] == "3040"
    assert filtered_rows[0]["order"] == "1"
    assert filtered_rows[1]["id"] == "3039"
    assert filtered_rows[1]["order"] == "2"

    note_add_payload = {
        "type": "blend_schedule_update",
        "update_type": "new_blend_added",
        "data": {
            "blend_id": 4000,
            "blend_area": "Desk_1",
            "lot_number": "NOTE-1",
            "item_code": "******",
            "item_description": "Schedule Note",
            "quantity": 0,
            "order": 4,
            "row_classes": "tableBodyRow Desk_1 NOTE",
            "has_been_printed": False,
            "last_print_event_str": "<em>Not Printed</em>",
            "print_history_json": "[]",
            "line": "Desk_1",
        },
    }
    _emit_to_all(page, note_add_payload)

    note_class = page.evaluate(
        "() => document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"4000\"]').className"
    )
    assert "NOTE" in note_class

    note_delete_payload = {
        "type": "blend_schedule_update",
        "update_type": "blend_deleted",
        "data": {"blend_id": 4000, "blend_area": "Desk_1"},
    }
    _emit_to_all(page, note_delete_payload)

    page.wait_for_function(
        "() => !document.querySelector('#deskScheduleTable tbody tr[data-blend-id=\"4000\"]')"
    )

    move_payload = {
        "type": "blend_schedule_update",
        "update_type": "blend_moved",
        "data": {
            "old_blend_id": 3039,
            "old_blend_area": "Desk_1",
            "new_blend_id": 3039,
            "new_blend_area": "Desk_2",
            "lot_number": "J252036",
            "item_code": "602037",
            "item_description": "UPDATED DESCRIPTION",
            "quantity": 625.5,
            "order": 1,
            "tank": "TK-1",
            "has_been_printed": True,
            "last_print_event_str": "Printed Oct 15",
            "print_history_json": "[]",
            "line": "Desk_2",
        },
    }
    _emit_to_all(page, move_payload)

    desk1_rows_after_move = [
        row
        for row in _get_row_details(page, "#deskScheduleTable")
        if row["id"] and not row["id"].startswith("template")
    ]
    assert all(row["id"] != "3039" for row in desk1_rows_after_move)

    desk2_rows = [
        row
        for row in _get_row_details(page, "#desk2ScheduleTable")
        if row["id"] and not row["id"].startswith("template")
    ]
    assert any(row["id"] == "3039" for row in desk2_rows)

    delete_blend_payload = {
        "type": "blend_schedule_update",
        "update_type": "blend_deleted",
        "data": {"blend_id": 3039, "blend_area": "Desk_2"},
    }
    _emit_to_all(page, delete_blend_payload)

    desk2_rows_after_delete = [
        row
        for row in _get_row_details(page, "#desk2ScheduleTable")
        if row["id"] and not row["id"].startswith("template")
    ]
    assert all(row["id"] != "3039" for row in desk2_rows_after_delete)

    lot_delete_payload = {
        "type": "blend_schedule_update",
        "update_type": "blend_deleted",
        "data": {"blend_id": 3040, "blend_area": "Desk_1"},
    }
    _emit_to_all(page, lot_delete_payload)

    final_rows = [
        row
        for row in _get_row_details(page, "#deskScheduleTable")
        if row["id"] and not row["id"].startswith("template")
    ]
    assert all(row["id"] not in {"3039", "3040", "4000"} for row in final_rows)
