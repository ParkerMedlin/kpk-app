import os
import requests
from datetime import datetime
import json
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import render, redirect, get_object_or_404
from core.models import BillOfMaterials, CiItem, ImItemWarehouse, BlendContainerClassification
from prodverse.models import *
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
import redis
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_client = redis.StrictRedis(host='kpk-app_redis_1', port=6379, db=0)

def _get_blend_component_item_code(item_code):
    if not item_code:
        return None
    return (
        BillOfMaterials.objects.filter(
            item_code__iexact=item_code,
            component_item_description__istartswith='BLEND',
        )
        .values_list('component_item_code', flat=True)
        .first()
    )

@csrf_exempt
def update_schedule_files(request):
    """Updates production schedule files and notifies connected WebSocket clients.
    
    Receives file content via POST request, writes to filesystem, and broadcasts update
    notification through WebSocket channel layer to all connected clients.
    
    Args:
        request: HTTP request object containing file name in X-Filename header and 
                file content in request body
    
    Returns:
        HttpResponse with success/error message and appropriate status code
    """
    if request.method == 'POST':
        file_name = request.headers.get('X-Filename')
        file_content = request.body
        file_path = os.path.join(settings.BASE_DIR, 'prodverse', 'static', 'prodverse', 'html', 'Kinpak, Inc', 'Production - Web Parts', file_name)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Notify clients via WebSocket with context-specific isolation
        event_message = {"file_name": file_name}
        contexts = {file_name, "global"}

        channel_layer = get_channel_layer()

        for context in contexts:
            redis_key = f"schedule_updates:{context}"
            try:
                existing = redis_client.get(redis_key)
                if existing:
                    raw_value = existing.decode('utf-8') if isinstance(existing, bytes) else existing
                    try:
                        state = json.loads(raw_value)
                    except json.JSONDecodeError:
                        state = {'events': []}
                else:
                    state = {'events': []}
                state.setdefault('events', [])
                state['events'].append({'event': 'schedule_update', 'data': {'message': event_message}})
                state['events'] = state['events'][-25:]
                redis_client.set(redis_key, json.dumps(state))
            except redis.RedisError as exc:
                logger = logging.getLogger(__name__)
                logger.error("Error storing schedule update state for %s: %s", context, exc)

            async_to_sync(channel_layer.group_send)(
                f"schedule_updates_unique_{context}",
                {
                    "type": "schedule_update",
                    "message": event_message
                }
            )
        return HttpResponse("File updated successfully")
    return HttpResponse("Method not allowed", status=405)

def get_carton_print_status(request):
    """Retrieves carton print status for items on a production line.

    Fetches item codes from Redis sorted set that have been marked as printed
    for the specified production line.

    Args:
        request: HTTP request object containing 'prodLine' query parameter

    Returns:
        JsonResponse containing list of item codes and their print status
    """
    prod_line = request.GET.get('prodLine')
    normalised_prod_line = (prod_line or '').replace(' ', '_')
    redis_key = f"carton_print:{normalised_prod_line}"

    item_codes = redis_client.zrange(redis_key, 0, -1)
    statuses = [
        {'itemCode': item_code.decode('utf-8'), 'isPrinted': True}
        for item_code in item_codes
    ]

    return JsonResponse({'statuses': statuses})


def get_pull_status(request):
    """Returns pull status snapshot for the requested production line."""

    prod_line = request.GET.get('prodLine')
    normalised_prod_line = (prod_line or '').replace(' ', '_')
    redis_key = f"pull_status:{normalised_prod_line}"

    item_codes = redis_client.smembers(redis_key)
    statuses = []
    for item_code in item_codes:
        statuses.append({
            'itemCode': item_code.decode('utf-8'),
            'isPulled': True
        })

    return JsonResponse({'statuses': statuses})

def display_item_qc(request):
    """Renders the item QC page.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered item-qc.html template
    """
    return render(request, 'prodverse/item-qc.html')

def display_pickticket_detail(request, item_code):
    """Displays pick ticket details for a given item code.
    
    Retrieves bill of materials for the item and calculates total quantities
    needed based on scheduled production quantity.
    
    Args:
        request: HTTP request object
        item_code: String identifier for the item
        
    Returns:
        Rendered pickticket.html template with bill of materials context
    """
    bom = BillOfMaterials.objects.all().filter(item_code__iexact=item_code)
    bom.item_description = BillOfMaterials.objects.only("item_description").filter(item_code__iexact=item_code).first().item_description
    schedule_qty = request.GET.get('schedule-quantity', 0)
    for bill in bom:
        if float(request.GET.get('schedule-quantity', 0)) * float(bill.qtyperbill) != 0:
            bill.total_qty = float(request.GET.get('schedule-quantity', 0)) * float(bill.qtyperbill)
        else:
            bill.total_qty = 0.0

    context = {
        'bill_of_materials': bom,
        'item_code': item_code,
        'schedule_qty': schedule_qty,
    }
    
    return render(request, 'prodverse/pickticket.html', context)

def display_production_schedule(request):
    """Renders the production schedule page.
    
    Args:
        request: HTTP request object
        
    Returns:
        Rendered productionschedule.html template
    """
    return render(request, 'prodverse/productionschedule.html')

@transaction.atomic
def display_specsheet_detail(request, item_code, po_number, juliandate):
    """Displays and updates specification sheet details for a given item.
    
    Handles both GET and POST requests:
    - POST: Updates the spec sheet state in the database
    - GET: Retrieves and displays the spec sheet details including bill of materials
           and label information
    
    Args:
        request: HTTP request object
        item_code: String identifier for the item
        po_number: String purchase order number
        juliandate: String julian date
        
    Returns:
        POST: JsonResponse with success status
        GET: Rendered specsheet.html template with full spec sheet context
             or redirect to lookup page if spec sheet not found
    
    Raises:
        SpecSheetData.DoesNotExist: If no spec sheet exists for the item code
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        state, created = SpecsheetState.objects.update_or_create(
            item_code=item_code,
            po_number=po_number,
            juliandate=juliandate,
            defaults={'state_json': data}
        )
        return JsonResponse({'status': 'success'})

    try:
        queryset = SpecSheetData.objects.filter(item_code__iexact=item_code)
        if not queryset.exists():
            raise SpecSheetData.DoesNotExist()
        if queryset.count() > 1:
            logger.warning(
                "Multiple spec sheet records found for item %s; using first result",
                item_code,
            )
        specsheet = queryset.first()
        item_code_description = CiItem.objects.only("itemcodedesc").get(itemcode__iexact=item_code).itemcodedesc

        flush_tote = None
        waste_rag = None
        blend_component_item_code = _get_blend_component_item_code(item_code)
        print(blend_component_item_code)
        if blend_component_item_code:
            container_classification = BlendContainerClassification.objects.filter(
                item_code__iexact=blend_component_item_code
            ).first()
            if container_classification:
                flush_tote = container_classification.flush_tote
                waste_rag = container_classification.waste_rag
        WASTE_RAG_COLORS = {
            'Acid': ('#000', '#ffc107', None),
            'Flammable': ('#fff', '#dc3545', None),
            'Grease/Oil': ('#000', '#fd7e14', None),
            'Soap': ('#000', '#f8f9fa', '2px solid #333'),
            'Base': ('#fff', '#0d6efd', None),
        }
        waste_rag_text = None
        waste_rag_bg = None
        waste_rag_label = None
        waste_rag_border = None
        if waste_rag:
            color_tuple = WASTE_RAG_COLORS.get(waste_rag)
            if color_tuple:
                waste_rag_label, waste_rag_bg, waste_rag_border = color_tuple
                waste_rag_text = waste_rag
        bom = BillOfMaterials.objects.filter(item_code__iexact=item_code) \
            .exclude(Q(component_item_code__startswith='/') & ~Q(component_item_code__startswith='/C'))
        label_component_item_codes = list(SpecSheetLabels.objects.values_list('item_code', flat=True))
        label_items = SpecSheetLabels.objects.all()
        try:
            state_obj = SpecsheetState.objects.get(item_code=item_code, po_number=po_number, juliandate=juliandate)
            # Assuming state_obj.state_json is a Python dict (if using JSONField) or already a JSON string
            raw_state_json_from_db = state_obj.state_json 
        except SpecsheetState.DoesNotExist:
            raw_state_json_from_db = None

        # Ensure state_json in context is a valid JSON string or empty object string
        if raw_state_json_from_db is None:
            context_state_json = '{}'
        elif isinstance(raw_state_json_from_db, str):
            # If it's already a string, try to parse and re-dump to ensure validity and consistent format
            try:
                parsed = json.loads(raw_state_json_from_db)
                context_state_json = json.dumps(parsed)
            except json.JSONDecodeError:
                context_state_json = '{}' # Fallback for bad JSON string
        elif isinstance(raw_state_json_from_db, dict):
            context_state_json = json.dumps(raw_state_json_from_db)
        else:
            # Fallback for unexpected types
            context_state_json = '{}'

        for bill in bom:
            if bill.component_item_code in label_component_item_codes:
                bill.weight_code = label_items.filter(item_code__iexact=bill.component_item_code).first().weight_code
                bill.location = label_items.filter(item_code__iexact=bill.component_item_code).first().location

        context = {
            'item_code': specsheet.item_code,
            'item_description': item_code_description,
            'component_item_code': specsheet.component_item_code,
            'product_class': specsheet.product_class,
            'water_flush': specsheet.water_flush,
            'solvent_flush': specsheet.solvent_flush,
            'soap_flush': specsheet.soap_flush,
            'oil_flush': specsheet.oil_flush,
            'polish_flush': specsheet.polish_flush,
            'package_retain': specsheet.package_retain,
            'uv_protect': specsheet.uv_protect,
            'freeze_protect': specsheet.freeze_protect,
            'min_weight': specsheet.min_weight,
            'target_weight': specsheet.target_weight,
            'max_weight': specsheet.max_weight,
            'upc': specsheet.upc,
            'scc': specsheet.scc,
            'us_dot': specsheet.us_dot,
            'special_notes': specsheet.special_notes,
            'eu_haz': specsheet.eu_case_marking,
            'haz_symbols': specsheet.haz_symbols,
            'pallet_footprint': specsheet.pallet_footprint,
            'notes': specsheet.notes,
            'bill_of_materials': bom,
            'state_json': context_state_json,
            'flush_tote': flush_tote,
            'waste_rag_text': waste_rag_text,
            'waste_rag_bg': waste_rag_bg,
            'waste_rag_label': waste_rag_label,
            'waste_rag_border': waste_rag_border,
        }
    except SpecSheetData.DoesNotExist:
        return redirect('/prodverse/specsheet/specsheet-lookup/?redirect=true')
    
    return render(request, 'prodverse/specsheet.html', context)

def display_specsheet_lookup_page(request):
    """
    Display the spec sheet lookup page.
    
    Args:
        request: The HTTP request object
        
    Returns:
        redirect_message: Query parameter indicating if user was redirected here
        from a failed spec sheet lookup
    """
    redirect_message = request.GET.get('redirect', None)
    context = {'redirect_message': redirect_message}
    return render(request, 'prodverse/specsheetlookup.html', context)

def get_last_modified(request, file_name):
    """
    Get the last modified timestamp for a file from a remote server.

    Args:
        request: The HTTP request object
        file_name: Name of the file to check

    Returns:
        JsonResponse containing either:
        - last_modified: ISO formatted timestamp string if file exists and has Last-Modified header
        - error: Error message if file not found or missing Last-Modified header
    """
    base_url = request.build_absolute_uri('/')[:-1]  # Remove trailing slash
    file_url = f'{base_url}:1337/dynamic/html/{file_name}'
    
    response = requests.head(file_url)
    
    if response.status_code == 200:
        last_modified = response.headers.get('Last-Modified')
        if last_modified:
            last_modified_date = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
            return JsonResponse({'last_modified': last_modified_date.strftime('%Y-%m-%d %H:%M:%S')})
        else:
            return JsonResponse({'error': 'Last-Modified header not found'})
    else:
        return JsonResponse({'error': f'File not found: {file_url}'})

def add_item_to_new_group(request):
    """
    Add an item to a new audit group.

    Args:
        request: The HTTP request object containing:
            recordType: Type of record being modified
            auditGroup: Name of the new audit group to add item to 
            redirectPage: Page to redirect to after update
            itemID: ID of the item to update

    Returns:
        HttpResponseRedirect to items-to-count page with recordType parameter
    """
    record_type = request.GET.get('recordType')
    new_audit_group = request.GET.get('auditGroup')
    redirect_page = request.GET.get('redirectPage')
    item_id = request.GET.get('itemID')
    print(f'record_type:{record_type}\nnew_audit_group:{new_audit_group}\nredirect_page:{redirect_page}\nitem_id:{item_id}')
    this_item = get_object_or_404(AuditGroup, id = item_id)
    this_item.audit_group = new_audit_group
    this_item.save()

    return HttpResponseRedirect(f'/prodverse/items-to-count?recordType={record_type}')

@login_required
def display_palletizer_camera(request):
    """Display the palletizer camera stream interface
    
    A dark portal through which forklift operators may gaze upon the palletizer's domain.
    Only those blessed with forklift_operator privileges may access this arcane view.
    """
    # Check if user is in forklift group
    if not request.user.groups.filter(name='forklift_operator').exists() and not request.user.is_superuser:
        return HttpResponse("Unauthorized: You must be a forklift operator to access this resource.", status=403)
    
    # This relative URL will be handled by the Nginx reverse proxy,
    # which securely forwards the request to the local streaming server.
    stream_url = '/hls-stream/hls/stream.m3u8'

    return render(request, 'prodverse/palletizer-camera.html', {
        'stream_url': stream_url
    })
