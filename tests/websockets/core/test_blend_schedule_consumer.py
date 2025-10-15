import json
from collections import deque

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from app.core.websockets.blend_schedule import consumer as blend_consumer
from app.core.websockets.blend_schedule.routes import (
    websocket_routes as blend_schedule_routes,
)
from app.websockets import base_consumer

pytestmark = [pytest.mark.websockets, pytest.mark.asyncio]


async def test_blend_schedule_connects_and_replays_initial_state(fake_redis):
    redis_key = "blend_schedule:Desk_1"
    await base_consumer.persist_event(
        redis_key,
        "blend_status_changed",
        {
            "blend_id": 101,
            "blend_area": "Desk_1",
            "has_been_printed": True,
        },
        limit=5,
    )

    application = URLRouter(blend_schedule_routes)
    communicator = WebsocketCommunicator(
        application,
        "/ws/blend_schedule/Desk_1/",
    )
    connected, _ = await communicator.connect()
    assert connected

    payload = await communicator.receive_json_from()
    assert payload["type"] == "initial_state"
    events = payload["events"]
    assert events
    assert events[0]["event"] == "blend_status_changed"
    assert events[0]["data"]["blend_id"] == 101

    await communicator.disconnect()


async def test_blend_schedule_update_filters_sender(monkeypatch):
    consumer = blend_consumer.BlendScheduleConsumer()
    consumer.channel_name = "chan-1"
    consumer.group_name = "blend_schedule_unique_Desk_1"
    consumer.redis_key = "blend_schedule:Desk_1"
    consumer.schedule_context = "Desk_1"
    consumer._recent_event_keys = deque(maxlen=16)

    sent_messages = []

    async def fake_send(*, text_data=None, bytes_data=None):
        sent_messages.append(text_data or bytes_data)

    monkeypatch.setattr(consumer, "send", fake_send)

    await consumer.blend_schedule_update(
        {
            "type": "blend_schedule_update",
            "update_type": "blend_status_changed",
            "data": {"blend_area": "Desk_1"},
            "sender_channel_name": "chan-1",
        }
    )

    assert not sent_messages


async def test_blend_schedule_update_forwards_matching_context(monkeypatch):
    consumer = blend_consumer.BlendScheduleConsumer()
    consumer.channel_name = "chan-2"
    consumer.group_name = "blend_schedule_unique_Desk_1"
    consumer.redis_key = "blend_schedule:Desk_1"
    consumer.schedule_context = "Desk_1"
    consumer._recent_event_keys = deque(maxlen=16)

    sent_messages = []

    async def fake_send(*, text_data=None, bytes_data=None):
        if text_data:
            sent_messages.append(json.loads(text_data))

    monkeypatch.setattr(consumer, "send", fake_send)

    await consumer.blend_schedule_update(
        {
            "type": "blend_schedule_update",
            "update_type": "blend_status_changed",
            "data": {"blend_area": "Desk_1", "blend_id": 202},
            "sender_channel_name": "chan-99",
        }
    )

    assert sent_messages
    message = sent_messages[0]
    assert message["update_type"] == "blend_status_changed"
    assert message["data"]["blend_id"] == 202


async def test_blend_moved_event_processes_for_old_or_new_area(monkeypatch):
    consumer = blend_consumer.BlendScheduleConsumer()
    consumer.channel_name = "chan-3"
    consumer.group_name = "blend_schedule_unique_Desk_1"
    consumer.redis_key = "blend_schedule:Desk_1"
    consumer.schedule_context = "Desk_1"
    consumer._recent_event_keys = deque(maxlen=16)

    sent_messages = []

    async def fake_send(*, text_data=None, bytes_data=None):
        if text_data:
            sent_messages.append(json.loads(text_data))

    monkeypatch.setattr(consumer, "send", fake_send)

    await consumer.blend_schedule_update(
        {
            "type": "blend_schedule_update",
            "update_type": "blend_moved",
            "data": {
                "old_blend_area": "Desk_1",
                "new_blend_area": "Desk_2",
                "old_blend_id": 1,
                "new_blend_id": 2,
            },
            "sender_channel_name": "chan-external",
        }
    )

    assert sent_messages
    assert sent_messages[0]["update_type"] == "blend_moved"
