import logging
import json

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from app.prodverse.websockets.carton_print import consumer as carton_print_consumer
from app.prodverse.websockets.carton_print.routes import (
    websocket_routes as carton_print_routes,
)
from app.websockets import base_consumer

pytestmark = [pytest.mark.websockets]

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_carton_print_connects_and_replays_initial_state(fake_redis):
    redis_key = "carton_print_events:Hx"
    fake_redis.set(
        redis_key,
        json.dumps(
            {
                "events": [
                    {
                        "event": "carton_print_update",
                        "data": {"itemCode": "PN123_PO42_10", "isPrinted": True},
                    }
                ]
            }
        ),
    )

    application = URLRouter(carton_print_routes)

    communicator = WebsocketCommunicator(application, "/ws/carton-print/Hx/")
    connected, _ = await communicator.connect()
    assert connected

    payload = await communicator.receive_json_from()
    assert payload["type"] == "initial_state"
    assert payload["events"][0]["event"] == "carton_print_update"
    assert payload["events"][0]["data"]["itemCode"] == "PN123_PO42_10"
    logger.info(
        "carton_print initial replay delivered %s from redis key %s",
        payload["events"][0],
        redis_key,
    )

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_receive_persists_and_broadcasts(monkeypatch, fake_redis, channel_layer):
    consumer = carton_print_consumer.CartonPrintConsumer()
    consumer.channel_layer = channel_layer
    consumer.channel_name = "sender-chan"
    consumer.group_name = "carton_print_unique_Hx"
    consumer.redis_key = "carton_print_events:Hx"
    consumer.redis_zset_key = "carton_print:Hx"
    consumer.prod_line = "Hx"

    async def fake_group_send(group, message):
        fake_group_send.calls.append((group, message))

    fake_group_send.calls = []
    monkeypatch.setattr(consumer.channel_layer, "group_send", fake_group_send)

    payload = {
        "itemCode": "PN123_PO42_10",
        "isPrinted": True,
    }

    await consumer.receive(json.dumps(payload))

    assert fake_group_send.calls, "Carton print consumer should broadcast updates"
    group, message = fake_group_send.calls[0]
    assert group == "carton_print_unique_Hx"
    assert message["type"] == "carton_print_update"
    assert message["itemCode"] == "PN123_PO42_10"

    events = await base_consumer.load_events("carton_print_events:Hx")
    assert events
    assert events[-1]["event"] == "carton_print_update"
    assert events[-1]["data"]["isPrinted"] is True

    members = fake_redis.zrange("carton_print:Hx", 0, -1)
    assert "PN123_PO42_10" in members
    logger.info(
        "carton_print receive persisted %s and broadcast to %s",
        events[-1],
        group,
    )


@pytest.mark.asyncio
async def test_carton_print_update_filters_sender(monkeypatch):
    consumer = carton_print_consumer.CartonPrintConsumer()
    consumer.channel_name = "chan-1"
    consumer.group_name = "carton_print_unique_Hx"
    consumer.prod_line = "Hx"

    sent_messages = []

    async def fake_send(*, text_data=None, bytes_data=None):
        if text_data:
            sent_messages.append(json.loads(text_data))

    monkeypatch.setattr(consumer, "send", fake_send)

    await consumer.carton_print_update(
        {
            "type": "carton_print_update",
            "itemCode": "PN123",
            "isPrinted": True,
            "sender_channel_name": "chan-1",
        }
    )
    assert not sent_messages, "Sender updates should be suppressed"

    await consumer.carton_print_update(
        {
            "type": "carton_print_update",
            "itemCode": "PN999",
            "isPrinted": False,
            "sender_channel_name": "chan-2",
        }
    )
    assert sent_messages
    payload = sent_messages[0]
    assert payload["type"] == "carton_print_update"
    assert payload["itemCode"] == "PN999"
    assert "sender_channel_name" not in payload
    logger.info(
        "carton_print_update forwarded payload %s to %s",
        payload,
        consumer.channel_name,
    )


@pytest.mark.asyncio
async def test_initial_state_falls_back_to_zset(fake_redis, monkeypatch):
    consumer = carton_print_consumer.CartonPrintConsumer()
    consumer.redis_key = "carton_print_events:Hx"
    consumer.redis_zset_key = "carton_print:Hx"
    consumer.prod_line = "Hx"

    fake_redis.zadd("carton_print:Hx", {"PN555_PO11_5": 1234567890.0})

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
    assert events[0]["event"] == "carton_print_update"
    assert events[0]["data"]["itemCode"] == "PN555_PO11_5"
    logger.info(
        "carton_print fallback initial state replayed %s from redis zset %s",
        events[0],
        consumer.redis_zset_key,
    )
