import json
import logging
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


class PullStatusConsumer(RedisBackedConsumer, AsyncWebsocketConsumer):
    """
    Websocket consumer that tracks pull status toggles for a given production
    line. State is persisted in Redis both as a set (for the latest snapshot)
    and as an ordered event log (for replay).
    """

    redis_set_key: Optional[str] = None

    async def connect(self):
        raw_prod_line = self.scope["url_route"]["kwargs"].get("prodLine")
        self.prod_line = (raw_prod_line or "").replace(" ", "_") or None

        if not self.prod_line:
            logger.error(
                "Invalid pull status connection parameters: prod_line=%s",
                raw_prod_line,
            )
            await self.close(code=4000)
            return

        self.group_name = f"pull_status_unique_{self.prod_line}"
        self.redis_key = f"pull_status_events:{self.prod_line}"
        self.redis_set_key = f"pull_status:{self.prod_line}"

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
                "Invalid JSON received on PullStatusConsumer: %s", text_data
            )
            return

        # Handle heartbeat pings silently
        if data.get("action") == "ping":
            return

        item_code = data.get("itemCode")
        is_pulled = data.get("isPulled")

        if not item_code or is_pulled is None:
            logger.error(
                "Incomplete pull status payload received: itemCode=%s, isPulled=%s",
                item_code,
                is_pulled,
            )
            return

        await self._update_pull_status(item_code, bool(is_pulled))

        await self.send_to_group(
            "pull_status_update",
            {
                "itemCode": item_code,
                "isPulled": bool(is_pulled),
            },
            persist=True,
            persist_event_type="pull_status_update",
        )

    async def pull_status_update(self, event: Dict[str, object]) -> None:
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
                "Failed to serialize pull status update for prod_line=%s: %s",
                getattr(self, "prod_line", "unknown"),
                exc,
            )

    async def _send_initial_state(self) -> None:
        events = await self.load_state()
        sanitized_events = sanitize_events(events)
        if sanitized_events:
            await self._send_initial_state_payload(sanitized_events)
            return

        fallback_events = await self._snapshot_pulled_items()
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
                "Failed to serialize pull status initial state for prod_line=%s: %s",
                getattr(self, "prod_line", "unknown"),
                exc,
            )
            await self.clear_state()

    async def _update_pull_status(self, item_code: str, is_pulled: bool) -> None:
        client = base_consumer.redis_client
        if client is None or not self.redis_set_key:
            return

        try:
            if is_pulled:
                await sync_to_async(client.sadd, thread_sensitive=False)(
                    self.redis_set_key, item_code
                )
            else:
                await sync_to_async(client.srem, thread_sensitive=False)(
                    self.redis_set_key, item_code
                )
        except redis.RedisError as exc:
            logger.error(
                "Error updating Redis set %s for item %s: %s",
                self.redis_set_key,
                item_code,
                exc,
            )

    async def _snapshot_pulled_items(self) -> List[Dict[str, object]]:
        client = base_consumer.redis_client
        if client is None or not self.redis_set_key:
            return []

        try:
            items = await sync_to_async(client.smembers, thread_sensitive=False)(
                self.redis_set_key
            )
        except redis.RedisError as exc:
            logger.error(
                "Error loading pull status snapshot from %s: %s",
                self.redis_set_key,
                exc,
            )
            return []

        return [
            {
                "event": "pull_status_update",
                "data": {"itemCode": item, "isPulled": True},
            }
            for item in sorted(items)
        ]
