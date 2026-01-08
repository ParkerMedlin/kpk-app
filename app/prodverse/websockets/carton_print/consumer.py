import json
import logging
import time
from typing import Dict, List, Optional

import redis
from asgiref.sync import sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer

from app.websockets import base_consumer
from app.websockets.base_consumer import (
    RedisBackedConsumer,
    json_default,
    sanitize_events,
    sanitize_payload,
)

logger = logging.getLogger(__name__)

THREE_WEEKS_SECONDS = 21 * 24 * 60 * 60


class CartonPrintConsumer(RedisBackedConsumer, AsyncWebsocketConsumer):
    """
    Websocket consumer that tracks carton print toggles for a given production
    line. State is persisted in Redis as a sorted set (ZSET) with Unix timestamps
    as scores for automatic cleanup of stale entries, plus an ordered event log
    for replay.
    """

    redis_zset_key: Optional[str] = None

    async def connect(self):
        raw_prod_line = self.scope["url_route"]["kwargs"].get("prodLine")
        self.prod_line = (raw_prod_line or "").replace(" ", "_") or None

        if not self.prod_line:
            logger.error(
                "Invalid carton print connection parameters: prod_line=%s",
                raw_prod_line,
            )
            await self.close(code=4000)
            return

        self.group_name = f"carton_print_unique_{self.prod_line}"
        self.redis_key = f"carton_print_events:{self.prod_line}"
        self.redis_zset_key = f"carton_print:{self.prod_line}"

        await self._cleanup_stale_entries()
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code):
        await self.safe_group_discard()
        raise StopConsumer

    async def receive(self, text_data: str):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error(
                "Invalid JSON received on CartonPrintConsumer: %s", text_data
            )
            return

        # Handle heartbeat pings silently
        if data.get("action") == "ping":
            return

        item_code = data.get("itemCode")
        is_printed = data.get("isPrinted")

        if not item_code or is_printed is None:
            logger.error(
                "Incomplete carton print payload received: itemCode=%s, isPrinted=%s",
                item_code,
                is_printed,
            )
            return

        await self._update_print_status(item_code, bool(is_printed))

        await self.send_to_group(
            "carton_print_update",
            {
                "itemCode": item_code,
                "isPrinted": bool(is_printed),
            },
            persist=True,
            persist_event_type="carton_print_update",
        )

    async def carton_print_update(self, event: Dict[str, object]) -> None:
        if self.is_sender(event):
            return

        payload = {
            key: value
            for key, value in event.items()
            if key != "sender_channel_name"
        }
        payload = sanitize_payload(payload)

        try:
            await self.send(text_data=json.dumps(payload, default=json_default))
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialize carton print update for prod_line=%s: %s",
                getattr(self, "prod_line", "unknown"),
                exc,
            )

    async def _send_initial_state(self) -> None:
        events = await self.load_state()
        sanitized_events = sanitize_events(events)
        if sanitized_events:
            await self._send_initial_state_payload(sanitized_events)
            return

        fallback_events = await self._snapshot_printed_items()
        sanitized_fallback = sanitize_events(fallback_events)
        if sanitized_fallback:
            await self._send_initial_state_payload(sanitized_fallback)

    async def _send_initial_state_payload(self, events: List[Dict[str, object]]) -> None:
        try:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "initial_state",
                        "events": events,
                    },
                    default=json_default,
                )
            )
        except (TypeError, ValueError) as exc:
            logger.error(
                "Failed to serialize carton print initial state for prod_line=%s: %s",
                getattr(self, "prod_line", "unknown"),
                exc,
            )
            await self.clear_state()

    async def _update_print_status(self, item_code: str, is_printed: bool) -> None:
        client = base_consumer.redis_client
        if client is None or not self.redis_zset_key:
            return

        try:
            if is_printed:
                await sync_to_async(client.zadd, thread_sensitive=False)(
                    self.redis_zset_key, {item_code: time.time()}
                )
            else:
                await sync_to_async(client.zrem, thread_sensitive=False)(
                    self.redis_zset_key, item_code
                )
        except redis.RedisError as exc:
            logger.error(
                "Error updating Redis zset %s for item %s: %s",
                self.redis_zset_key,
                item_code,
                exc,
            )

    async def _cleanup_stale_entries(self) -> None:
        client = base_consumer.redis_client
        if client is None or not self.redis_zset_key:
            return

        cutoff = time.time() - THREE_WEEKS_SECONDS
        try:
            removed = await sync_to_async(client.zremrangebyscore, thread_sensitive=False)(
                self.redis_zset_key, "-inf", cutoff
            )
            if removed:
                logger.info(
                    "Cleaned up %d stale carton print entries from %s",
                    removed,
                    self.redis_zset_key,
                )
        except redis.RedisError as exc:
            logger.error(
                "Error cleaning up stale entries from %s: %s",
                self.redis_zset_key,
                exc,
            )

    async def _snapshot_printed_items(self) -> List[Dict[str, object]]:
        client = base_consumer.redis_client
        if client is None or not self.redis_zset_key:
            return []

        try:
            items = await sync_to_async(client.zrange, thread_sensitive=False)(
                self.redis_zset_key, 0, -1
            )
        except redis.RedisError as exc:
            logger.error(
                "Error loading carton print snapshot from %s: %s",
                self.redis_zset_key,
                exc,
            )
            return []

        return [
            {
                "event": "carton_print_update",
                "data": {"itemCode": item, "isPrinted": True},
            }
            for item in sorted(items)
        ]
