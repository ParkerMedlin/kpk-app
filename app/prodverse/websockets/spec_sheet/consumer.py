import json
import logging
from typing import Any, Dict, Optional

import redis
from asgiref.sync import sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer

import app.websockets.base_consumer as base_consumer
from app.websockets.base_consumer import (
    RedisBackedConsumer,
    json_default,
    sanitize_events,
    sanitize_payload,
)

logger = logging.getLogger(__name__)

STATE_EVENT_LIMIT = 5


class SpecSheetConsumer(RedisBackedConsumer, AsyncWebsocketConsumer):
    async def connect(self) -> None:
        self.spec_id = self.scope["url_route"]["kwargs"].get("spec_id")

        if not self.spec_id or self.spec_id == "undefined":
            logger.error("Invalid spec sheet identifier received: %s", self.spec_id)
            await self.close(code=4000)
            return

        self.group_name = f"spec_sheet_unique_{self.spec_id}"
        self.redis_key = f"spec_sheet_events:{self.spec_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        raise StopConsumer

    async def receive(self, text_data: Optional[str] = None, bytes_data=None) -> None:
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Received invalid JSON payload for spec sheet %s", self.spec_id)
            return

        if not isinstance(payload, dict):
            logger.error("Spec sheet payload must be a JSON object for %s", self.spec_id)
            return

        payload.pop("senderToken", None)
        state: Optional[Dict[str, Any]] = payload.get("state")
        if state is None:
            # Support legacy clients that send the state at the root level
            state = payload

        if not isinstance(state, dict):
            logger.error(
                "Spec sheet payload missing state object for %s: %s",
                self.spec_id,
                payload,
            )
            return

        sanitized_state = sanitize_payload(state)

        logger.info("Spec sheet update received for %s", self.spec_id)

        await self.send_to_group(
            "spec_sheet_update",
            {"state": sanitized_state},
        )
        await self.persist_event(
            "spec_sheet_update",
            sanitized_state,
            limit=STATE_EVENT_LIMIT,
        )

    async def spec_sheet_update(self, event: Dict[str, Any]) -> None:
        if self.is_sender(event):
            return

        state = sanitize_payload(event.get("state"))
        await self._send_json(
            {
                "type": "spec_sheet_update",
                "state": state,
            }
        )

    async def _send_initial_state(self) -> None:
        events = await self.load_state()
        sanitized_events = sanitize_events(events)
        if sanitized_events:
            logger.info(
                "Replaying %d spec sheet events for %s",
                len(sanitized_events),
                self.spec_id,
            )
            await self._send_json(
                {"type": "initial_state", "events": sanitized_events}
            )
            return

        legacy_state = await self._load_legacy_state()
        if legacy_state is None:
            return

        sanitized_state = sanitize_payload(legacy_state)
        await self._send_json(
            {
                "type": "initial_state",
                "events": [
                    {
                        "event": "spec_sheet_update",
                        "data": sanitized_state,
                    }
                ],
            }
        )
        logger.info(
            "Loaded legacy spec sheet state for %s and backfilled event log",
            self.spec_id,
        )
        await self.persist_event(
            "spec_sheet_update",
            sanitized_state,
            limit=STATE_EVENT_LIMIT,
        )

    async def _load_legacy_state(self) -> Optional[Dict[str, Any]]:
        client = base_consumer.redis_client
        if client is None:
            return None

        legacy_key = f"spec_sheet:{self.spec_id}"
        try:
            raw = await sync_to_async(
                client.get,
                thread_sensitive=False,
            )(legacy_key)
        except redis.RedisError as exc:
            logger.error(
                "Error loading legacy spec sheet state for %s: %s",
                self.spec_id,
                exc,
            )
            return None

        if not raw:
            return None

        try:
            state = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(
                "Invalid JSON stored in legacy spec sheet state for %s; clearing key",
                self.spec_id,
            )
            await sync_to_async(client.delete, thread_sensitive=False)(
                legacy_key
            )
            return None

        return state

    async def _send_json(self, payload: Dict[str, Any]) -> None:
        await self.send(
            text_data=json.dumps(payload, default=json_default)
        )
