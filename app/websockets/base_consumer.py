import datetime as dt
import json
import logging
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

import redis
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

STATE_EVENT_LIMIT = 25

try:
    redis_client = redis.StrictRedis(
        host="kpk-app_redis_1",
        port=6379,
        db=0,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    redis_client.ping()
except redis.RedisError as exc:
    logger.warning(
        "Redis unavailable for websocket state persistence: %s", exc
    )
    redis_client = None


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    return str(value)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, (int, float, str)) or value is None:
        return value
    return str(value)


def sanitize_payload(value: Any) -> Any:
    return _sanitize_value(value)


def sanitize_events(events: Optional[Iterable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for entry in events or []:
        if not isinstance(entry, dict):
            continue
        event_name = entry.get("event")
        data = entry.get("data")
        if event_name is None:
            continue
        sanitized.append(
            {
                "event": _sanitize_value(event_name),
                "data": _sanitize_value(data),
            }
        )
    return sanitized


def _append_event_sync(
    redis_key: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    limit: int = STATE_EVENT_LIMIT,
) -> None:
    if redis_client is None:
        return
    try:
        existing = redis_client.get(redis_key)
        if existing:
            try:
                state = json.loads(existing)
            except json.JSONDecodeError:
                state = {"events": []}
        else:
            state = {"events": []}

        events = state.get("events", [])
        events.append({"event": event_type, "data": payload})
        state["events"] = events[-limit:]
        redis_client.set(redis_key, json.dumps(state, default=json_default), ex=20)
    except redis.RedisError as exc:
        logger.error(
            "Error appending websocket state to Redis key %s: %s",
            redis_key,
            exc,
        )


def _load_events_sync(redis_key: str) -> List[Dict[str, Any]]:
    if redis_client is None:
        return []
    try:
        raw = redis_client.get(redis_key)
        if not raw:
            return []
        state = json.loads(raw)
        events = state.get("events", [])
        if not isinstance(events, list):
            return []
        return events
    except (redis.RedisError, json.JSONDecodeError) as exc:
        logger.error(
            "Error loading websocket state from Redis key %s: %s",
            redis_key,
            exc,
        )
        return []


def _clear_events_sync(redis_key: str) -> None:
    if redis_client is None:
        return
    try:
        redis_client.delete(redis_key)
    except redis.RedisError as exc:
        logger.error(
            "Error clearing websocket state for Redis key %s: %s",
            redis_key,
            exc,
        )


async def persist_event(
    redis_key: str,
    event_type: str,
    payload: Dict[str, Any],
    *,
    limit: int = STATE_EVENT_LIMIT,
) -> None:
    if redis_client is None:
        return
    await sync_to_async(_append_event_sync, thread_sensitive=False)(
        redis_key,
        event_type,
        payload,
        limit=limit,
    )


async def load_events(redis_key: str) -> List[Dict[str, Any]]:
    if redis_client is None:
        return []
    return await sync_to_async(_load_events_sync, thread_sensitive=False)(
        redis_key
    )


async def clear_events(redis_key: str) -> None:
    if redis_client is None:
        return
    await sync_to_async(_clear_events_sync, thread_sensitive=False)(redis_key)


class RedisBackedConsumer:
    """
    Mixin that provides Redis-backed state persistence helpers for websocket
    consumers. Consumers are expected to set `group_name` and `redis_key`
    attributes prior to calling these helpers.
    """

    redis_key: Optional[str] = None
    group_name: Optional[str] = None

    async def persist_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        *,
        limit: int = STATE_EVENT_LIMIT,
    ) -> None:
        if not self.redis_key:
            logger.debug(
                "Skipping persist_event for %s: redis_key not configured",
                self.__class__.__name__,
            )
            return
        await persist_event(self.redis_key, event_type, payload, limit=limit)

    async def load_state(self) -> List[Dict[str, Any]]:
        if not self.redis_key:
            return []
        return await load_events(self.redis_key)

    async def clear_state(self) -> None:
        if not self.redis_key:
            return
        await clear_events(self.redis_key)

    async def send_to_group(
        self,
        message_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        persist: bool = False,
        persist_event_type: Optional[str] = None,
        persist_limit: int = STATE_EVENT_LIMIT,
    ) -> None:
        """
        Broadcast a payload to the current channel group. The payload is merged
        with bookkeeping fields used to suppress sender echoes. Optionally
        persists the event to Redis using `persist_event_type` or `message_type`.
        """
        if not self.group_name:
            raise ValueError(
                f"{self.__class__.__name__} missing group_name for send_to_group"
            )

        message: Dict[str, Any] = {
            "type": message_type,
            "sender_channel_name": getattr(self, "channel_name", None),
        }
        if payload:
            message.update(payload)

        await self.channel_layer.group_send(self.group_name, message)

        if persist:
            event_name = persist_event_type or message_type
            await self.persist_event(
                event_name,
                payload or {},
                limit=persist_limit,
            )

    def is_sender(self, event: Dict[str, Any]) -> bool:
        return event.get("sender_channel_name") == getattr(
            self, "channel_name", None
        )
