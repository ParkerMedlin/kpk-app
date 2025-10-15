from django.urls import re_path

from .consumer import SpecSheetConsumer

websocket_routes = [
    re_path(
        r"ws/spec_sheet/(?P<spec_id>.+)/$",
        SpecSheetConsumer.as_asgi(),
    ),
]

__all__ = ["websocket_routes"]
