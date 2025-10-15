import json
import logging

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from app.prodverse.websockets.spec_sheet import consumer as spec_sheet_consumer
from app.prodverse.websockets.spec_sheet.routes import (
    websocket_routes as spec_sheet_routes,
)
from app.websockets import base_consumer

pytestmark = [pytest.mark.websockets, pytest.mark.asyncio]

logger = logging.getLogger(__name__)


async def test_spec_sheet_connects_and_replays_initial_state(fake_redis):
    spec_id = "PN123_PO42_2025"
    redis_key = f"spec_sheet_events:{spec_id}"
    await base_consumer.persist_event(
        redis_key,
        "spec_sheet_update",
        {
            "checkboxes": {"step1": True},
            "signature1": "Jane Operator",
        },
        limit=5,
    )

    application = URLRouter(spec_sheet_routes)
    communicator = WebsocketCommunicator(
        application, f"/ws/spec_sheet/{spec_id}/"
    )
    connected, _ = await communicator.connect()
    assert connected

    payload = await communicator.receive_json_from()
    assert payload["type"] == "initial_state"
    events = payload["events"]
    assert events[0]["event"] == "spec_sheet_update"
    assert events[0]["data"]["checkboxes"]["step1"] is True
    assert events[0]["data"]["signature1"] == "Jane Operator"

    logger.info(
        "spec_sheet initial replay delivered %s for %s",
        events[0]["data"],
        spec_id,
    )

    await communicator.disconnect()


async def test_receive_persists_and_broadcasts(monkeypatch, fake_redis, channel_layer):
    consumer = spec_sheet_consumer.SpecSheetConsumer()
    consumer.channel_layer = channel_layer
    consumer.channel_name = "sender.spec"
    consumer.group_name = "spec_sheet_unique_example"
    consumer.redis_key = "spec_sheet_events:example"
    consumer.spec_id = "example"

    calls = []

    async def fake_group_send(group, message):
        calls.append((group, message))

    monkeypatch.setattr(consumer.channel_layer, "group_send", fake_group_send)

    payload = {
        "state": {
            "checkboxes": {"blend_complete": True},
            "signature1": "Supervisor",
        }
    }

    await consumer.receive(json.dumps(payload))

    assert calls, "Spec sheet consumer should broadcast updates"
    group, message = calls[0]
    assert group == "spec_sheet_unique_example"
    assert message["type"] == "spec_sheet_update"
    assert message["state"]["checkboxes"]["blend_complete"] is True

    events = await base_consumer.load_events("spec_sheet_events:example")
    assert events[-1]["event"] == "spec_sheet_update"
    assert events[-1]["data"]["signature1"] == "Supervisor"
    logger.info(
        "spec_sheet receive persisted payload %s and broadcast to %s",
        events[-1]["data"],
        group,
    )


async def test_spec_sheet_update_filters_sender(monkeypatch):
    consumer = spec_sheet_consumer.SpecSheetConsumer()
    consumer.channel_name = "chan-1"
    consumer.group_name = "spec_sheet_unique_example"
    consumer.redis_key = "spec_sheet_events:example"
    consumer.spec_id = "example"

    sent_messages = []

    async def fake_send(*, text_data=None, bytes_data=None):
        if text_data:
            sent_messages.append(json.loads(text_data))

    monkeypatch.setattr(consumer, "send", fake_send)

    await consumer.spec_sheet_update(
        {
            "type": "spec_sheet_update",
            "state": {"checkboxes": {"blend_complete": True}},
            "sender_channel_name": "chan-1",
        }
    )
    assert not sent_messages, "Sender updates should be suppressed"

    await consumer.spec_sheet_update(
        {
            "type": "spec_sheet_update",
            "state": {"checkboxes": {"blend_complete": False}},
            "sender_channel_name": "chan-2",
        }
    )
    assert sent_messages
    payload = sent_messages[0]
    assert payload["type"] == "spec_sheet_update"
    assert payload["state"]["checkboxes"]["blend_complete"] is False
    logger.info(
        "spec_sheet_update forwarded payload %s to channel %s",
        payload["state"],
        consumer.channel_name,
    )


async def test_initial_state_loads_legacy_state(fake_redis):
    spec_id = "LegacySpec"
    legacy_state = {"checkboxes": {"legacy": True}, "signature1": "Legacy"}
    fake_redis.set(f"spec_sheet:{spec_id}", json.dumps(legacy_state))

    application = URLRouter(spec_sheet_routes)
    communicator = WebsocketCommunicator(
        application, f"/ws/spec_sheet/{spec_id}/"
    )
    connected, _ = await communicator.connect()
    assert connected

    payload = await communicator.receive_json_from()
    assert payload["type"] == "initial_state"
    events = payload["events"]
    assert events[0]["event"] == "spec_sheet_update"
    assert events[0]["data"]["checkboxes"]["legacy"] is True

    await communicator.disconnect()

    events = await base_consumer.load_events(f"spec_sheet_events:{spec_id}")
    assert events, "Legacy state should be backfilled into event log"
    logger.info(
        "spec_sheet legacy state for %s was backfilled with %s",
        spec_id,
        events[-1]["data"],
    )
