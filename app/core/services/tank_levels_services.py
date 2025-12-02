from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from core.models import TankUsageLog
import decimal
from django.utils.dateparse import parse_datetime
import logging
from bs4 import BeautifulSoup
import urllib
import urllib.error
import socket

logger = logging.getLogger(__name__)

@csrf_exempt 
def log_tank_usage(request):
    """Log a tank usage event from start to stop."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            # Basic validation
            required_fields = ['tank_identifier', 'item_code', 'start_gallons', 'start_time', 'stop_gallons', 'gallons_dispensed', 'stop_time']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({'status': 'error', 'message': f'Missing field: {field}'}, status=400)

            usage_log = TankUsageLog()
            
            # Assign user and username if authenticated
            if request.user.is_authenticated:
                usage_log.user = request.user
                usage_log.logged_username = request.user.username # CAPTURE USERNAME HERE
            
            usage_log.tank_identifier = data.get('tank_identifier')
            usage_log.item_code = data.get('item_code')
            
            # Ensure numeric fields are handled correctly
            try:
                usage_log.start_gallons = decimal.Decimal(data.get('start_gallons'))
                usage_log.stop_gallons = decimal.Decimal(data.get('stop_gallons'))
                usage_log.gallons_dispensed = decimal.Decimal(data.get('gallons_dispensed'))
            except (decimal.InvalidOperation, TypeError) as e:
                return JsonResponse({'status': 'error', 'message': f'Invalid numeric value: {e}'}, status=400)

            # Convert ISO datetime strings to datetime objects
            start_time_str = data.get('start_time')
            stop_time_str = data.get('stop_time')

            if start_time_str:
                usage_log.start_time = parse_datetime(start_time_str)
            if stop_time_str:
                usage_log.stop_time = parse_datetime(stop_time_str)
            
            if not usage_log.start_time or not usage_log.stop_time:
                 return JsonResponse({'status': 'error', 'message': 'Invalid or missing start/stop time.'}, status=400)

            usage_log.save()
            return JsonResponse({'status': 'success', 'message': 'Tank usage logged successfully.', 'log_id': usage_log.id})
        
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
        except Exception as e:
            # Log the exception server-side for debugging
            # logger.error(f"Error in log_tank_usage: {e}", exc_info=True) # Assuming you have a logger configured
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method. Only POST is allowed.'}, status=405)

def get_tank_levels_html(request):
    """Get HTML content from tank level monitoring device.
    
    Retrieves raw HTML content from the tank level monitoring device at a specific IP address.
    The HTML contains current tank level readings and status information.

    Args:
        request: HTTP GET request

    Returns:
        JsonResponse containing:
            html_string (str): Raw HTML content from monitoring device or error message
    """
    if request.method == "GET":
        try:
            # Create request with timeout to prevent hanging
            req = urllib.request.Request('http://192.168.178.210/fieldDeviceData.htm')
            
            with urllib.request.urlopen(req, timeout=3.0) as fp:
                html_str = fp.read().decode("utf-8")
                
            html_str = urllib.parse.unquote(html_str)
            response_json = { 'html_string' : html_str }
            
        except (urllib.error.URLError, socket.timeout, socket.error) as e:
            logger.error(f"Tank level device unreachable: {e}")
            # Return empty/error response instead of hanging
            response_json = { 
                'html_string' : '<html><body><p>Tank level device unreachable</p></body></html>',
                'error': 'Device unreachable'
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching tank levels: {e}")
            response_json = { 
                'html_string' : '<html><body><p>Error fetching tank levels</p></body></html>',
                'error': 'Unexpected error'
            }

    return JsonResponse(response_json, safe=False)

def extract_all_tank_levels(html_string: str) -> dict[str, float]:
    soup = BeautifulSoup(html_string, "html.parser")
    tank_levels: dict[str, float] = {}
    keys_found = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        # Locate the Tag cell and the GL cell within this row
        tag_cell = next((c for c in cells if "Tag:" in c.get_text()), None)
        gl_cell  = next((c for c in cells if "GL "  in c.get_text()), None)
        if not (tag_cell and gl_cell):
            continue

        # --- Apply robust whitespace normalization ---
        raw_text = tag_cell.get_text().upper()
        # Remove both "TAG:" and "TAG: " variants more robustly
        if "TAG:" in raw_text:
            raw_text = raw_text.split("TAG:")[-1]  # Take everything after the last "TAG:"
        normalized_text = ' '.join(raw_text.split()) # Normalize internal whitespace

        if not normalized_text:
             logger.debug("[TankMonitor Parser] Skipping row, empty tag after cleaning.")
             continue
        # --- End normalization ---

        # --- Extract ONLY the final identifier part AFTER 'CMD3' ---
        try:
            # Split the string at "CMD3" and take the last part, then strip whitespace
            key_part = normalized_text.split("CMD3")[-1].strip()
            if not key_part: # Ensure we got something after splitting
                 logger.warning("[TankMonitor Parser] Could not extract valid ID after 'CMD3' for tag: '%s'", normalized_text)
                 continue
        except IndexError:
            # This handles cases where "CMD3" might not be present at all
            logger.warning("[TankMonitor Parser] 'CMD3' delimiter not found in normalized tag: '%s'. Using full tag.", normalized_text)
            key_part = normalized_text # Fallback to using the whole thing if format is unexpected

        # Clean up any remaining TAG artifacts from the key
        if key_part.startswith("TAG:"):
            key_part = key_part[4:].strip()
        elif key_part.startswith("TAG "):
            key_part = key_part[4:].strip()
            
        tag_text = key_part # Use the extracted part (e.g., '20 TEAK') as the key
        # --- End ID extraction ---

        try:
            gallons_str = gl_cell.get_text().split("GL")[0].strip()
            gallons_value = float(gallons_str)
            tank_levels[tag_text] = gallons_value # Assign using the extracted key
        except (ValueError, IndexError):
            logger.warning(
                "[TankMonitor Parser] Failed float parse for extracted tag '%s', row: %s | %s", # Log using extracted key
                tag_text,
                tag_cell.get_text(strip=True),
                gl_cell.get_text(strip=True),
            )
            # Do not add to tank_levels if float parsing fails
    
    return tank_levels