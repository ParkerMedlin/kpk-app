"""
ASGI config for app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

def get_application():
    import django
    django.setup()

    from django.core.asgi import get_asgi_application
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator
    from django.urls import re_path
    from prodverse.consumers import CartonPrintConsumer, ScheduleUpdateConsumer
    from core.consumers import CountCollectionConsumer, CountListConsumer

    # Import settings to check if SSL is enabled
    from django.conf import settings
    
    # Define your WebSocket routes
    websocket_routes = [
        re_path(r'ws/carton-print/(?P<date>\d{4}-\d{2}-\d{2})/(?P<prodLine>[^/]+)/$', CartonPrintConsumer.as_asgi()),
        re_path(r'ws/schedule_updates/$', ScheduleUpdateConsumer.as_asgi()),
        re_path(r'ws/count_list/(?P<count_list_id>\w+)/$', CountListConsumer.as_asgi()),
        re_path(r'ws/count_collection/$', CountCollectionConsumer.as_asgi())
    ]

    return ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(websocket_routes)
            )
        ),
    })

application = get_application()