import json
import logging

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from app.prodverse.websockets.pull_status import consumer as pull_status_consumer
from app.prodverse.websockets.pull_status.routes import (
    websocket_routes as pull_status_routes,
)
from app.websockets import base_consumer

pytestmark = [pytest.mark.websockets]

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_pull_status_connects_and_replays_initial_state(fake_redis):
    redis_key = "pull_status_events:KITSLINE"
    fake_redis.set(
        redis_key,
        json.dumps(
            {
                "events": [
                    {
                        "event": "pull_status_update",
                        "data": {"itemCode": "PN123_PO42_10", "isPulled": True},
                    }
                ]
            }
        ),
    )

    application = URLRouter(pull_status_routes)

    communicator = WebsocketCommunicator(application, "/ws/pull-status/KITSLINE/")
    connected, _ = await communicator.connect()
    assert connected

    payload = await communicator.receive_json_from()
    assert payload["type"] == "initial_state"
    assert payload["events"][0]["event"] == "pull_status_update"
    assert payload["events"][0]["data"]["itemCode"] == "PN123_PO42_10"
    logger.info(
        "pull_status initial replay delivered %s from redis key %s",
        payload["events"][0],
        redis_key,
    )

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_receive_persists_and_broadcasts(monkeypatch, fake_redis, channel_layer):
    consumer = pull_status_consumer.PullStatusConsumer()
    consumer.channel_layer = channel_layer
    consumer.channel_name = "sender-chan"
    consumer.group_name = "pull_status_unique_KITSLINE"
    consumer.redis_key = "pull_status_events:KITSLINE"
    consumer.redis_set_key = "pull_status:KITSLINE"
    consumer.prod_line = "KITSLINE"

    async def fake_group_send(group, message):
        fake_group_send.calls.append((group, message))

    fake_group_send.calls = []
    monkeypatch.setattr(consumer.channel_layer, "group_send", fake_group_send)

    payload = {
        "itemCode": "PN123_PO42_10",
        "isPulled": True,
    }

    await consumer.receive(json.dumps(payload))

    assert fake_group_send.calls, "Pull status consumer should broadcast updates"
    group, message = fake_group_send.calls[0]
    assert group == "pull_status_unique_KITSLINE"
    assert message["type"] == "pull_status_update"
    assert message["itemCode"] == "PN123_PO42_10"

    events = await base_consumer.load_events("pull_status_events:KITSLINE")
    assert events
    assert events[-1]["event"] == "pull_status_update"
    assert events[-1]["data"]["isPulled"] is True

    members = fake_redis.smembers("pull_status:KITSLINE")
    assert "PN123_PO42_10" in members
    logger.info(
        "pull_status receive persisted %s and broadcast to %s",
        events[-1],
        group,
    )


@pytest.mark.asyncio
async def test_pull_status_update_filters_sender(monkeypatch):
    consumer = pull_status_consumer.PullStatusConsumer()
    consumer.channel_name = "chan-1"
    consumer.group_name = "pull_status_unique_KITSLINE"
    consumer.prod_line = "KITSLINE"

    sent_messages = []

    async def fake_send(*, text_data=None, bytes_data=None):
        if text_data:
            sent_messages.append(json.loads(text_data))

    monkeypatch.setattr(consumer, "send", fake_send)

    await consumer.pull_status_update(
        {
            "type": "pull_status_update",
            "itemCode": "PN123",
            "isPulled": True,
            "sender_channel_name": "chan-1",
        }
    )
    assert not sent_messages, "Sender updates should be suppressed"

    await consumer.pull_status_update(
        {
            "type": "pull_status_update",
            "itemCode": "PN999",
            "isPulled": False,
            "sender_channel_name": "chan-2",
        }
    )
    assert sent_messages
    payload = sent_messages[0]
    assert payload["type"] == "pull_status_update"
    assert payload["itemCode"] == "PN999"
    assert "sender_channel_name" not in payload
    logger.info(
        "pull_status_update forwarded payload %s to %s",
        payload,
        consumer.channel_name,
    )


@pytest.mark.asyncio
async def test_initial_state_falls_back_to_set(fake_redis, monkeypatch):
    consumer = pull_status_consumer.PullStatusConsumer()
    consumer.redis_key = "pull_status_events:KITSLINE"
    consumer.redis_set_key = "pull_status:KITSLINE"
    consumer.prod_line = "KITSLINE"

    fake_redis.sadd("pull_status:KITSLINE", "PN555_PO11_5")

    sent_messages = []

    async def fake_send(*, text_data=None, bytes_data=None):
        if text_data:
            sent_messages.append(json.loads(text_data))

    monkeypatch.setattr(consumer, "send", fake_send)

    await consumer._send_initial_state()

    assert sent_messages
    payload = sent_messages[0]
    assert payload["type"] == "initial_state"
    events = payload["events"]
    assert events[0]["event"] == "pull_status_update"
    assert events[0]["data"]["itemCode"] == "PN555_PO11_5"
    logger.info(
        "pull_status fallback initial state replayed %s from redis set %s",
        events[0],
        consumer.redis_set_key,
    )
