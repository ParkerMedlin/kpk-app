from django.urls import re_path

from core.consumers import CountCollectionConsumer
from core.websockets.blend_schedule.routes import (
    websocket_routes as blend_schedule_routes,
)
from core.websockets.count_list.routes import websocket_routes as count_list_routes
from prodverse.consumers import ScheduleUpdateConsumer
from prodverse.websockets.carton_print.routes import (
    websocket_routes as carton_print_routes,
)
from prodverse.websockets.pull_status.routes import (
    websocket_routes as pull_status_routes,
)
from prodverse.websockets.spec_sheet.routes import (
    websocket_routes as spec_sheet_routes,
)

websocket_routes = [
    *count_list_routes,
    *carton_print_routes,
    *pull_status_routes,
    *spec_sheet_routes,
    *blend_schedule_routes,
    re_path(
        r"ws/count_collection/(?P<collection_context>.+)/$",
        CountCollectionConsumer.as_asgi(),
    ),
    re_path(r"ws/count_collection/$", CountCollectionConsumer.as_asgi()),
    re_path(
        r"ws/schedule_updates/(?P<schedule_context>.+)/$",
        ScheduleUpdateConsumer.as_asgi(),
    ),
]

__all__ = ["websocket_routes"]
