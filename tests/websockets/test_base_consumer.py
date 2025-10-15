import datetime as dt
import logging
from decimal import Decimal

import pytest

from app.websockets import base_consumer

pytestmark = pytest.mark.websockets

logger = logging.getLogger(__name__)


def test_sanitize_payload_handles_nested_types():
    payload = {
        "decimal": Decimal("10.50"),
        "date": dt.date(2024, 1, 15),
        "datetime": dt.datetime(2024, 1, 15, 12, 30, tzinfo=dt.timezone.utc),
        "list": [Decimal("1.0"), {"nested": dt.date(2024, 2, 1)}],
        "tuple": (Decimal("2.0"), dt.date(2024, 3, 1)),
    }

    sanitized = base_consumer.sanitize_payload(payload)

    assert sanitized["decimal"] == "10.50"
    assert sanitized["date"] == "2024-01-15"
    assert sanitized["datetime"].startswith("2024-01-15T12:30:00")
    assert sanitized["list"][0] == "1.0"
    assert sanitized["list"][1]["nested"] == "2024-02-01"
    assert sanitized["tuple"][0] == "2.0"
    logger.info("sanitize_payload normalised nested payload: %s", sanitized)


@pytest.mark.asyncio
async def test_persist_and_load_events_round_trip(fake_redis):
    key = "test:redis"
    payload = {
        "record_id": 42,
        "decimal": Decimal("5.25"),
        "timestamp": dt.datetime(2025, 10, 14, 7, 57, 20),
    }

    await base_consumer.persist_event(key, "count_updated", payload, limit=10)

    events = await base_consumer.load_events(key)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "count_updated"
    assert event["data"]["record_id"] == 42
    assert event["data"]["decimal"] == "5.25"
    assert event["data"]["timestamp"] == "2025-10-14T07:57:20"
    logger.info(
        "persist_event round trip stored %s with payload %s",
        event["event"],
        event["data"],
    )


@pytest.mark.asyncio
async def test_send_to_group_includes_sender_and_persists(fake_redis, channel_layer):
    class DummyConsumer(base_consumer.RedisBackedConsumer):
        pass

    consumer = DummyConsumer()
    consumer.channel_layer = channel_layer
    consumer.channel_name = "sender.test"
    consumer.group_name = "group.test"
    consumer.redis_key = "redis:test"

    recipient = await channel_layer.new_channel()
    await channel_layer.group_add(consumer.group_name, recipient)

    payload = {"record_id": 7, "value": Decimal("3.14")}

    await consumer.send_to_group(
        "count_updated",
        payload,
        persist=True,
        persist_limit=5,
    )

    message = await channel_layer.receive(recipient)
    assert message["type"] == "count_updated"
    assert message["record_id"] == 7
    assert message["value"] == Decimal("3.14")
    assert message["sender_channel_name"] == "sender.test"

    events = await base_consumer.load_events(consumer.redis_key)
    assert events[-1]["event"] == "count_updated"
    assert events[-1]["data"]["record_id"] == 7
    logger.info(
        "send_to_group emitted to %s with event %s and persisted payload %s",
        consumer.group_name,
        message["type"],
        events[-1]["data"],
    )
