from django.urls import re_path

from .consumer import BlendScheduleConsumer

websocket_routes = [
    re_path(
        r"ws/blend_schedule/(?P<schedule_context>.+)/$",
        BlendScheduleConsumer.as_asgi(),
    ),
    re_path(
        r"ws/blend_schedule/$",
        BlendScheduleConsumer.as_asgi(),
    ),
]

__all__ = ["websocket_routes"]
