from datetime import timedelta
import logging

from django.conf import settings
from django.utils import timezone

# Get logger
logger = logging.getLogger(__name__)

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set session timeout to 12 hours
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        response = self.get_response(request)
        return response

class TerminalFrameMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the current host and path
        current_host = request.get_host()
        request_path = request.path
        logger.info(f"TerminalFrameMiddleware: Processing path {request_path} from {current_host}")
        
        # Check if this is a reports endpoint request BEFORE getting the response
        if request_path.startswith('/core/reports'):
            logger.info(f"TerminalFrameMiddleware: Found reports request at {request_path}")
            
            # Get the response
            response = self.get_response(request)
            
            # Completely remove Django's X-Frame-Options header
            if 'X-Frame-Options' in response:
                logger.info(f"TerminalFrameMiddleware: Removing existing header: {response['X-Frame-Options']}")
                del response['X-Frame-Options']
            
            # Set ALL the security headers we need
            framing_headers = {
                'X-Frame-Options': 'SAMEORIGIN',
                'Content-Security-Policy': f"frame-ancestors 'self'",
                'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'same-origin'
            }
            
            # Apply all our headers
            for header, value in framing_headers.items():
                response[header] = value
                logger.info(f"TerminalFrameMiddleware: Set {header} to {value}")
            
            return response
        else:
            # For all other requests, just return the response as is
            return self.get_response(request)
