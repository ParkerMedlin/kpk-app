import logging
from typing import Iterable, Optional, Set

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from app.websockets import base_consumer

logger = logging.getLogger(__name__)

LEGACY_GROUP = "blend_schedule_updates"
STATE_EVENT_LIMIT = 50


def _collect_target_areas(
    update_type: str,
    data: Optional[dict],
    areas: Optional[Iterable[str]],
) -> Set[str]:
    candidates: Set[str] = set()

    for area in areas or []:
        if area:
            candidates.add(str(area))

    if not data:
        candidates.add("all")
        return candidates

    primary_area = data.get("blend_area")
    if primary_area:
        candidates.add(str(primary_area))

    line = data.get("line")
    if line:
        candidates.add(str(line))

    if update_type == "blend_moved":
        for key in ("old_blend_area", "new_blend_area"):
            area = data.get(key)
            if area:
                candidates.add(str(area))

    candidates.add("all")
    return {area for area in candidates if area and area != "undefined"}


def _persist_state(area: str, update_type: str, data: dict) -> None:
    redis_key = f"blend_schedule:{area}"
    try:
        async_to_sync(base_consumer.persist_event)(
            redis_key,
            update_type or "blend_schedule_update",
            data,
            limit=STATE_EVENT_LIMIT,
        )
    except Exception:
        logger.exception("Failed to persist blend schedule state for %s", redis_key)


def broadcast_blend_schedule_update(
    update_type: str,
    data: dict,
    *,
    areas: Optional[Iterable[str]] = None,
) -> None:
    """
    Broadcasts a blend schedule update across legacy and refactored websocket groups
    while persisting a sanitized snapshot for each affected context.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.error(
            "❌ Channel layer unavailable; cannot broadcast blend schedule update"
        )
        return

    sanitized_data = base_consumer.sanitize_payload(data or {})
    event_name = update_type or "blend_schedule_update"
    payload = {
        "type": "blend_schedule_update",
        "update_type": event_name,
        "data": sanitized_data,
    }

    target_areas = _collect_target_areas(event_name, sanitized_data, areas)
    group_names = {f"blend_schedule_unique_{area}" for area in target_areas}
    group_names.add(LEGACY_GROUP)

    for group_name in group_names:
        try:
            async_to_sync(channel_layer.group_send)(group_name, payload)
        except Exception:
            logger.exception(
                "Failed to broadcast blend schedule update to %s", group_name
            )

    for area in target_areas:
        _persist_state(area, event_name, sanitized_data)
