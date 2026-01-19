import asyncio
import json
import logging
from collections import deque
from typing import Any, Deque, Dict, Iterable, Optional

from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer

from app.websockets.base_consumer import (
    DISCONNECT_TIMEOUT,
    RedisBackedConsumer,
    json_default,
    sanitize_events,
    sanitize_payload,
)

logger = logging.getLogger(__name__)

STATE_EVENT_LIMIT = 50
LEGACY_GROUP_NAME = "blend_schedule_updates"


def _normalize_context(raw_context: Optional[str]) -> Optional[str]:
    if raw_context in {None, "", "global"}:
        return "all"
    return raw_context


class BlendScheduleConsumer(RedisBackedConsumer, AsyncWebsocketConsumer):
    """
    Redis-backed websocket consumer responsible for blend schedule updates
    across desk areas, blend areas, and the aggregate "all" view.
    """

    schedule_context: Optional[str] = None
    _recent_event_keys: Deque[str]

    async def connect(self) -> None:
        raw_context = self.scope["url_route"]["kwargs"].get("schedule_context")
        normalized = _normalize_context(raw_context)

        if not normalized or normalized == "undefined":
            logger.error("Invalid blend schedule context received: %s", raw_context)
            await self.close(code=4000)
            return

        self.schedule_context = normalized
        self.group_name = f"blend_schedule_unique_{self.schedule_context}"
        self.redis_key = f"blend_schedule:{self.schedule_context}"
        self._recent_event_keys = deque(maxlen=16)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        try:
            await self.channel_layer.group_add(LEGACY_GROUP_NAME, self.channel_name)
        except Exception:
            # Legacy group might not exist once the migration fully lands.
            logger.debug("Legacy group %s unavailable during connect", LEGACY_GROUP_NAME)

        await self.accept()
        await self._send_initial_state()

    async def disconnect(self, close_code: int) -> None:
        await self.safe_group_discard()
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(LEGACY_GROUP_NAME, self.channel_name),
                timeout=DISCONNECT_TIMEOUT,
            )
        except (asyncio.TimeoutError, Exception):
            logger.debug("Legacy group discard failed for %s", LEGACY_GROUP_NAME)
        raise StopConsumer

    async def receive(self, text_data: Optional[str] = None, bytes_data=None) -> None:
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            logger.error("Received invalid JSON on blend schedule socket: %s", text_data)
            return

        if not isinstance(payload, dict):
            logger.error("Blend schedule payload must be a JSON object: %s", payload)
            return

        if payload.get("action") == "ping":
            await self._send_json(
                {"type": "pong", "timestamp": payload.get("timestamp")}
            )

    async def blend_schedule_update(self, event: Dict[str, Any]) -> None:
        if self.is_sender(event):
            return

        update_type = event.get("update_type") or "blend_schedule_update"
        data = sanitize_payload(event.get("data") or {})

        if not self._should_process_event(update_type, data):
            return

        message = {
            "type": "blend_schedule_update",
            "update_type": update_type,
            "data": data,
        }
        await self._send_json(message)

    async def _send_initial_state(self) -> None:
        events = await self.load_state()
        sanitized = sanitize_events(events)
        if not sanitized:
            logger.debug(
                "No initial blend schedule state for context %s", self.schedule_context
            )
            return

        await self._send_json({"type": "initial_state", "events": sanitized})
        logger.info(
            "Replayed %d blend schedule events for %s",
            len(sanitized),
            self.schedule_context,
        )

    def _should_process_event(self, update_type: str, data: Dict[str, Any]) -> bool:
        """
        Filter out duplicate or irrelevant events for the current context.
        """
        if not self.schedule_context or self.schedule_context == "all":
            return self._record_event(update_type, data)

        # For specific contexts, ensure the payload targets the same area.
        areas: Iterable[str] = []
        if update_type == "blend_moved":
            areas = [
                data.get("old_blend_area"),
                data.get("new_blend_area"),
            ]
        else:
            areas = [
                data.get("blend_area"),
                data.get("line"),
            ]

        if self.schedule_context not in {area for area in areas if area}:
            return False

        return self._record_event(update_type, data)

    def _record_event(self, update_type: str, data: Dict[str, Any]) -> bool:
        """
        Tracks recently processed events to suppress duplicates caused by
        simultaneous legacy + scoped group broadcasts.
        """
        key = json.dumps(
            {"update_type": update_type, "data": data},
            sort_keys=True,
            default=json_default,
        )
        if key in self._recent_event_keys:
            return False

        self._recent_event_keys.append(key)
        return True

    async def _send_json(self, payload: Dict[str, Any]) -> None:
        await self.send(text_data=json.dumps(payload, default=json_default))
