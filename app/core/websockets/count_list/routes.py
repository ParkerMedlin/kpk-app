from django.urls import re_path

from .consumer import CountListConsumer

websocket_routes = [
    re_path(r"ws/count_list/(?P<count_list_id>.+)/$", CountListConsumer.as_asgi()),
    re_path(r"ws/count_list/$", CountListConsumer.as_asgi()),
]

__all__ = ["websocket_routes", "CountListConsumer"]
