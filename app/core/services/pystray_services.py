import requests
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import logging
import json
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from core.models import LotNumRecord, BillOfMaterials, ItemLocation, FunctionToggle
import redis
import uuid
import datetime as dt
import requests
import json

logger = logging.getLogger(__name__)


def _parse_request_data(request):
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST.dict()


def _normalize_function_name(value):
    if value is None:
        return ''
    return value.strip()


@login_required
def list_function_toggles(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    toggles = FunctionToggle.objects.order_by('function_name')
    payload = [
        {
            'function_name': toggle.function_name,
            'status': toggle.status,
        }
        for toggle in toggles
    ]
    return JsonResponse({'status': 'success', 'toggles': payload})


@login_required
def create_function_toggle(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    data = _parse_request_data(request)
    function_name = _normalize_function_name(data.get('function_name'))
    status = (data.get('status') or FunctionToggle.STATUS_ON).strip().lower()

    if not function_name:
        return JsonResponse({'status': 'error', 'message': 'function_name is required.'}, status=400)
    if status not in dict(FunctionToggle.STATUS_CHOICES):
        return JsonResponse({'status': 'error', 'message': 'Invalid status value.'}, status=400)

    toggle, created = FunctionToggle.objects.update_or_create(
        function_name=function_name,
        defaults={'status': status},
    )

    return JsonResponse(
        {
            'status': 'success',
            'created': created,
            'toggle': {
                'function_name': toggle.function_name,
                'status': toggle.status,
            },
        }
    )


@login_required
def update_function_toggle(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    data = _parse_request_data(request)
    function_name = _normalize_function_name(data.get('function_name'))
    status = (data.get('status') or '').strip().lower()

    if not function_name or not status:
        return JsonResponse({'status': 'error', 'message': 'function_name and status are required.'}, status=400)
    if status not in dict(FunctionToggle.STATUS_CHOICES):
        return JsonResponse({'status': 'error', 'message': 'Invalid status value.'}, status=400)

    try:
        toggle = FunctionToggle.objects.get(function_name=function_name)
    except FunctionToggle.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Function toggle not found.'}, status=404)

    toggle.status = status
    toggle.save(update_fields=['status'])

    return JsonResponse(
        {
            'status': 'success',
            'toggle': {
                'function_name': toggle.function_name,
                'status': toggle.status,
            },
        }
    )


@login_required
def delete_function_toggle(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    data = _parse_request_data(request)
    function_name = _normalize_function_name(data.get('function_name'))

    if not function_name:
        return JsonResponse({'status': 'error', 'message': 'function_name is required.'}, status=400)

    try:
        toggle = FunctionToggle.objects.get(function_name=function_name)
    except FunctionToggle.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Function toggle not found.'}, status=404)

    toggle.delete()

    return JsonResponse({'status': 'success'})

@login_required
def trigger_looper_restart(request):
    """ 
    Receives a request from the frontend (Loop Status page button) and 
    triggers the restart of the data looper by calling the local HTTPS 
    endpoint of the PYSTRAY service running on the host machine.
    """
    if request.method == 'GET':
        target_url = "https://host.docker.internal:9999/trigger-restart"
        
        try:
            logger.info(f"Attempting to trigger restart via: {target_url}")
            # Make the request to the local systray service
            # verify=False is necessary because the cert is likely self-signed
            # or issued for a different name (e.g., host IP) than 127.0.0.1
            response = requests.get(target_url, verify=False, timeout=5) 
            
            # Check if the systray service responded successfully (e.g., 200 OK)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            
            logger.info(f"Successfully triggered restart service. Response: {response.status_code}")
            return JsonResponse({'status': 'success', 'message': 'Restart triggered successfully.'})
            
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection Error calling restart service at {target_url}: {conn_err}")
            return JsonResponse({'status': 'error', 'message': 'Could not connect to the restart service. Is it running?'}, status=503) # Service Unavailable
        except requests.exceptions.Timeout as timeout_err:
             logger.error(f"Timeout calling restart service at {target_url}: {timeout_err}")
             return JsonResponse({'status': 'error', 'message': 'Connection to restart service timed out.'}, status=504) # Gateway Timeout
        except requests.exceptions.RequestException as req_err:
            # Catch other potential request errors (like SSL errors if verify=True was used, etc.)
            logger.error(f"Error calling restart service at {target_url}: {req_err}")
            return JsonResponse({'status': 'error', 'message': f'An error occurred contacting the restart service: {req_err}'}, status=500)
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error in trigger_looper_restart view: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
            
    else:
        # Only GET is allowed for this endpoint
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405) # Method Not Allowed
    
def get_pystray_service_status(request):
    pystray_status_url = 'https://host.docker.internal:9999/service-status' 
    try:
        # Note: verify=False is necessary if the service uses a self-signed cert
        # Allow network requests to fail fast if service isn't running
        response = requests.get(pystray_status_url, timeout=2, verify=False) 
        response.raise_for_status() # Check for HTTP errors (4xx or 5xx)
        
        # Forward the exact JSON response from the pystray service
        pystray_data = response.json() 
        return JsonResponse(pystray_data)

    except requests.exceptions.Timeout:
        # Log sparingly for expected timeouts when service is off
        logger.debug(f"Timeout connecting to PySTray service at {pystray_status_url} (likely stopped)")
        return JsonResponse({'status': 'stopped', 'reason': 'timeout'}, status=504) # Gateway timeout
    except requests.exceptions.ConnectionError:
        # Log sparingly for expected connection errors when service is off
        logger.debug(f"Connection refused by PySTray service at {pystray_status_url} (likely stopped)")
        return JsonResponse({'status': 'stopped', 'reason': 'connection_refused'}, status=502) # Bad Gateway
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting PySTray status from {pystray_status_url}: {e}")
        return JsonResponse({'status': 'error', 'reason': 'request_exception', 'details': str(e)}, status=500)
    except json.JSONDecodeError:
         logger.error(f"Failed to decode JSON response from {pystray_status_url}")
         return JsonResponse({'status': 'error', 'reason': 'json_decode_error'}, status=500)
    
def cache_health(request):
    cache.set("cache_ping", "pong", 2)
    return JsonResponse({"status": cache.get("cache_ping") == "pong"})

@login_required
@csrf_exempt # Assuming AJAX POST, consider CSRF protection if forms are used
def print_blend_sheet(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_code = data.get('item_code')
            lot_number = data.get('lot_number')
            lot_quantity = data.get('lot_quantity')

            if not all([item_code, lot_number, lot_quantity]):
                return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)

            # Forward the request to the local Pystray service
            # Ensure this URL and port match your Pystray service configuration
            pystray_service_url = 'http://localhost:8090/print' 
            payload = {
                'item_code': item_code,
                'lot_number': lot_number,
                'lot_quantity': lot_quantity
            }
            
            try:
                # Adjust timeout as needed
                response = requests.post(pystray_service_url, json=payload, timeout=30) 
                response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
                
                # Assuming the pystray service returns JSON
                pystray_response_data = response.json()
                return JsonResponse(pystray_response_data)

            except requests.exceptions.RequestException as e:
                # Log the error e
                return JsonResponse({'status': 'error', 'message': f'Failed to communicate with print service: {str(e)}'}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            # Log the error e
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

if not logging.getLogger(__name__).hasHandlers():
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
def trigger_excel_macro_execution(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            macro_to_run = data.get('macro_to_run')
            data_for_macro = data.get('data_for_macro')

            if not macro_to_run or data_for_macro is None:
                return JsonResponse({'status': 'error', 'message': "'macro_to_run' or 'data_for_macro' is required."}, status=400)

            lot_num_record_instance = None
            components_for_pick_sheet = []

            if macro_to_run in ["blndSheetGen", "generateProductionPackage"]:
                if len(data_for_macro) >= 6:
                    lot_number_from_data = data_for_macro[1]
                    item_code_from_data = data_for_macro[5]
                    try:
                        lot_num_record_instance = LotNumRecord.objects.get(lot_number=lot_number_from_data, item_code=item_code_from_data)
                    except (LotNumRecord.DoesNotExist, LotNumRecord.MultipleObjectsReturned):
                        pass

            if macro_to_run == "generateProductionPackage":
                if len(data_for_macro) >= 6:
                    blend_item_code = str(data_for_macro[5])
                    bom_items = BillOfMaterials.objects.filter(item_code__iexact=blend_item_code)
                    
                    for bom_item in bom_items:
                        component_code = bom_item.component_item_code
                        component_desc = bom_item.component_item_description
                        component_item_location = "Location N/A"
                        
                        try:
                            location_record = ItemLocation.objects.filter(item_code__iexact=component_code).first()
                            if location_record:
                                component_item_location = location_record.zone
                        except Exception:
                            pass

                        components_for_pick_sheet.append({
                            'componentItemCode': component_code,
                            'componentItemDesc': component_desc,
                            'componentItemLocation': component_item_location
                        })
            
            redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
            job_id = str(uuid.uuid4())
            
            job_data = {
                'id': job_id,
                'macro_to_run': macro_to_run,
                'data_for_macro': data_for_macro,
                'user_id': request.user.id,
                'created_at': dt.datetime.now().isoformat(),
                'status': 'queued',
                'lot_num_record_id': lot_num_record_instance.pk if lot_num_record_instance else None,
                'lot_number': lot_num_record_instance.lot_number if lot_num_record_instance else None,
                'item_code': lot_num_record_instance.item_code if lot_num_record_instance else None,
                'line': lot_num_record_instance.line if lot_num_record_instance else None
            }
            
            if macro_to_run == "generateProductionPackage":
                job_data['components_for_pick_sheet'] = components_for_pick_sheet
            
            # Push to queue
            redis_client.lpush('excel_macro_queue', json.dumps(job_data))
            redis_client.hset('excel_macro_jobs', job_id, json.dumps(job_data))
            
            return JsonResponse({
                'status': 'queued',
                'job_id': job_id,
                'message': f'{macro_to_run} job queued successfully'
            })

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON in request body.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Only POST requests allowed.'}, status=405)
    
@login_required
def get_data_looper_log(request):
    """
    Returns log content from the data_sync worker log file.
    Proxies to the looper_health watchdog service on the host machine.
    Supports offset-based polling for real-time log tailing.
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        offset = int(request.GET.get('offset', 0))
    except (ValueError, TypeError):
        offset = 0

    target_url = f"https://host.docker.internal:9999/get-log?offset={offset}"

    try:
        response = requests.get(target_url, verify=False, timeout=5)
        response.raise_for_status()
        return JsonResponse(response.json())

    except requests.exceptions.ConnectionError:
        logger.debug(f"Connection refused by looper_health service at {target_url}")
        return JsonResponse({
            'logs': '[Cannot connect to looper_health service - is it running?]\n',
            'new_offset': offset,
            'error': True,
            'status': 'connection_refused'
        })
    except requests.exceptions.Timeout:
        logger.debug(f"Timeout connecting to looper_health service at {target_url}")
        return JsonResponse({
            'logs': '[Timeout connecting to looper_health service]\n',
            'new_offset': offset,
            'error': True,
            'status': 'timeout'
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting log from {target_url}: {e}")
        return JsonResponse({
            'logs': f'[Error fetching log: {str(e)}]\n',
            'new_offset': offset,
            'error': True,
            'status': 'error'
        })


def check_excel_job_status(request, job_id):
    """Check status of an Excel macro job.
    
    Retrieves job status from Redis queue system.
    
    Args:
        request: HTTP request object
        job_id: UUID of the job to check
        
    Returns:
        JsonResponse with job status data
    """
    try:
        redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        job_data = redis_client.hget('excel_macro_jobs', job_id)
        
        if job_data:
            return JsonResponse(json.loads(job_data))
        else:
            return JsonResponse({'status': 'not_found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
