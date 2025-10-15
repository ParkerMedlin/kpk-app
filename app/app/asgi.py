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
    from app.websockets.routing import websocket_routes

    # Import settings to check if SSL is enabled
    from django.conf import settings
    
    return ProtocolTypeRouter({
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(websocket_routes)
            )
        ),
    })

application = get_application()
