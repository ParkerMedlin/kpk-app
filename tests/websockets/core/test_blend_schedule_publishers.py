import pytest
from channels.layers import InMemoryChannelLayer

from app.core.websockets import publishers as blend_publishers
from app.websockets import base_consumer


@pytest.mark.websockets
def test_broadcast_blend_schedule_update_targets_groups(monkeypatch):
    layer = InMemoryChannelLayer()
    sent = []

    async def fake_group_send(group, message):
        sent.append((group, message))

    layer.group_send = fake_group_send
    monkeypatch.setattr(blend_publishers, "get_channel_layer", lambda: layer)

    persisted = []

    async def fake_persist(redis_key, event_type, payload, limit=None):
        persisted.append((redis_key, event_type, payload))

    monkeypatch.setattr(base_consumer, "persist_event", fake_persist)

    payload = {
        "blend_area": "Desk_1",
        "blend_id": 123,
        "lot_number": "J250001",
    }

    blend_publishers.broadcast_blend_schedule_update(
        "blend_status_changed",
        payload,
        areas=["Desk_1"],
    )

    groups = {group for group, _ in sent}
    assert groups == {
        "blend_schedule_updates",
        "blend_schedule_unique_Desk_1",
        "blend_schedule_unique_all",
    }

    redis_keys = {key for key, _, _ in persisted}
    assert redis_keys == {"blend_schedule:Desk_1", "blend_schedule:all"}


@pytest.mark.websockets
def test_broadcast_blend_schedule_update_infers_areas(monkeypatch):
    layer = InMemoryChannelLayer()
    sent = []

    async def fake_group_send(group, message):
        sent.append((group, message))

    layer.group_send = fake_group_send
    monkeypatch.setattr(blend_publishers, "get_channel_layer", lambda: layer)

    persisted = []

    async def fake_persist(redis_key, event_type, payload, limit=None):
        persisted.append((redis_key, event_type, payload))

    monkeypatch.setattr(base_consumer, "persist_event", fake_persist)

    payload = {
        "blend_id": 555,
        "blend_area": "Desk_2",
        "old_blend_area": "Desk_1",
        "new_blend_area": "Desk_2",
    }

    blend_publishers.broadcast_blend_schedule_update(
        "blend_moved",
        payload,
        areas=None,
    )

    groups = {group for group, _ in sent}
    assert groups == {
        "blend_schedule_updates",
        "blend_schedule_unique_Desk_1",
        "blend_schedule_unique_Desk_2",
        "blend_schedule_unique_all",
    }

    redis_keys = {key for key, _, _ in persisted}
    assert redis_keys == {
        "blend_schedule:Desk_1",
        "blend_schedule:Desk_2",
        "blend_schedule:all",
    }
