"""
ASGI config for app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path
from prodverse.consumers import CartonPrintConsumer  # Import the WebSocket consumer
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

from django.urls import re_path  # Use re_path for regex-based URL patterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                re_path(r'ws/carton-print/(?P<date>\d{4}-\d{2}-\d{2})/(?P<prodLine>[^/]+)/$', CartonPrintConsumer.as_asgi()),  # Updated WebSocket route
            ])
        )
    ),
})