import asyncio
import json
import logging

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from app.core.websockets.count_list import consumer as count_list_consumer
from app.core.websockets.count_list.routes import websocket_routes
from app.websockets import base_consumer

pytestmark = pytest.mark.websockets

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_count_list_connects_and_replays_initial_state(fake_redis):
    redis_key = "count_list:123"
    fake_redis.set(
        redis_key,
        json.dumps(
            {
                "events": [
                    {
                        "event": "count_updated",
                        "data": {"record_id": 1, "value": "42"},
                    }
                ]
            }
        ),
    )

    application = URLRouter(websocket_routes)

    communicator = WebsocketCommunicator(application, "/ws/count_list/123/")
    connected, _ = await communicator.connect()
    assert connected

    payload = await communicator.receive_json_from()
    assert payload["type"] == "initial_state"
    assert payload["events"][0]["event"] == "count_updated"
    assert payload["events"][0]["data"]["record_id"] == 1
    logger.info(
        "count_list initial replay returned %s for key %s",
        payload["events"][0],
        redis_key,
    )

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_update_count_persists_and_routes_to_group(
    monkeypatch, fake_redis, channel_layer
):
    async def fake_save_count(self, data):
        return None

    monkeypatch.setattr(
        count_list_consumer.CountListConsumer, "save_count", fake_save_count
    )

    consumer = count_list_consumer.CountListConsumer()
    consumer.channel_layer = channel_layer
    consumer.channel_name = "sender-chan"
    consumer.group_name = "count_list_unique_555"
    consumer.redis_key = "count_list:555"
    consumer.count_list_id = "555"

    async def fake_group_send(group, message):
        fake_group_send.calls.append((group, message))

    fake_group_send.calls = []
    monkeypatch.setattr(consumer.channel_layer, "group_send", fake_group_send)

    update_payload = {
        "action": "update_count",
        "record_id": 99,
        "record_type": "blend",
        "expected_quantity": 10,
        "counted_quantity": "4",
        "counted_date": "2025-10-14",
        "variance": 6,
        "counted": True,
        "comment": "",
        "containers": [],
        "sage_converted_quantity": "4",
        "location": "A1",
        "data": {"record_id": 99},
    }

    await consumer.update_count(update_payload)

    assert fake_group_send.calls, "Expected update_count to broadcast to the group"
    group, message = fake_group_send.calls[0]
    assert group == "count_list_unique_555"
    assert message["type"] == "count_updated"
    assert message["record_id"] == 99
    assert message["data"]["data"]["record_id"] == 99

    events = await base_consumer.load_events("count_list:555")
    assert events
    assert events[-1]["event"] == "count_updated"
    logger.info(
        "count_list update persisted event %s with payload %s",
        events[-1]["event"],
        events[-1]["data"],
    )


@pytest.mark.asyncio
async def test_forward_event_filters_sender(monkeypatch):
    consumer = count_list_consumer.CountListConsumer()
    consumer.channel_name = "chan-1"
    consumer.group_name = "count_list_unique_555"
    consumer.count_list_id = "555"

    sent_payloads = []

    async def fake_send(*, text_data=None, bytes_data=None):
        if text_data:
            sent_payloads.append(json.loads(text_data))

    consumer.send = fake_send

    # Sender matches current channel; event should be suppressed.
    await consumer.count_updated(
        {"type": "count_updated", "record_id": 1, "sender_channel_name": "chan-1"}
    )
    assert not sent_payloads

    # Event from a different channel should be forwarded without sender metadata.
    await consumer.count_updated(
        {"type": "count_updated", "record_id": 9, "sender_channel_name": "chan-2"}
    )

    assert sent_payloads
    payload = sent_payloads[0]
    assert payload["type"] == "count_updated"
    assert payload["record_id"] == 9
    assert "sender_channel_name" not in payload
    logger.info(
        "count_list forward_event delivered payload to %s with sender stripped",
        consumer.channel_name,
    )
