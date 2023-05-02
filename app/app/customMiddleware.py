from datetime import timedelta

from django.conf import settings
from django.utils import timezone

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set session timeout to 12 hours
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        response = self.get_response(request)
        return response
