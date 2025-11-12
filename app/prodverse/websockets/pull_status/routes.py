from django.urls import re_path

from .consumer import PullStatusConsumer

websocket_routes = [
    re_path(
        r"ws/pull-status/(?P<prodLine>[^/]+)/$",
        PullStatusConsumer.as_asgi(),
    ),
]

__all__ = ["websocket_routes", "PullStatusConsumer"]
