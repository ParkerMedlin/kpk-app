from django.urls import re_path

from .consumer import CartonPrintConsumer

websocket_routes = [
    re_path(
        r"ws/carton-print/(?P<date>\d{4}-\d{2}-\d{2})/(?P<prodLine>[^/]+)/$",
        CartonPrintConsumer.as_asgi(),
    ),
]

__all__ = ["websocket_routes", "CartonPrintConsumer"]
