from django.urls import re_path

from .consumer import CartonPrintConsumer

websocket_routes = [
    re_path(
        r"ws/carton-print/(?P<prodLine>[^/]+)/$",
        CartonPrintConsumer.as_asgi(),
    ),
]

__all__ = ["websocket_routes", "CartonPrintConsumer"]
